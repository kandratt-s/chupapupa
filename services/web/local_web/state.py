import streamlit as st


def get_session():
    if "user_id" not in st.session_state:
        st.session_state["user_id"] = None
        st.session_state["role"] = None
    return st.session_state
