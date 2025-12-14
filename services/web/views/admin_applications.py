import streamlit as st
from state import get_session
from services.web.api.local_logic import (
    local_get_all_applications,
    local_get_user,
    local_get_event,
    local_admin_approve_application,
    local_admin_reject_application,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("📥 Заявки")

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

    # Сортировка: pending первыми, потом по дате
    status_order = {"pending": 0, "approved": 1, "rejected": 2}
    apps = sorted(
        apps,
        key=lambda a: (status_order.get(a.get("status"), 3), a.get("created_at", "")),
        reverse=False,
    )

    if not apps:
        st.info("Заявок не найдено.")
        return

    for idx, app in enumerate(apps):
        user = local_get_user(app["user_id"])
        event = local_get_event(app["event_id"])

        with st.container(border=True):
            # Статус в заголовке
            status = app.get("status", "pending")
            if status == "approved":
                status_badge = "✅ Одобрена"
                status_color = "green"
            elif status == "rejected":
                status_badge = "❌ Отклонена"
                status_color = "red"
            else:
                status_badge = "⏳ На рассмотрении"
                status_color = "orange"

            st.write(f"### Заявка #{app['id']} — :{status_color}[{status_badge}]")

            col1, col2 = st.columns(2)

            # Левая колонка — информация о студенте
            with col1:
                st.write("#### 👤 Студент")

                if user:
                    # Фото профиля
                    photo_path = user.get("photo_path")
                    if photo_path:
                        try:
                            st.image(photo_path, width=150, caption="Фото профиля")
                        except:
                            st.write("📷 Фото недоступно")
                    else:
                        st.write("📷 Нет фото профиля")

                    st.write(f"**{user['name']} {user['surname']}**")
                    st.write(f"📧 {user['email']}")
                    st.write(f"⭐️ Баллы: {user.get('points', 0)}")
                else:
                    st.error("Студент не найден")

            # Правая колонка — информация о мероприятии и фото
            with col2:
                st.write("#### 📅 Мероприятие")

                if event:
                    st.write(f"**{event['name']}**")
                    st.write(f"📅 Дата: {event['date']}")
                    profile_text = (
                        "🎯 Профильное"
                        if event.get("is_profile")
                        else "📘 Непрофильное"
                    )
                    st.write(profile_text)
                else:
                    st.write(f"**{app.get('event_name', 'Неизвестно')}**")
                    st.warning("Мероприятие удалено")

                # Фото с мероприятия
                st.write("#### 📸 Фото с мероприятия")
                event_photo = app.get("photo_path")
                if event_photo:
                    try:
                        st.image(event_photo, width=200, caption="Фото с мероприятия")
                    except:
                        st.write("📷 Фото недоступно")
                else:
                    st.write("📷 Фото не прикреплено")

            # Дата создания
            st.write(f"🕐 Создано: {app.get('created_at', 'Неизвестно')}")
