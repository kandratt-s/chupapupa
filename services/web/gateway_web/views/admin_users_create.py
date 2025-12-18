import streamlit as st
import os
import asyncio
from state import get_session
from services.web.gateway_web.api.gateway_client import api_register_user


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("➕ Создать пользователя")
    st.markdown("---")

    if "user_form_key" not in session:
        session["user_form_key"] = 0

    with st.form(f"create_user_form_{session['user_form_key']}"):
        name = st.text_input("Имя")
        surname = st.text_input("Фамилия")
        email = st.text_input("Email")
        password = st.text_input("Пароль", type="password")
        role = st.selectbox("Роль", ["student", "admin"])
        photo = st.file_uploader("Фото профиля", type=["jpg", "jpeg", "png"])

        submitted = st.form_submit_button("✅ Создать", use_container_width=True)

        if submitted:
            if (
                not name.strip()
                or not surname.strip()
                or not email.strip()
                or not password.strip()
            ):
                st.error("Все поля обязательны")
                return
            if len(password) < 6:
                st.error("Пароль должен быть не менее 6 символов")
                return

            photo_path = None
            if photo:
                photos_dir = "services/web/data/photos/users"
                os.makedirs(photos_dir, exist_ok=True)
                filename = f"user_{email.replace('@', '_')}.jpg"
                photo_path = f"{photos_dir}/{filename}"
                with open(photo_path, "wb") as f:
                    f.write(photo.getbuffer())

            try:
                user = asyncio.run(
                    api_register_user(
                        token=session.get("token"),
                        name=name,
                        surname=surname,
                        email=email,
                        password=password,
                        role=role,
                        photo_path=photo_path,
                    )
                )
            except Exception as e:
                st.error(f"Ошибка создания пользователя: {e}")
                return

            if not user:
                st.error("Не удалось создать пользователя (проверьте права и корректность данных).")
                return

            st.success(f"✅ Пользователь создан: {user['name']} {user['surname']}")
            session["user_form_key"] += 1
            st.rerun()
