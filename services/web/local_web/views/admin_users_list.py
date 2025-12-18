import streamlit as st
from services.web.local_web.state import get_session
from services.web.local_web.api.local_logic import (
    local_get_all_users,
    local_delete_user,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("👥 Список пользователей")
    st.markdown("---")

    # Фильтры
    filter_mode = st.radio(
        "Фильтр",
        ["Все", "Студенты", "Администраторы"],
        horizontal=True,
    )

    users = local_get_all_users()

    if filter_mode == "Студенты":
        users = [u for u in users if u.get("role") == "student"]
    elif filter_mode == "Администраторы":
        users = [u for u in users if u.get("role") == "admin"]

    users = sorted(users, key=lambda u: u.get("name", "").lower())

    # Статистика
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

    # Пагинация
    per_page = 6
    total_pages = (len(users) - 1) // per_page + 1

    if "users_page" not in session:
        session["users_page"] = 1

    page = session["users_page"]
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_users = users[start:end]

    # Отображение в сетке
    cols = st.columns(2)

    for idx, u in enumerate(page_users):
        with cols[idx % 2]:
            with st.container(border=True):
                col1, col2 = st.columns([1, 2])

                with col1:
                    photo_path = u.get("photo_path")
                    if photo_path:
                        try:
                            st.image(photo_path, width=80)
                        except:
                            st.markdown("📷")
                    else:
                        st.markdown("### 👤")

                with col2:
                    role_icon = "👑" if u.get("role") == "admin" else "🎓"
                    st.markdown(f"**{role_icon} {u['name']} {u['surname']}**")
                    st.caption(f"📧 {u['email']}")
                    st.caption(f"⭐️ {u.get('points', 0)} баллов")

                    if u["id"] == session["user_id"]:
                        st.info("Это вы", icon="ℹ️")
                    else:
                        if st.button("🗑", key=f"del_u_{start + idx}"):
                            local_delete_user(u["id"])
                            st.rerun()

    # Пагинация
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if page > 1:
            if st.button("⬅️ Назад", key="users_prev"):
                session["users_page"] = page - 1
                st.rerun()

    with col2:
        st.markdown(
            f"<center>Страница {page} из {total_pages}</center>", unsafe_allow_html=True
        )

    with col3:
        if page < total_pages:
            if st.button("Вперёд ➡️", key="users_next"):
                session["users_page"] = page + 1
                st.rerun()
