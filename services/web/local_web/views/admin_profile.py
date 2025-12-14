import streamlit as st
from services.web.local_web.state import get_session
from services.web.local_web.api.local_logic import (
    local_get_user,
    local_get_all_applications,
    local_get_all_users,
    local_get_all_events,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    user = local_get_user(session["user_id"])

    if not user:
        st.error("Пользователь не найден.")
        return

    st.title("👤 Профиль администратора")
    st.markdown("---")

    # Карточка профиля
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

    # Статистика
    st.markdown("### 📊 Статистика системы")

    apps = local_get_all_applications()
    users = local_get_all_users()
    events = local_get_all_events()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container(border=True):
            st.metric("👥 Пользователей", len(users))

    with col2:
        with st.container(border=True):
            st.metric("📅 Мероприятий", len(events))

    with col3:
        with st.container(border=True):
            pending = len([a for a in apps if a.get("status") == "pending"])
            st.metric("⏳ Ожидают решения", pending)

    with col4:
        with st.container(border=True):
            approved = len([a for a in apps if a.get("status") == "approved"])
            st.metric("✅ Одобрено", approved)
