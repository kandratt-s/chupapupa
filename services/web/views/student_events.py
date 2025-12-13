import streamlit as st
import os, time
from state import get_session
from services.web.api.local_logic import (
    local_get_active_events,
    local_create_application,
    local_add_points,
)


def render():
    session = get_session()

    if session["role"] != "student":
        st.error("Доступ запрещён")
        return

    st.title("Мероприятия")

    events = local_get_active_events()

    if not events:
        st.info("Нет активных мероприятий.")
        return

    for idx, ev in enumerate(events):
        with st.container(border=True):
            st.write(f"### {ev['name']}")
            st.write(f"Дата: {ev['date']}")
            st.write(ev.get("description", ""))
            st.write("Профильное мероприятие" if ev["is_profile"] else "Непрофильное")

            with st.expander("Отметиться"):
                uploaded = st.file_uploader(
                    "Загрузите фото",
                    type=["jpg", "jpeg", "png"],
                    key=f"upload_{idx}_{ev['id']}",
                )

                if uploaded:
                    photos_dir = "services/web/data/photos"
                    os.makedirs(photos_dir, exist_ok=True)

                    filename = f"user_{session['user_id']}_event_{ev['id']}_{int(time.time())}.jpg"
                    path = os.path.join(photos_dir, filename)

                    with open(path, "wb") as f:
                        f.write(uploaded.getbuffer())

                    if st.button("Отправить заявку", key=f"submit_{ev['id']}"):
                        local_create_application(
                            user_id=session["user_id"],
                            event_id=ev["id"],
                            photo_path=path,
                        )

                        base = 2
                        mult = 1.5 if ev["is_profile"] else 0.5
                        points = int(base * mult)
                        local_add_points(session["user_id"], points)

                        st.success(f"Заявка отправлена. Начислено {points} баллов.")
                        st.rerun()
