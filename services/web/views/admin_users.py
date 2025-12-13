import streamlit as st
from state import get_session
from services.web.api.local_logic import (
    local_get_all_users,
    local_register_user,
    local_delete_user,
)
from services.web.utils.validators import is_valid_email


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("Пользователи")

    # -----------------------------
    # Создание пользователя
    # -----------------------------
    st.subheader("Создать пользователя")

    name = st.text_input("Имя")
    surname = st.text_input("Фамилия")
    email = st.text_input("Email")
    role = st.selectbox("Роль", ["student", "admin"])
    password = st.text_input("Пароль", type="password")

    if st.button("Создать"):
        if not is_valid_email(email):
            st.error("Некорректный email")
        elif not password.strip():
            st.error("Пароль не может быть пустым")
        else:
            user = local_register_user(name, surname, email, role, password)
            st.success(f"Пользователь создан: {user['email']} ({user['role']})")
            st.rerun()

    st.markdown("---")

    # -----------------------------
    # Список пользователей
    # -----------------------------
    st.subheader("Список пользователей")

    users = local_get_all_users()

    if not users:
        st.info("Пользователей пока нет.")
        return

    for u in users:
        with st.container(border=True):
            st.write(f"### {u['name']} {u['surname']}")
            st.write(f"Email: {u['email']}")
            st.write(f"Роль: {u['role']}")
            st.write(f"Баллы: {u.get('points', 0)}")

            if u["id"] == session["user_id"]:
                st.info("Нельзя удалить самого себя")
            else:
                if st.button("Удалить", key=f"del_user_{u['id']}"):
                    local_delete_user(u["id"])
                    st.warning("Пользователь удалён")
                    st.rerun()
