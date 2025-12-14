import streamlit as st
from datetime import datetime
import asyncio
from state import get_session
from services.web.gateway_web.api.gateway_client import api_get_my_applications


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

    if session["role"] != "student":
        st.error("Доступ запрещён")
        return

    st.title("📝 Мои заявки")
    st.markdown("---")

    filter_mode = st.radio(
        "Фильтр",
        ["Все", "На рассмотрении", "Одобренные", "Отклонённые"],
        horizontal=True,
    )

    try:
        apps = asyncio.run(api_get_my_applications(session["user_id"]))
    except Exception as e:
        st.error(f"Ошибка загрузки заявок: {e}")
        return

    if filter_mode == "На рассмотрении":
        apps = [a for a in apps if a.get("status") == "pending"]
    elif filter_mode == "Одобренные":
        apps = [a for a in apps if a.get("status") == "approved"]
    elif filter_mode == "Отклонённые":
        apps = [a for a in apps if a.get("status") == "rejected"]

    apps = sorted(
        apps, key=lambda a: parse_datetime(a.get("created_at", "")), reverse=True
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Всего", len(apps))
    with col2:
        approved = len([a for a in apps if a.get("status") == "approved"])
        st.metric("✅ Одобрено", approved)
    with col3:
        pending = len([a for a in apps if a.get("status") == "pending"])
        st.metric("⏳ Ожидают", pending)

    st.markdown("---")

    if not apps:
        st.info("📭 Заявок не найдено.")
        return

    for app in apps:
        status = app.get("status", "pending")

        if status == "approved":
            icon = "✅"
            status_text = "Одобрена"
        elif status == "rejected":
            icon = "❌"
            status_text = "Отклонена"
        else:
            icon = "⏳"
            status_text = "На рассмотрении"

        with st.container(border=True):
            col1c, col2c = st.columns([3, 1])

            with col1c:
                st.markdown(f"### {app.get('event_name', 'Мероприятие')}")
                st.caption(f"🕐 {app.get('created_at', 'Неизвестно')}")

                photo_path = app.get("photo_path")
                if photo_path:
                    try:
                        st.image(photo_path, width=200)
                    except:
                        st.caption("📷 Фото недоступно")

            with col2c:
                st.markdown(f"## {icon}")
                st.markdown(f"**{status_text}**")
