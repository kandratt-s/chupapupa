import streamlit as st
from datetime import datetime
from services.web.local_web.state import get_session
from services.web.local_web.api.local_logic import (
    local_get_all_applications,
    local_get_user,
    local_get_event,
    local_admin_approve_application,
    local_admin_reject_application,
)


def parse_datetime(dt_str: str):
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except:
        try:
            return datetime.fromisoformat(dt_str)
        except:
            return datetime.min


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("📥 Заявки")
    st.markdown("---")

    # Фильтры
    filter_mode = st.radio(
        "Фильтр",
        ["Все", "На рассмотрении", "Одобренные", "Отклонённые"],
        horizontal=True,
    )

    apps = local_get_all_applications()

    # Применяем фильтр
    if filter_mode == "На рассмотрении":
        apps = [a for a in apps if a.get("status") == "pending"]
    elif filter_mode == "Одобренные":
        apps = [a for a in apps if a.get("status") == "approved"]
    elif filter_mode == "Отклонённые":
        apps = [a for a in apps if a.get("status") == "rejected"]

    # Сортировка по дате
    apps = sorted(
        apps, key=lambda a: parse_datetime(a.get("created_at", "")), reverse=True
    )

    # Статистика
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Всего", len(apps))
    with col2:
        pending = len([a for a in apps if a.get("status") == "pending"])
        st.metric("⏳ Ожидают", pending)
    with col3:
        approved = len([a for a in apps if a.get("status") == "approved"])
        st.metric("✅ Одобрено", approved)

    st.markdown("---")

    if not apps:
        st.info("📭 Заявок не найдено.")
        return

    # Пагинация
    per_page = 3
    total_pages = (len(apps) - 1) // per_page + 1

    if "apps_page" not in session:
        session["apps_page"] = 1

    page = session["apps_page"]
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_apps = apps[start:end]

    # Отображение заявок
    for idx, app in enumerate(page_apps):
        user = local_get_user(app["user_id"])
        event = local_get_event(app["event_id"])

        status = app.get("status", "pending")
        if status == "approved":
            status_badge = "✅ Одобрена"
            border_color = "#2ecc71"
        elif status == "rejected":
            status_badge = "❌ Отклонена"
            border_color = "#e74c3c"
        else:
            status_badge = "⏳ На рассмотрении"
            border_color = "#f39c12"

        st.markdown(
            f"""
            <div style="
                border-left: 5px solid {border_color};
                padding-left: 15px;
                margin-bottom: 10px;
            ">
                <h3>Заявка #{app['id']} — {status_badge}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            # Информация о студенте и мероприятии
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 👤 Студент")
                if user:
                    photo_path = user.get("photo_path")
                    if photo_path:
                        try:
                            st.image(photo_path, width=200, caption="Фото профиля")
                        except:
                            st.caption("📷 Фото недоступно")
                    else:
                        st.info("📷 Нет фото профиля")

                    st.markdown(f"**{user['name']} {user['surname']}**")
                    st.markdown(f"📧 {user['email']}")
                    st.markdown(f"⭐️ **{user.get('points', 0)}** баллов")
                else:
                    st.error("Студент не найден")

            with col2:
                st.markdown("#### 📅 Мероприятие")
                if event:
                    st.markdown(f"**{event['name']}**")
                    st.markdown(f"📅 Дата: {event['date']}")
                    profile_text = (
                        "🎯 Профильное"
                        if event.get("is_profile")
                        else "📘 Непрофильное"
                    )
                    st.markdown(profile_text)
                else:
                    st.warning(f"⚠️ {app.get('event_name', 'Мероприятие удалено')}")

            st.markdown("---")

            # Фото с мероприятия — крупно
            st.markdown("#### 📸 Фото с мероприятия")
            event_photo = app.get("photo_path")
            if event_photo:
                try:
                    st.image(event_photo, width=400, caption="Фото-подтверждение")
                except:
                    st.warning("📷 Фото недоступно")
            else:
                st.info("📷 Фото не прикреплено")

            st.markdown("---")

            # Дата и кнопки
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.caption(f"🕐 Создано: {app.get('created_at', 'Неизвестно')}")

            # Кнопки только для pending
            if status == "pending":
                with col2:
                    if st.button(
                        "✅ Принять",
                        key=f"appr_{start + idx}",
                        type="primary",
                        use_container_width=True,
                    ):
                        local_admin_approve_application(app["id"])
                        st.rerun()

                with col3:
                    if st.button(
                        "❌ Отклонить",
                        key=f"rej_{start + idx}",
                        use_container_width=True,
                    ):
                        local_admin_reject_application(app["id"])
                        st.rerun()

        st.markdown("")
        st.markdown("")

    # Пагинация
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if page > 1:
            if st.button("⬅️ Назад", key="apps_prev"):
                session["apps_page"] = page - 1
                st.rerun()

    with col2:
        st.markdown(
            f"<center>Страница {page} из {total_pages}</center>", unsafe_allow_html=True
        )

    with col3:
        if page < total_pages:
            if st.button("Вперёд ➡️", key="apps_next"):
                session["apps_page"] = page + 1
                st.rerun()
