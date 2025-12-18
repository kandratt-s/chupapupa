import streamlit as st
import asyncio
from state import get_session
from services.web.gateway_web.api.gateway_client import (
    api_get_user,
    api_get_my_applications,
    api_get_active_events,
)


def render():
    session = get_session()

    if session["role"] != "student":
        st.error("Доступ запрещён")
        return

    try:
        user = asyncio.run(api_get_user(session.get("token"), session["user_id"]))
    except Exception as e:
        st.error(f"Ошибка загрузки профиля: {e}")
        return

    if not user:
        st.error("Пользователь не найден.")
        return

    st.title("👤 Профиль студента")
    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        photo_path = user.get("photo_path")
        if photo_path:
            try:
                st.image(photo_path, width=200)
            except:
                st.markdown("### 🎓")
        else:
            st.markdown(
                """
                <div style="
                    width: 150px;
                    height: 150px;
                    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 60px;
                ">🎓</div>
                """,
                unsafe_allow_html=True,
            )

    with col2:
        st.markdown(f"## {user['name']} {user['surname']}")
        st.markdown("**🎓 Студент**")
        st.markdown("---")
        st.markdown(f"📧 **Email:** {user['email']}")

        points = user.get("points", 0)
        st.markdown(f"### ⭐️ {points} баллов")

        goal = 20
        progress = min(points / goal, 1.0)
        st.progress(progress)
        st.caption(f"Прогресс: {points}/{goal} баллов")

    st.markdown("---")

    st.markdown("### 📊 Ваша активность")

    try:
        my_apps = asyncio.run(api_get_my_applications(session.get("token")))
        active_events = asyncio.run(api_get_active_events(session.get("token")))
    except Exception as e:
        st.error(f"Ошибка загрузки активности: {e}")
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        with st.container(border=True):
            st.metric("📝 Всего заявок", len(my_apps))

    with col2:
        with st.container(border=True):
            approved = len([a for a in my_apps if a.get("status") == "approved"])
            st.metric("✅ Одобрено", approved)

    with col3:
        with st.container(border=True):
            pending = len([a for a in my_apps if a.get("status") == "pending"])
            st.metric("⏳ На рассмотрении", pending)

    with col4:
        with st.container(border=True):
            st.metric("📅 Доступно мероприятий", len(active_events))

    st.markdown("---")

    st.markdown("### 📋 Последние заявки")

    if my_apps:
        recent_apps = sorted(
            my_apps, key=lambda a: a.get("created_at", ""), reverse=True
        )[:3]

        for app in recent_apps:
            status = app.get("status", "pending")
            if status == "approved":
                icon = "✅"
            elif status == "rejected":
                icon = "❌"
            else:
                icon = "⏳"

            with st.container(border=True):
                col1c, col2c = st.columns([3, 1])
                with col1c:
                    st.markdown(f"**{app.get('event_name', 'Мероприятие')}**")
                    st.caption(f"🕐 {app.get('created_at', 'Неизвестно')}")
                with col2c:
                    st.markdown(f"### {icon}")
    else:
        st.info("У вас пока нет заявок. Посетите раздел «Мероприятия»!")
