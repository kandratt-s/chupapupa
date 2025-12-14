import streamlit as st
from state import get_session
from services.web.api.local_logic import (
    local_get_all_users,
    local_delete_user,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("👥 Список пользователей")

    # Фильтры
    filter_mode = st.radio(
        "Фильтр",
        ["Все", "Студенты", "Администраторы"],
        horizontal=True,
    )

    users = local_get_all_users()

    # Применяем фильтр
    if filter_mode == "Студенты":
        users = [u for u in users if u.get("role") == "student"]
    elif filter_mode == "Администраторы":
        users = [u for u in users if u.get("role") == "admin"]

    # Сортировка по имени
    users = sorted(users, key=lambda u: u.get("name", "").lower())

    if not users:
        st.info("Пользователей не найдено.")
        return

    for idx, u in enumerate(users):
        with st.container(border=True):
            col1, col2, col3 = st.columns([1, 3, 1])

            # Фото профиля
            with col1:
                photo_path = u.get("photo_path")
                if photo_path:
                    try:
                        st.image(photo_path, width=100)
                    except:
                        st.write("📷 Нет фото")
                else:
                    st.write("📷 Нет фото")

            # Информация
            with col2:
                role_icon = "👑" if u.get("role") == "admin" else "🎓"
                st.write(f"### {role_icon} {u['name']} {u['surname']}")
                st.write(f"📧 {u['email']}")
                st.write(f"⭐️ Баллы: {u.get('points', 0)}")

            # Действия
            with col3:
                if u["id"] == session["user_id"]:
                    st.info("Это вы")
                else:
                    if st.button("🗑 Удалить", key=f"del_user_{idx}_{u['id']}"):
                        local_delete_user(u["id"])
                        st.warning(f"Пользователь {u['name']} удалён")
                        st.rerun()
