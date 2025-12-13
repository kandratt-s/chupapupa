import streamlit as st
from datetime import date
from state import get_session
from services.web.api.local_logic import (
    local_get_all_events,
    local_admin_create_event,
    local_admin_deactivate_event,
    local_admin_delete_event,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("Мероприятия")

    # -----------------------------
    # Создание мероприятия
    # -----------------------------
    st.subheader("Создать новое мероприятие")

    name = st.text_input("Название")
    description = st.text_area("Описание")
    is_profile = st.checkbox("Профильное мероприятие", value=True)
    event_date = st.date_input("Дата мероприятия", value=date.today())

    if st.button("Создать"):
        if not name.strip():
            st.error("Название не может быть пустым")
        else:
            st.session_state["action"] = (
                "create_event",
                {
                    "name": name,
                    "description": description,
                    "is_profile": is_profile,
                    "date_str": str(event_date),
                },
            )

    st.markdown("---")

    # -----------------------------
    # Список мероприятий
    # -----------------------------
    st.subheader("Список мероприятий")

    events = local_get_all_events()

    if not events:
        st.info("Мероприятий пока нет.")
        return

    for idx, ev in enumerate(events):
        with st.container(border=True):
            st.write(f"### {ev['name']}")
            st.write(f"Дата: {ev['date']}")
            st.write(ev.get("description", ""))
            st.write("Профильное" if ev["is_profile"] else "Непрофильное")
            st.write(f"Активно: {ev['is_active']}")

            col1, col2 = st.columns(2)

            with col1:
                if ev["is_active"]:
                    if st.button("Сделать неактивным", key=f"deact_{idx}_{ev['id']}"):
                        st.session_state["action"] = ("deactivate_event", ev["id"])

            with col2:
                if st.button("Удалить", key=f"del_{idx}_{ev['id']}"):
                    st.session_state["action"] = ("delete_event", ev["id"])

    # -----------------------------
    # Выполнение действий после рендера
    # -----------------------------
    action = st.session_state.pop("action", None)
    if action:
        name, value = action
        if name == "create_event":
            ev = local_admin_create_event(**value)
            st.success(f"Мероприятие создано: {ev['name']}")
            st.rerun()
        elif name == "deactivate_event":
            local_admin_deactivate_event(value)
            st.success("Мероприятие деактивировано")
            st.rerun()
        elif name == "delete_event":
            local_admin_delete_event(value)
            st.warning("Мероприятие удалено")
            st.rerun()
