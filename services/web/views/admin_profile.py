import streamlit as st
from state import get_session
from services.web.api.local_logic import (
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

    # Заголовок
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

    # Статистика администратора
    st.markdown("### 📊 Ваша статистика управления")

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

    st.markdown("---")

    # Быстрые действия
    st.markdown("### ⚡️ Быстрые действия")

    col1, col2, col3 = st.columns(3)

    with col1:
        with st.container(border=True):
            st.markdown("#### ➕ Создать мероприятие")
            st.caption("Добавить новое мероприятие в систему")
            if st.button("Перейти", key="goto_events", use_container_width=True):
                session["route"] = "admin_events_create"
                st.rerun()

    with col2:
        with st.container(border=True):
            st.markdown("#### 📥 Заявки")
            pending = len([a for a in apps if a.get("status") == "pending"])
            st.caption(f"На рассмотрении: {pending}")
            if st.button("Перейти", key="goto_apps", use_container_width=True):
                session["route"] = "admin_applications"
                st.rerun()

    with col3:
        with st.container(border=True):
            st.markdown("#### 📈 Статистика")
            st.caption("Аналитика и отчёты")
            if st.button("Перейти", key="goto_stats", use_container_width=True):
                session["route"] = "admin_statistics"
                st.rerun()
