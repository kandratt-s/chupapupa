import streamlit as st
from datetime import datetime
import asyncio
from state import get_session
from api.gateway_client import (
    api_get_all_events,
    api_deactivate_event,
    api_delete_event,
)


def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return datetime.min


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("📅 Список мероприятий")
    st.markdown("---")

    filter_mode = st.radio(
        "Фильтр",
        ["Все", "Активные", "Завершённые"],
        horizontal=True,
    )

    try:
        events = asyncio.run(api_get_all_events(session.get("token")))
    except Exception as e:
        st.error(f"Ошибка загрузки мероприятий: {e}")
        return

    if filter_mode == "Активные":
        events = [e for e in events if e.get("is_active", True)]
    elif filter_mode == "Завершённые":
        events = [e for e in events if not e.get("is_active", True)]

    events = sorted(events, key=lambda e: parse_date(e.get("date", "")), reverse=True)

    total = len(events)
    active = len([e for e in events if e.get("is_active", True)])

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Всего", total)
    with col2:
        st.metric("Активных", active)

    st.markdown("---")

    if not events:
        st.info("📭 Мероприятий не найдено.")
        return

    per_page = 5
    total_pages = (len(events) - 1) // per_page + 1

    if "events_page" not in session:
        session["events_page"] = 1

    page = session["events_page"]
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_events = events[start:end]

    for idx, ev in enumerate(page_events):
        with st.container(border=True):
            col1c, col2c = st.columns([3, 1])

            with col1c:
                status_icon = "🟢" if ev.get("is_active", True) else "🔴"
                profile_icon = "🎯" if ev.get("is_profile") else "📘"

                st.markdown(f"### {status_icon} {ev['name']}")
                st.caption(
                    f"📅 {ev['date']} | {profile_icon} {'Профильное' if ev.get('is_profile') else 'Непрофильное'}"
                )
                st.markdown(f"{ev.get('description', 'Нет описания')}")

            with col2c:
                if ev.get("is_active", True):
                    if st.button("🏁 Завершить", key=f"deact_{start + idx}"):
                        try:
                            asyncio.run(api_deactivate_event(session.get("token"), ev["id"]))
                        except Exception as e:
                            st.error(f"Ошибка деактивации: {e}")
                            return
                        st.rerun()

                if st.button("🗑 Удалить", key=f"del_{start + idx}"):
                    try:
                        asyncio.run(api_delete_event(session.get("token"), ev["id"]))
                    except Exception as e:
                        st.error(f"Ошибка удаления: {e}")
                        return
                    st.rerun()

    st.markdown("---")
    col1p, col2p, col3p = st.columns([1, 2, 1])

    with col1p:
        if page > 1:
            if st.button("⬅️ Назад"):
                session["events_page"] = page - 1
                st.rerun()

    with col2p:
        st.markdown(
            f"<center>Страница {page} из {total_pages}</center>", unsafe_allow_html=True
        )

    with col3p:
        if page < total_pages:
            if st.button("Вперёд ➡️"):
                session["events_page"] = page + 1
                st.rerun()
