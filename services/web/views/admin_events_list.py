import streamlit as st
from datetime import datetime
from state import get_session
from services.web.api.local_logic import (
    local_get_all_events,
    local_admin_deactivate_event,
    local_admin_delete_event,
)


def parse_date(date_str: str):
    """Парсинг даты для сортировки."""
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

    # Фильтры
    filter_mode = st.radio(
        "Фильтр",
        ["Все", "Активные", "Завершённые"],
        horizontal=True,
    )

    events = local_get_all_events()

    # Применяем фильтр
    if filter_mode == "Активные":
        events = [e for e in events if e.get("is_active", True)]
    elif filter_mode == "Завершённые":
        events = [e for e in events if not e.get("is_active", True)]

    # Сортировка по дате (от поздней к ранней)
    events = sorted(events, key=lambda e: parse_date(e.get("date", "")), reverse=True)

    if not events:
        st.info("Мероприятий не найдено.")
        return

    for idx, ev in enumerate(events):
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                st.write(f"### {ev['name']}")
                st.write(f"📅 Дата: {ev['date']}")
                st.write(f"📝 {ev.get('description', 'Описание отсутствует')}")

                profile_badge = (
                    "🎯 Профильное" if ev.get("is_profile") else "📘 Непрофильное"
                )
                status_badge = (
                    "🟢 Активно" if ev.get("is_active", True) else "🔴 Завершено"
                )
                st.write(f"{profile_badge} | {status_badge}")

            with col2:
                if ev.get("is_active", True):
                    if st.button("🏁 Завершить", key=f"deact_{idx}_{ev['id']}"):
                        local_admin_deactivate_event(ev["id"])
                        st.success("Мероприятие завершено")
                        st.rerun()

                if st.button("🗑 Удалить", key=f"del_{idx}_{ev['id']}"):
                    local_admin_delete_event(ev["id"])
                    st.warning("Мероприятие удалено")
                    st.rerun()
