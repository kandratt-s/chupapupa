import streamlit as st
from datetime import datetime
import asyncio
from state import get_session
from api.gateway_client import (
    api_get_all_applications,
    api_get_user_admin,
    api_get_event,
    api_approve_application,
    api_reject_application,
    GATEWAY_URL,
)


def parse_datetime(dt_str: str):
    try:
        return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
    except:
        try:
            return datetime.fromisoformat(dt_str)
        except:
            return datetime.min


def render():
    session = get_session()

    if session["role"] != "admin":
        st.error("Доступ запрещён")
        return

    st.title("📥 Заявки")
    st.markdown("---")

    filter_mode = st.radio(
        "Фильтр",
        ["Все", "На рассмотрении", "Одобренные", "Отклонённые"],
        horizontal=True,
    )

    try:
        apps = asyncio.run(api_get_all_applications(session.get("token")))
    except Exception as e:
        st.error(f"Ошибка загрузки заявок: {e}")
        return

    if filter_mode == "На рассмотрении":
        apps = [a for a in apps if a.get("status") == "pending"]
    elif filter_mode == "Одобренные":
        apps = [a for a in apps if a.get("status") == "approved"]
    elif filter_mode == "Отклонённые":
        apps = [a for a in apps if a.get("status") == "rejected"]

    apps = sorted(
        apps, key=lambda a: parse_datetime(a.get("created_at", "")), reverse=True
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 Всего", len(apps))
    with col2:
        pending = len([a for a in apps if a.get("status") == "pending"])
        st.metric("⏳ Ожидают", pending)
    with col3:
        approved = len([a for a in apps if a.get("status") == "approved"])
        st.metric("✅ Одобрено", approved)

    st.markdown("---")

    if not apps:
        st.info("📭 Заявок не найдено.")
        return

    per_page = 3
    total_pages = (len(apps) - 1) // per_page + 1

    if "apps_page" not in session:
        session["apps_page"] = 1

    page = session["apps_page"]
    page = max(1, min(page, total_pages))

    start = (page - 1) * per_page
    end = start + per_page
    page_apps = apps[start:end]

    for idx, app in enumerate(page_apps):
        try:
            user = asyncio.run(api_get_user_admin(session.get("token"), app["user_id"]))
        except Exception:
            user = None
        try:
            event = asyncio.run(api_get_event(session.get("token"), app["event_id"]))
        except Exception:
            event = None

        status = app.get("status", "pending")
        if status == "approved":
            status_badge = "✅ Одобрена"
            border_color = "#2ecc71"
        elif status == "rejected":
            status_badge = "❌ Отклонена"
            border_color = "#e74c3c"
        else:
            status_badge = "⏳ На рассмотрении"
            border_color = "#f39c12"

        st.markdown(
            f"""
            <div style="
                border-left: 5px solid {border_color};
                padding-left: 15px;
                margin-bottom: 10px;
            ">
                <h3>Заявка #{app['id']} — {status_badge}</h3>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            col1c, col2c = st.columns(2)

            with col1c:
                st.markdown("#### 👤 Студент")
                if user:
                    photo_path = user.get("photo_path")
                    if photo_path:
                        try:
                            relative_path = photo_path.replace('/shared/photos/', '')
                            full_url = f"{GATEWAY_URL}/photos/{relative_path}"
                            st.image(full_url, width=200, caption="Фото профиля")
                        except:
                            st.caption("📷 Фото недоступно")
                    else:
                        st.info("📷 Нет фото профиля")

                    st.markdown(f"**{user['name']} {user['surname']}**")
                    st.markdown(f"📧 {user['email']}")
                    st.markdown(f"⭐️ **{user.get('points', 0)}** баллов")
                else:
                    st.error("Студент не найден")

            with col2c:
                st.markdown("#### 📅 Мероприятие")
                if event:
                    st.markdown(f"**{event['name']}**")
                    st.markdown(f"📅 Дата: {event['date']}")
                    profile_text = (
                        "🎯 Профильное"
                        if event.get("is_profile")
                        else "📘 Непрофильное"
                    )
                    st.markdown(profile_text)
                else:
                    st.warning(f"⚠️ {app.get('event_name', 'Мероприятие удалено')}")

            st.markdown("---")

            st.markdown("#### 📸 Фото с мероприятия")
            event_photo = app.get("file_path") or app.get("photo_path")
            print(f"DEBUG: event_photo = {event_photo}")
            if event_photo:
                try:
                    relative_path = event_photo.replace('photos/', '')
                    full_url = f"{GATEWAY_URL}/photos/{relative_path}"
                    print(f"DEBUG: full_url = {full_url}")
                    st.image(full_url, width=400, caption="Фото-подтверждение")
                except:
                    st.warning("📷 Фото недоступно")
            else:
                st.info("📷 Фото не прикреплено")

            st.markdown("---")

            col1b, col2b, col3b = st.columns([2, 1, 1])

            with col1b:
                st.caption(f"🕐 Создано: {app.get('created_at', 'Неизвестно')}")

            if status == "pending":
                with col2b:
                    if st.button(
                        "✅ Принять",
                        key=f"appr_{start + idx}",
                        type="primary",
                        use_container_width=True,
                    ):
                        try:
                            asyncio.run(api_approve_application(session.get("token"), app["id"]))
                        except Exception as e:
                            st.error(f"Ошибка одобрения: {e}")
                            return
                        st.rerun()

                with col3b:
                    if st.button(
                        "❌ Отклонить",
                        key=f"rej_{start + idx}",
                        use_container_width=True,
                    ):
                        try:
                            asyncio.run(api_reject_application(session.get("token"), app["id"]))
                        except Exception as e:
                            st.error(f"Ошибка отклонения: {e}")
                            return
                        st.rerun()

        st.markdown("")
        st.markdown("")

    st.markdown("---")
    col1p, col2p, col3p = st.columns([1, 2, 1])

    with col1p:
        if page > 1:
            if st.button("⬅️ Назад", key="apps_prev"):
                session["apps_page"] = page - 1
                st.rerun()

    with col2p:
        st.markdown(
            f"<center>Страница {page} из {total_pages}</center>", unsafe_allow_html=True
        )

    with col3p:
        if page < total_pages:
            if st.button("Вперёд ➡️", key="apps_next"):
                session["apps_page"] = page + 1
                st.rerun()
