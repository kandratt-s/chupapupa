import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from collections import Counter
from services.web.local_web.state import get_session
from services.web.local_web.api.local_logic import (
    local_get_all_applications,
    local_get_all_users,
    local_get_all_events,
    local_get_event,
)


def parse_date(dt_str: str):
    """Извлекаем только дату."""
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d")
    except:
        try:
            return datetime.fromisoformat(dt_str).strftime("%Y-%m-%d")
        except:
            return None


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("📈 Статистика")
    st.markdown("---")

    # Загрузка данных
    apps = local_get_all_applications()
    users = local_get_all_users()
    events = local_get_all_events()

    students = [u for u in users if u.get("role") == "student"]

    # =============================================
    # ОБЩАЯ СТАТИСТИКА
    # =============================================
    st.markdown("### 📊 Общая статистика")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Пользователей", len(users))
    with col2:
        st.metric("🎓 Студентов", len(students))
    with col3:
        st.metric("📅 Мероприятий", len(events))
    with col4:
        st.metric("📝 Заявок", len(apps))

    pending = len([a for a in apps if a.get("status") == "pending"])
    approved = len([a for a in apps if a.get("status") == "approved"])
    rejected = len([a for a in apps if a.get("status") == "rejected"])

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("⏳ На рассмотрении", pending)
    with col2:
        st.metric("✅ Одобрено", approved)
    with col3:
        st.metric("❌ Отклонено", rejected)
    with col4:
        active_events = len([e for e in events if e.get("is_active", True)])
        st.metric("🟢 Активных мероприятий", active_events)

    st.markdown("---")

    # =============================================
    # PIE CHART: Статусы заявок
    # =============================================
    st.markdown("### 📋 Распределение заявок по статусам")

    if apps:
        status_data = {
            "Статус": ["✅ Одобрено", "❌ Отклонено", "⏳ На рассмотрении"],
            "Количество": [approved, rejected, pending],
        }
        status_df = pd.DataFrame(status_data)
        status_df = status_df[status_df["Количество"] > 0]

        if not status_df.empty:
            fig = px.pie(
                status_df,
                values="Количество",
                names="Статус",
                color="Статус",
                color_discrete_map={
                    "✅ Одобрено": "#2ecc71",
                    "❌ Отклонено": "#e74c3c",
                    "⏳ На рассмотрении": "#f39c12",
                },
                hole=0.4,
            )
            fig.update_layout(
                height=450, font=dict(size=16), legend=dict(font=dict(size=14))
            )
            fig.update_traces(
                textposition="outside", textinfo="percent+value", textfont_size=14
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных")
    else:
        st.info("Нет заявок")

    st.markdown("---")

    # =============================================
    # BAR CHART: Популярность мероприятий
    # =============================================
    st.markdown("### 📅 Популярность мероприятий")

    if apps and events:
        event_apps_count = Counter(a.get("event_id") for a in apps)

        event_data = []
        for event_id, count in event_apps_count.most_common(10):
            event = local_get_event(event_id)
            if event:
                event_data.append(
                    {
                        "Мероприятие": event["name"],
                        "Заявок": count,
                        "Тип": (
                            "Профильное" if event.get("is_profile") else "Непрофильное"
                        ),
                    }
                )

        if event_data:
            events_df = pd.DataFrame(event_data)

            fig = px.bar(
                events_df,
                x="Мероприятие",
                y="Заявок",
                color="Тип",
                color_discrete_map={"Профильное": "#3498db", "Непрофильное": "#9b59b6"},
                text="Заявок",
            )
            fig.update_layout(
                height=450,
                font=dict(size=14),
                xaxis_tickangle=-45,
                legend=dict(font=dict(size=14)),
            )
            fig.update_traces(textposition="outside", textfont_size=14)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных")
    else:
        st.info("Нет заявок или мероприятий")

    st.markdown("---")

    # =============================================
    # LINE CHART: Динамика заявок
    # =============================================
    st.markdown("### 📈 Динамика подачи заявок")

    if apps:
        dates = [parse_date(a.get("created_at", "")) for a in apps]
        dates = [d for d in dates if d is not None]

        if dates:
            date_counts = Counter(dates)
            sorted_dates = sorted(date_counts.keys())

            dynamics_df = pd.DataFrame(
                {"Дата": sorted_dates, "Заявок": [date_counts[d] for d in sorted_dates]}
            )

            fig = px.line(
                dynamics_df, x="Дата", y="Заявок", markers=True, line_shape="spline"
            )
            fig.update_traces(
                line=dict(color="#3498db", width=3),
                marker=dict(size=10, color="#2ecc71"),
            )
            fig.update_layout(height=400, font=dict(size=14), xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Нет данных о датах")
    else:
        st.info("Нет заявок")

    st.markdown("---")

    # =============================================
    # ТАБЛИЦА: Рейтинг студентов
    # =============================================
    st.markdown("### 🏆 Рейтинг студентов по баллам")

    if students:
        sorted_students = sorted(
            students, key=lambda u: u.get("points", 0), reverse=True
        )

        table_data = []
        for i, s in enumerate(sorted_students, 1):
            number = f"{i}"

            table_data.append(
                {
                    "Место": number,
                    "Студент": f"{s['name']} {s['surname']}",
                    "Email": s["email"],
                    "Баллы": s.get("points", 0),
                }
            )

        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True,
            height=400,
        )
    else:
        st.info("Нет студентов")

    st.markdown("---")

    # =============================================
    # Эффективность
    # =============================================
    st.markdown("### 📊 Эффективность рассмотрения заявок")

    if apps:
        total_reviewed = approved + rejected
        if total_reviewed > 0:
            approval_rate = (approved / total_reviewed) * 100

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("📝 Всего рассмотрено", total_reviewed)
            with col2:
                st.metric("✅ Процент одобрения", f"{approval_rate:.1f}%")
            with col3:
                avg_points = (
                    sum(s.get("points", 0) for s in students) / len(students)
                    if students
                    else 0
                )
                st.metric("⭐️ Средний балл студента", f"{avg_points:.1f}")

            # Прогресс-бар одобрения
            st.progress(approval_rate / 100)
        else:
            st.info("Нет рассмотренных заявок")
    else:
        st.info("Нет заявок")
