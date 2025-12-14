import streamlit as st
from datetime import datetime
from state import get_session
from services.web.api.local_logic import (
    local_get_all_applications,
    local_get_user,
    local_get_event,
    local_admin_approve_application,
    local_admin_reject_application,
)


def parse_datetime(dt_str: str):
    """Парсинг даты для сортировки."""
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

    # Сортировка по дате (от новых к старым)
    apps = sorted(
        apps, key=lambda a: parse_datetime(a.get("created_at", "")), reverse=True
    )

    # Статистика
    total = len(apps)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего заявок", total)
    with col2:
        pending = len([a for a in apps if a.get("status") == "pending"])
        st.metric("На рассмотрении", pending)
    with col3:
        approved = len([a for a in apps if a.get("status") == "approved"])
        st.metric("Одобрено", approved)

    st.markdown("---")

    if not apps:
        st.info("📭 Заявок не найдено.")
        return

    for idx, app in enumerate(apps):
        user = local_get_user(app["user_id"])
        event = local_get_event(app["event_id"])

        with st.container(border=True):
            # Статус
            status = app.get("status", "pending")
            if status == "approved":
                status_badge = "✅ Одобрена"
            elif status == "rejected":
                status_badge = "❌ Отклонена"
            else:
                status_badge = "⏳ На рассмотрении"

            st.markdown(f"### Заявка #{app['id']} — {status_badge}")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 👤 Студент")
                if user:
                    photo_path = user.get("photo_path")
                    if photo_path:
                        try:
                            st.image(photo_path, width=120)
                        except:
                            st.caption("📷 Фото недоступно")

                    st.markdown(f"**{user['name']} {user['surname']}**")
                    st.caption(
                        f"📧 {user['email']} | ⭐️ {user.get('points', 0)} баллов"
                    )
                else:
                    st.error("Студент не найден")

            with col2:
                st.markdown("#### 📅 Мероприятие")
                if event:
                    st.markdown(f"**{event['name']}**")
                    st.caption(
                        f"📅 {event['date']} | {'🎯 Профильное' if event.get('is_profile') else '📘 Непрофильное'}"
                    )
                else:
                    st.warning(f"⚠️ {app.get('event_name', 'Удалено')}")

                st.markdown("#### 📸 Фото с мероприятия")
                event_photo = app.get("photo_path")
                if event_photo:
                    try:
                        st.image(event_photo, width=150)
                    except:
                        st.caption("📷 Недоступно")
                else:
                    st.caption("📷 Не прикреплено")

            st.caption(f"🕐 {app.get('created_at', 'Неизвестно')}")

            # Кнопки только для pending
            if status == "pending":
                col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
                with col_btn1:
                    if st.button("✅ Принять", key=f"appr_{idx}", type="primary"):
                        local_admin_approve_application(app["id"])
                        st.rerun()
                with col_btn2:
                    if st.button("❌ Отклонить", key=f"rej_{idx}"):
                        local_admin_reject_application(app["id"])
                        st.rerun()
