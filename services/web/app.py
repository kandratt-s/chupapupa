import sys

sys.path.insert(0, r"C:\Dima\Проект питон\chupapupa")

import streamlit as st
import importlib
from state import get_session

st.set_page_config(page_title="Practice Service", layout="wide")

session = get_session()

if "route" not in session:
    session["route"] = "auth"


def go(route: str):
    session["route"] = route
    st.rerun()


def logout():
    session["user_id"] = None
    session["role"] = None
    session["route"] = "auth"
    st.rerun()


# -----------------------------
# Меню
# -----------------------------
st.sidebar.title("Меню")

if not session["user_id"]:
    st.sidebar.button("Авторизация", on_click=lambda: go("auth"))

else:
    if session["role"] == "student":
        st.sidebar.button("📅 Мероприятия", on_click=lambda: go("student_events"))
        st.sidebar.button("📝 Мои заявки", on_click=lambda: go("student_applications"))
        st.sidebar.button("👤 Профиль", on_click=lambda: go("student_profile"))

    elif session["role"] == "admin":
        st.sidebar.markdown("### Мероприятия")
        st.sidebar.button(
            "➕ Создать мероприятие", on_click=lambda: go("admin_events_create")
        )
        st.sidebar.button(
            "📅 Список мероприятий", on_click=lambda: go("admin_events_list")
        )

        st.sidebar.markdown("### Пользователи")
        st.sidebar.button(
            "➕ Создать пользователя", on_click=lambda: go("admin_users_create")
        )
        st.sidebar.button(
            "👥 Список пользователей", on_click=lambda: go("admin_users_list")
        )

        st.sidebar.markdown("### Заявки")
        st.sidebar.button("📥 Заявки", on_click=lambda: go("admin_applications"))

        st.sidebar.markdown("---")
        st.sidebar.button("👤 Профиль", on_click=lambda: go("admin_profile"))

    st.sidebar.button("🚪 Выйти", on_click=logout)

# -----------------------------
# Маршруты → модули
# -----------------------------
ROUTES = {
    "auth": "services.web.views.auth",
    "student_events": "services.web.views.student_events",
    "student_applications": "services.web.views.student_applications",
    "student_profile": "services.web.views.student_profile",
    "admin_events_create": "services.web.views.admin_events_create",
    "admin_events_list": "services.web.views.admin_events_list",
    "admin_applications": "services.web.views.admin_applications",
    "admin_users_create": "services.web.views.admin_users_create",
    "admin_users_list": "services.web.views.admin_users_list",
    "admin_profile": "services.web.views.admin_profile",
}

module_name = ROUTES.get(session["route"], "services.web.views.auth")
module = importlib.import_module(module_name)
module.render()