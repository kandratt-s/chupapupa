import streamlit as st
import os
import time
from services.web.local_web.state import get_session
from services.web.local_web.api.local_logic import (
    local_get_active_events,
    local_create_application,
)


def render():
    session = get_session()

    if session["role"] != "student":
        st.error("Доступ запрещён")
        return

    st.title("📅 Мероприятия")
    st.markdown("---")

    events = local_get_active_events()

    if not events:
        st.info("📭 Нет активных мероприятий.")
        return

    # Ключ для сброса загрузчика
    if "upload_key" not in session:
        session["upload_key"] = 0

    for idx, ev in enumerate(events):
        with st.container(border=True):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.markdown(f"### {ev['name']}")
                st.caption(f"📅 {ev['date']}")
                st.markdown(ev.get("description", ""))

                profile_text = (
                    "🎯 Профильное" if ev.get("is_profile") else "📘 Непрофильное"
                )
                base = 2
                mult = 1.5 if ev.get("is_profile") else 0.5
                points = int(base * mult)
                st.markdown(f"{profile_text} | ⭐️ **{points} баллов**")

            with col2:
                with st.expander("📸 Отметиться"):
                    uploaded = st.file_uploader(
                        "Загрузите фото",
                        type=["jpg", "jpeg", "png"],
                        key=f"upload_{session['upload_key']}_{idx}_{ev['id']}",
                    )

                    if uploaded:
                        st.image(uploaded, width=150)

                        if st.button("📤 Отправить", key=f"submit_{idx}_{ev['id']}"):
                            photos_dir = "services/web/data/photos/events"
                            os.makedirs(photos_dir, exist_ok=True)

                            filename = f"user_{session['user_id']}_event_{ev['id']}_{int(time.time())}.jpg"
                            path = os.path.join(photos_dir, filename)

                            with open(path, "wb") as f:
                                f.write(uploaded.getbuffer())

                            local_create_application(
                                user_id=session["user_id"],
                                event_id=ev["id"],
                                photo_path=path,
                            )

                            st.success("✅ Заявка отправлена!")
                            # Очищаем загрузчик
                            session["upload_key"] += 1
                            st.rerun()
