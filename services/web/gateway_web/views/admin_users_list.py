import streamlit as st
import asyncio
from state import get_session
from services.web.gateway_web.api.gateway_client import (
    api_get_all_users,
    api_delete_user,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("👥 Список пользователей")
    st.markdown("---")

    filter_mode = st.radio(
        "Фильтр",
        ["Все", "Студенты", "Администраторы"],
        horizontal=True,
    )

    try:
        users = asyncio.run(api_get_all_users())
    except Exception as e:
        st.error(f"Ошибка загрузки пользователей: {e}")
        return

    if filter_mode == "Студенты":
        users = [u for u in users if u.get("role") == "student"]
    elif filter_mode == "Администраторы":
        users = [u for u in users if u.get("role") == "admin"]

    users = sorted(users, key=lambda u: u.get("name", "").lower())

    total = len(users)
    students = len([u for u in users if u.get("role") == "student"])
    admins = len([u for u in users if u.get("role") == "admin"])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Всего", total)
    with col2:
        st.metric("Студентов", students)
    with col3:
        st.metric("Админов", admins)

    st.markdown("---")

    if not users:
        st.info("📭 Пользователей не найдено.")
        return

    per_page = 6
    total_pages = (len(users) - 1) // per_page + 1

    if "users_page" not in session:
        session["users_page"] = 1

    page = session["users_page"]
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_users = users[start:end]

    cols = st.columns(2)

    for idx, u in enumerate(page_users):
        with cols[idx % 2]:
            with st.container(border=True):
                col1c, col2c = st.columns([1, 2])

                with col1c:
                    photo_path = u.get("photo_path")
                    if photo_path:
                        try:
                            st.image(photo_path, width=80)
                        except:
                            st.markdown("📷")
                    else:
                        st.markdown("### 👤")

                with col2c:
                    role_icon = "👑" if u.get("role") == "admin" else "🎓"
                    st.markdown(f"**{role_icon} {u['name']} {u['surname']}**")
                    st.caption(f"📧 {u['email']}")
                    st.caption(f"⭐️ {u.get('points', 0)} баллов")

                    if u["id"] == session["user_id"]:
                        st.info("Это вы", icon="ℹ️")
                    else:
                        if st.button("🗑", key=f"del_u_{start + idx}"):
                            try:
                                asyncio.run(api_delete_user(u["id"]))
                            except Exception as e:
                                st.error(f"Ошибка удаления пользователя: {e}")
                                return
                            st.rerun()

    st.markdown("---")
    col1p, col2p, col3p = st.columns([1, 2, 1])

    with col1p:
        if page > 1:
            if st.button("⬅️ Назад", key="users_prev"):
                session["users_page"] = page - 1
                st.rerun()

    with col2p:
        st.markdown(
            f"<center>Страница {page} из {total_pages}</center>", unsafe_allow_html=True
        )

    with col3p:
        if page < total_pages:
            if st.button("Вперёд ➡️", key="users_next"):
                session["users_page"] = page + 1
                st.rerun()
