import streamlit as st
import os
import time
import asyncio
from state import get_session
from services.web.gateway_web.api.gateway_client import (
    api_get_active_events,
    api_create_application,
)

def render():
    session = get_session()

    if session["role"] != "student":
        st.error("Доступ запрещён")
        return

    st.title("📅 Мероприятия")
    st.markdown("---")

    try:
        events = asyncio.run(api_get_active_events(session.get("token")))
    except Exception as e:
        st.error(f"Ошибка загрузки мероприятий: {e}")
        return

    if not events:
        st.info("📭 Нет активных мероприятий.")
        return

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
                st.markdown("### 📸 Отметиться")
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

                        try:
                            asyncio.run(
                                api_create_application(
                                    token=session.get("token"),
                                    event_id=ev["id"],
                                    photo_path=path,
                                )
                            )
                        except Exception as e:
                            st.error(f"Ошибка отправки заявки: {e}")
                            return

                        st.success("✅ Заявка отправлена!")
                        session["upload_key"] += 1
                        st.rerun()
