import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(BASE_DIR))

import streamlit as st
import importlib
from state import get_session

st.set_page_config(page_title="Practice Service", layout="wide")

session = get_session()

if "route" not in session:
    session["route"] = "auth"


def go(route: str):
    session["route"] = route


def logout():
    session["user_id"] = None
    session["role"] = None
    session["token"] = None
    session["refresh_token"] = None
    session["route"] = "auth"


# -----------------------------
# Меню
# -----------------------------
st.sidebar.title("🎓 Practice Service")
st.sidebar.markdown("---")

if not session["user_id"]:
    if st.sidebar.button("🔐 Авторизация", use_container_width=True):
        go("auth")
        st.rerun()

else:
    if session["role"] == "student":
        st.sidebar.markdown("### 📚 Студент")
        if st.sidebar.button("📅 Мероприятия", use_container_width=True):
            go("student_events")
            st.rerun()
        if st.sidebar.button("📝 Мои заявки", use_container_width=True):
            go("student_applications")
            st.rerun()
        if st.sidebar.button("👤 Профиль", use_container_width=True):
            go("student_profile")
            st.rerun()

    elif session["role"] == "admin":
        st.sidebar.markdown("### 📅 Мероприятия")
        if st.sidebar.button("➕ Создать", use_container_width=True):
            go("admin_events_create")
            st.rerun()
        if st.sidebar.button("📋 Список", use_container_width=True):
            go("admin_events_list")
            st.rerun()

        st.sidebar.markdown("### 👥 Пользователи")
        if st.sidebar.button("➕ Создать", use_container_width=True, key="create_user"):
            go("admin_users_create")
            st.rerun()
        if st.sidebar.button("📋 Список", use_container_width=True, key="list_users"):
            go("admin_users_list")
            st.rerun()

        st.sidebar.markdown("### 📊 Управление")
        if st.sidebar.button("📥 Заявки", use_container_width=True):
            go("admin_applications")
            st.rerun()
        if st.sidebar.button("📈 Статистика", use_container_width=True):
            go("admin_statistics")
            st.rerun()

        st.sidebar.markdown("---")
        if st.sidebar.button(
            "👤 Профиль", use_container_width=True, key="admin_profile"
        ):
            go("admin_profile")
            st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Выйти", use_container_width=True):
        logout()
        st.rerun()

# -----------------------------
# Маршруты
# -----------------------------
ROUTES = {
    "auth": "services.web.gateway_web.views.auth",
    "student_events": "services.web.gateway_web.views.student_events",
    "student_applications": "services.web.gateway_web.views.student_applications",
    "student_profile": "services.web.gateway_web.views.student_profile",
    "admin_events_create": "services.web.gateway_web.views.admin_events_create",
    "admin_events_list": "services.web.gateway_web.views.admin_events_list",
    "admin_applications": "services.web.gateway_web.views.admin_applications",
    "admin_users_create": "services.web.gateway_web.views.admin_users_create",
    "admin_users_list": "services.web.gateway_web.views.admin_users_list",
    "admin_profile": "services.web.gateway_web.views.admin_profile",
    "admin_statistics": "services.web.gateway_web.views.admin_statistics",
}

module_name = ROUTES.get(session["route"], "services.web.gateway_web.views.auth")
module = importlib.import_module(module_name)
module.render()
