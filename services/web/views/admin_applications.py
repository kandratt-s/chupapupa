# import sys, os

# ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
# sys.path.insert(0, ROOT)

import streamlit as st
from state import get_session
from services.web.api.local_logic import (
    local_get_all_applications,
    local_get_user,
    local_get_event,
    local_update_application_status,
)


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("Заявки")

    apps = local_get_all_applications()

    if not apps:
        st.info("Заявок пока нет.")
        return

    for app in apps:
        user = local_get_user(app["user_id"])
        ev = local_get_event(app["event_id"])

        with st.container(border=True):
            st.write(f"### Заявка #{app['id']}")

            if ev:
                st.write(f"Мероприятие: **{ev['name']}** ({ev['date']})")

            if user:
                st.write(f"Студент: {user['name']} {user['surname']} ({user['email']})")

            st.write(f"Статус: **{app['status']}**")
            st.write(f"Создано: {app['created_at']}")

            if app.get("photo_path"):
                st.image(app["photo_path"], width=300)

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Одобрить", key=f"approve_{app['id']}"):
                    local_update_application_status(app["id"], "approved")
                    st.success("Заявка одобрена")
                    st.rerun()

            with col2:
                if st.button("Отклонить", key=f"reject_{app['id']}"):
                    local_update_application_status(app["id"], "rejected")
                    st.warning("Заявка отклонена")
                    st.rerun()
