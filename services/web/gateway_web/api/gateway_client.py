import httpx

GATEWAY_URL = "http://localhost:8000"

async def _request(method: str, service: str, path: str, data=None, params=None):
    url = f"{GATEWAY_URL}/{service}/{path}"
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=url,
            json=data,
            params=params,
        )
    response.raise_for_status()
    return response.json()


# ---------- AUTH / USERS ----------
async def api_register_user(name, surname, email, password, role, photo_path=None):
    return await _request(
        "POST",
        "api",
        "users/create",
        {
            "name": name,
            "surname": surname,
            "email": email,
            "password": password,
            "role": role,
            "photo_path": photo_path,
        },
    )


async def api_login(email: str, password: str):
    return await _request(
        "POST", "auth", "login", {"email": email, "password": password}
    )


async def api_get_user(user_id: int):
    return await _request("GET", "api", f"users/{user_id}")


async def api_get_all_users():
    return await _request("GET", "api", "users")


async def api_delete_user(user_id: int):
    return await _request("DELETE", "api", f"users/{user_id}")


# ---------- EVENTS ----------


async def api_create_event(name: str, description: str, is_profile: bool, date: str):
    return await _request(
        "POST",
        "events",
        "create",
        {
            "name": name,
            "description": description,
            "is_profile": is_profile,
            "date": date,
        },
    )


async def api_get_event(event_id: int):
    return await _request("GET", "events", f"{event_id}")


async def api_get_all_events():
    return await _request("GET", "events", "all")


async def api_deactivate_event(event_id: int):
    return await _request("POST", "events", f"{event_id}/deactivate")


async def api_delete_event(event_id: int):
    return await _request("DELETE", "events", f"{event_id}")


async def api_get_active_events():
    return await _request("GET", "events", "active")


# ---------- APPLICATIONS ----------


async def api_create_application(user_id: int, event_id: int, photo_path: str):
    return await _request(
        "POST",
        "attendance",
        "create",
        {
            "user_id": user_id,
            "event_id": event_id,
            "photo_path": photo_path,
        },
    )


async def api_get_my_applications(user_id: int):
    return await _request("GET", "attendance", f"user/{user_id}")


async def api_get_all_applications():
    return await _request("GET", "attendance", "all")


async def api_approve_application(app_id: int):
    return await _request("POST", "attendance", f"{app_id}/approve")


async def api_reject_application(app_id: int):
    return await _request("POST", "attendance", f"{app_id}/reject")


# ---------- STATISTICS ----------


async def api_get_full_statistics():
    return await _request("GET", "statistics", "full")
