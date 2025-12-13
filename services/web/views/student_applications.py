import streamlit as st
from state import get_session
from services.web.api.local_logic import local_get_my_applications


def render():
    session = get_session()

    if session["role"] != "student":
        st.error("Доступ запрещён")
        return

    st.title("Мои заявки")

    apps = local_get_my_applications(session["user_id"])

    if not apps:
        st.info("У вас пока нет заявок.")
        return

    for a in apps:
        with st.container(border=True):
            st.write(f"### {a['event_name']}")
            st.write(f"Создано: {a['created_at']}")

            status = a["status"]

            if status == "approved":
                st.success("Заявка одобрена")
            elif status == "rejected":
                st.error("Заявка отклонена")
            else:
                st.info("Заявка на рассмотрении")

            if a.get("photo_path"):
                st.image(a["photo_path"], width=300)
