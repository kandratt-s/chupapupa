import streamlit as st
import asyncio
from state import get_session
from services.web.gateway_web.api.gateway_client import (
    api_get_user,
    api_get_all_applications,
    api_get_all_users,
    api_get_all_events,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    try:
        user = asyncio.run(api_get_user(session["user_id"]))
    except Exception as e:
        st.error(f"Ошибка загрузки профиля: {e}")
        return

    if not user:
        st.error("Пользователь не найден.")
        return

    st.title("👤 Профиль администратора")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        photo_path = user.get("photo_path")
        if photo_path:
            try:
                st.image(photo_path, width=200)
            except:
                st.markdown("### 👑")
        else:
            st.markdown(
                """
                <div style="
                    width: 150px;
                    height: 150px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 60px;
                ">👑</div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown(f"## {user['name']} {user['surname']}")
        st.markdown("**👑 Администратор**")
        st.markdown("---")
        st.markdown(f"📧 **Email:** {user['email']}")
        st.markdown(f"🆔 **ID:** {user['id']}")

    st.markdown("---")

    st.markdown("### 📊 Статистика системы")

    try:
        apps = asyncio.run(api_get_all_applications())
        users = asyncio.run(api_get_all_users())
        events = asyncio.run(api_get_all_events())
    except Exception as e:
        st.error(f"Ошибка загрузки статистики: {e}")
        return

    col1s, col2s, col3s, col4s = st.columns(4)

    with col1s:
        with st.container(border=True):
            st.metric("👥 Пользователей", len(users))

    with col2s:
        with st.container(border=True):
            st.metric("📅 Мероприятий", len(events))

    with col3s:
        with st.container(border=True):
            pending = len([a for a in apps if a.get("status") == "pending"])
            st.metric("⏳ Ожидают решения", pending)

    with col4s:
        with st.container(border=True):
            approved = len([a for a in apps if a.get("status") == "approved"])
            st.metric("✅ Одобрено", approved)
