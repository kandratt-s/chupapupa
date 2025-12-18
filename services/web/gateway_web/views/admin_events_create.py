import streamlit as st
from datetime import date
import asyncio
from state import get_session
from api.gateway_client import api_create_event


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
                try:
                    ev = asyncio.run(
                        api_create_event(
                            token=session.get("token"),
                            name=name,
                            description=description,
                            is_profile=is_profile,
                            date=str(event_date),
                        )
                    )
                except Exception as e:
                    st.error(f"Ошибка создания мероприятия: {e}")
                    return

                st.success(f"✅ Мероприятие создано: {ev['name']}")
