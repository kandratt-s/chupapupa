# import sys, os

# ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# sys.path.insert(0, ROOT)

import streamlit as st
from state import get_session
from services.web.api.local_logic import local_get_user


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("Профиль администратора")

    user = local_get_user(session["user_id"])

    if not user:
        st.error("Пользователь не найден.")
        return

    st.write(f"**Имя:** {user['name']}")
    st.write(f"**Фамилия:** {user['surname']}")
    st.write(f"**Email:** {user['email']}")
    st.write(f"**Роль:** {user['role']}")
