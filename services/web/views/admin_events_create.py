import streamlit as st
from datetime import date
from state import get_session
from services.web.api.local_logic import local_admin_create_event


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("➕ Создать мероприятие")

    with st.form("create_event_form"):
        name = st.text_input("Название")
        description = st.text_area("Описание")
        is_profile = st.checkbox("Профильное мероприятие", value=True)
        event_date = st.date_input("Дата мероприятия", value=date.today())

        submitted = st.form_submit_button("Создать")

        if submitted:
            if not name.strip():
                st.error("Название не может быть пустым")
            else:
                ev = local_admin_create_event(
                    name=name,
                    description=description,
                    is_profile=is_profile,
                    date_str=str(event_date),
                )
                st.success(f"✅ Мероприятие создано: {ev['name']}")
