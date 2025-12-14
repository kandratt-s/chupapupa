import streamlit as st
from state import get_session
from services.web.api.local_logic import local_login
from services.web.utils.validators import is_valid_email


def render():
    session = get_session()

    st.title("🔐 Авторизация")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.container(border=True):
            st.markdown("### Вход в систему")

            email = st.text_input("📧 Email", placeholder="example@mail.ru")
            password = st.text_input(
                "🔑 Пароль", type="password", placeholder="Введите пароль"
            )

            st.markdown("")

            if st.button("Войти", use_container_width=True, type="primary"):
                if not email.strip():
                    st.error("Введите email")
                elif not password.strip():
                    st.error("Введите пароль")
                else:
                    user = local_login(email, password)
                    if user:
                        session["user_id"] = user["id"]
                        session["role"] = user["role"]
                        # Редирект на профиль
                        if user["role"] == "admin":
                            session["route"] = "admin_profile"
                        else:
                            session["route"] = "student_profile"
                        st.rerun()
                    else:
                        st.error("❌ Неверный email или пароль")

            st.markdown("---")
            st.caption("Practice Service v1.0")
