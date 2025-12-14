import streamlit as st
import os
import time
from state import get_session
from services.web.api.local_logic import (
    local_get_active_events,
    local_create_application,
)


def render():
    session = get_session()

    if session["role"] != "student":
        st.error("Доступ запрещён")
        return

    st.title("📅 Мероприятия")

    events = local_get_active_events()

    if not events:
        st.info("Нет активных мероприятий.")
        return

    for idx, ev in enumerate(events):
        with st.container(border=True):
            st.write(f"### {ev['name']}")
            st.write(f"📅 Дата: {ev['date']}")
            st.write(ev.get("description", ""))

            profile_text = (
                "🎯 Профильное" if ev.get("is_profile") else "📘 Непрофильное"
            )
            base = 2
            mult = 1.5 if ev.get("is_profile") else 0.5
            points = int(base * mult)
            st.write(f"{profile_text} | ⭐️ {points} баллов")

            with st.expander("📸 Отметиться"):
                uploaded = st.file_uploader(
                    "Загрузите фото с мероприятия",
                    type=["jpg", "jpeg", "png"],
                    key=f"upload_{idx}_{ev['id']}",
                )

                if uploaded:
                    st.image(uploaded, width=200, caption="Превью")

                    if st.button("📤 Отправить заявку", key=f"submit_{idx}_{ev['id']}"):
                        # Сохраняем фото
                        photos_dir = "services/web/data/photos/events"
                        os.makedirs(photos_dir, exist_ok=True)

                        filename = f"user_{session['user_id']}_event_{ev['id']}_{int(time.time())}.jpg"
                        path = os.path.join(photos_dir, filename)

                        with open(path, "wb") as f:
                            f.write(uploaded.getbuffer())

                        # Создаём заявку (без начисления баллов)
                        local_create_application(
                            user_id=session["user_id"],
                            event_id=ev["id"],
                            photo_path=path,
                        )

                        st.success(
                            "✅ Заявка отправлена! Ожидайте подтверждения администратором."
                        )
                        st.rerun()