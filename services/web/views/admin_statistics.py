import streamlit as st
import pandas as pd
from datetime import datetime
from collections import Counter
from state import get_session
from services.web.api.local_logic import (
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
            return "Неизвестно"


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
    admins = [u for u in users if u.get("role") == "admin"]

    # =============================================
    # ОБЩАЯ СТАТИСТИКА (метрики)
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

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pending = len([a for a in apps if a.get("status") == "pending"])
        st.metric("⏳ На рассмотрении", pending)
    with col2:
        approved = len([a for a in apps if a.get("status") == "approved"])
        st.metric("✅ Одобрено", approved)
    with col3:
        rejected = len([a for a in apps if a.get("status") == "rejected"])
        st.metric("❌ Отклонено", rejected)
    with col4:
        active_events = len([e for e in events if e.get("is_active", True)])
        st.metric("🟢 Активных мероприятий", active_events)

    st.markdown("---")

    # =============================================
    # ГРАФИКИ
    # =============================================

    col_left, col_right = st.columns(2)

    # ----- PIE: Статусы заявок -----
    with col_left:
        st.markdown("### 📋 Статусы заявок")

        if apps:
            status_counts = Counter(a.get("status", "pending") for a in apps)

            status_df = pd.DataFrame(
                {
                    "Статус": ["Одобрено", "Отклонено", "На рассмотрении"],
                    "Количество": [
                        status_counts.get("approved", 0),
                        status_counts.get("rejected", 0),
                        status_counts.get("pending", 0),
                    ],
                }
            )

            # Убираем нулевые
            status_df = status_df[status_df["Количество"] > 0]

            if not status_df.empty:
                st.bar_chart(status_df.set_index("Статус"))
            else:
                st.info("Нет данных")
        else:
            st.info("Нет заявок")

    # ----- PIE: Типы мероприятий -----
    with col_right:
        st.markdown("### 🎯 Типы мероприятий")

        if events:
            profile_count = len([e for e in events if e.get("is_profile", False)])
            non_profile_count = len(events) - profile_count

            type_df = pd.DataFrame(
                {
                    "Тип": ["Профильные", "Непрофильные"],
                    "Количество": [profile_count, non_profile_count],
                }
            )

            type_df = type_df[type_df["Количество"] > 0]

            if not type_df.empty:
                st.bar_chart(type_df.set_index("Тип"))
            else:
                st.info("Нет данных")
        else:
            st.info("Нет мероприятий")

    st.markdown("---")

    # ----- BAR: Топ студентов по баллам -----
    st.markdown("### 🏆 Рейтинг студентов по баллам")

    if students:
        # Сортируем по баллам
        sorted_students = sorted(
            students, key=lambda u: u.get("points", 0), reverse=True
        )[:10]

        if sorted_students:
            students_df = pd.DataFrame(
                {
                    "Студент": [f"{s['name']} {s['surname']}" for s in sorted_students],
                    "Баллы": [s.get("points", 0) for s in sorted_students],
                }
            )

            st.bar_chart(students_df.set_index("Студент"))

            # Таблица с деталями
            with st.expander("📋 Подробная таблица"):
                table_data = []
                for i, s in enumerate(sorted_students, 1):
                    table_data.append(
                        {
                            "🏅 Место": i,
                            "👤 Студент": f"{s['name']} {s['surname']}",
                            "📧 Email": s["email"],
                            "⭐️ Баллы": s.get("points", 0),
                        }
                    )
                st.table(pd.DataFrame(table_data))
        else:
            st.info("Нет студентов с баллами")
    else:
        st.info("Нет студентов")

    st.markdown("---")

    # ----- BAR: Популярность мероприятий -----
    st.markdown("### 📅 Популярность мероприятий (по количеству заявок)")

    if apps and events:
        event_apps_count = Counter(a.get("event_id") for a in apps)

        event_data = []
        for event_id, count in event_apps_count.most_common(10):
            event = local_get_event(event_id)
            if event:
                event_data.append(
                    {
                        "name": event["name"],
                        "count": count,
                        "is_profile": event.get("is_profile", False),
                    }
                )

        if event_data:
            events_df = pd.DataFrame(
                {
                    "Мероприятие": [e["name"] for e in event_data],
                    "Заявок": [e["count"] for e in event_data],
                }
            )

            st.bar_chart(events_df.set_index("Мероприятие"))

            # Таблица
            with st.expander("📋 Подробная таблица"):
                table_data = []
                for e in event_data:
                    table_data.append(
                        {
                            "📅 Мероприятие": e["name"],
                            "🎯 Тип": (
                                "Профильное" if e["is_profile"] else "Непрофильное"
                            ),
                            "📝 Заявок": e["count"],
                        }
                    )
                st.table(pd.DataFrame(table_data))
        else:
            st.info("Нет данных")
    else:
        st.info("Нет заявок или мероприятий")

    st.markdown("---")

    # ----- LINE: Динамика заявок по дням -----
    st.markdown("### 📈 Динамика заявок по дням")

    if apps:
        dates = [parse_date(a.get("created_at", "")) for a in apps]
        dates = [d for d in dates if d != "Неизвестно"]

        if dates:
            date_counts = Counter(dates)
            sorted_dates = sorted(date_counts.keys())

            dynamics_df = pd.DataFrame(
                {"Дата": sorted_dates, "Заявок": [date_counts[d] for d in sorted_dates]}
            )

            st.line_chart(dynamics_df.set_index("Дата"))
        else:
            st.info("Нет данных о датах")
    else:
        st.info("Нет заявок")

    st.markdown("---")

    # ----- Эффективность одобрения -----
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
