# import sys, os

# ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# sys.path.insert(0, ROOT)

import streamlit as st
from state import get_session
from services.web.api.local_logic import local_login, local_register_user
from services.web.utils.validators import is_valid_email


def render():
    session = get_session()
    st.title("Авторизация")

    email = st.text_input("Email")
    password = st.text_input("Пароль", type="password")

    if st.button("Войти"):
        user = local_login(email, password)
        if user:
            session["user_id"] = user["id"]
            session["role"] = user["role"]
            session["route"] = (
                "student_events" if user["role"] == "student" else "admin_events"
            )
            st.rerun()
        else:
            st.error("Неверный email или пароль")
