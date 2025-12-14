import streamlit as st
import os
import time
from state import get_session
from services.web.api.local_logic import local_register_user
from services.web.utils.validators import is_valid_email


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("➕ Создать пользователя")

    with st.form("create_user_form"):
        name = st.text_input("Имя")
        surname = st.text_input("Фамилия")
        email = st.text_input("Email")
        role = st.selectbox("Роль", ["student", "admin"])
        password = st.text_input("Пароль", type="password")

        # Фото профиля
        photo = st.file_uploader(
            "📸 Фото профиля",
            type=["jpg", "jpeg", "png"],
            help="Обязательно для студентов",
        )

        submitted = st.form_submit_button("Создать")

        if submitted:
            # Валидация
            if not name.strip():
                st.error("Имя не может быть пустым")
            elif not is_valid_email(email):
                st.error("Некорректный email")
            elif not password.strip():
                st.error("Пароль не может быть пустым")
            elif role == "student" and not photo:
                st.error("Для студента необходимо загрузить фото")
            else:
                # Сохраняем фото
                photo_path = None
                if photo:
                    photos_dir = "services/web/data/photos/profiles"
                    os.makedirs(photos_dir, exist_ok=True)

                    filename = (
                        f"profile_{email.replace('@', '_')}_{int(time.time())}.jpg"
                    )
                    photo_path = os.path.join(photos_dir, filename)

                    with open(photo_path, "wb") as f:
                        f.write(photo.getbuffer())

                # Создаём пользователя
                user = local_register_user(
                    name=name,
                    surname=surname,
                    email=email,
                    role=role,
                    password=password,
                    photo_path=photo_path,
                )
                st.success(
                    f"✅ Пользователь создан: {user['name']} {user['surname']} ({user['role']})"
                )
