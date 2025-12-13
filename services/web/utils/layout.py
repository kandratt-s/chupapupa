import streamlit as st
from state import get_session


def require_auth(expected_role: str | None = None):
    session = get_session()
    if not session["user_id"]:
        st.warning("Вы не авторизованы.")
        st.switch_page("pages/auth.py")
    if expected_role and session["role"] != expected_role:
        st.error(f"Эта страница доступна только для роли: {expected_role}")
        st.stop()
    return session