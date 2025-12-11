from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import httpx, asyncio, json, re
from email_validator import validate_email, EmailNotValidError
import hashlib
import time
import os


USER_TOKENS_PATH = "user_tokens.json"
USER_INFO_PATH = "user_info.json"
USER_STATES_PATH = "user_states.json"
BOT_TOKEN = "8105586935:AAFOSia4-_neziYsd02pkp8pBPfbvXQ6hfk"
GATEWAY_URL = "http://localhost:8000"
PHOTOS_DIR = "photos"
EVENTS_PATH = "events.json"


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(dictionary: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=3)


tokens = load(USER_TOKENS_PATH)
user_info = load(USER_INFO_PATH)
user_states = load(USER_STATES_PATH)


def is_authenticated(user_id: str) -> bool:
    try:
        u = tokens.get(user_id)
        return bool(u and u.get("token"))
    except Exception:
        return False


def validate_mail(email: str) -> str:
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError as e:
        return None


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not (re.search(r"[A-Z]", password) or re.search(r"[a-z]", password)):
        return False
    if not (re.search(r"\d", password)):
        return False
    if not re.search(r"[!@#$%^&*]", password):
        return False
    return True


def get_display_name(user_id: str, tg_user: types.User = None) -> str:
    try:
        tok = tokens.get(user_id) or {}
        login = tok.get("login")
        if login and login in user_info:
            fi = user_info.get(login, {})
            fn = fi.get("first_name") or ""
            if fn:
                return fn
    except Exception:
        pass
    if tg_user:
        return getattr(tg_user, "first_name", "Пользователь") or "Пользователь"
    return "Пользователь"


def clear_user_state(user_id: str):
    if user_id in user_states:
        photo_path = user_states[user_id].get("photo_path")
        if photo_path and os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except Exception:
                pass
        try:
            del user_states[user_id]
            save(user_states, USER_STATES_PATH)
        except Exception:
            pass


def build_user_menu(user_id: str):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Отметиться на мероприятии", callback_data="btn_submit_event"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Мои мероприятия", callback_data="btn_my_events"
                )
            ],
            [types.InlineKeyboardButton(text="Профиль", callback_data="btn_profile")],
            [types.InlineKeyboardButton(text="Выйти", callback_data="btn_logout")],
        ]
    )
    return kb


def build_admin_menu(user_id: str):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Создать мероприятие", callback_data="btn_create_event"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Список событий", callback_data="btn_list_events"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Список пользователей", callback_data="btn_list_users"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Удалить событие", callback_data="btn_delete_event"
                )
            ],
            [types.InlineKeyboardButton(text="Профиль", callback_data="btn_profile")],
            [types.InlineKeyboardButton(text="Выйти", callback_data="btn_logout")],
        ]
    )
    return kb


async def show_menu_for_user(message: types.Message, user_id: str):
    try:
        # remove previous prompt message if stored
        prev = user_states.get(user_id, {})
        prev_mid = prev.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
            try:
                del user_states[user_id]["prompt_message_id"]
                save(user_states, USER_STATES_PATH)
            except Exception:
                pass
    except Exception:
        pass

    # if the triggering message is a bot message (callback.message), delete it
    try:
        if getattr(message, "from_user", None) and getattr(message.from_user, "is_bot", False):
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            except Exception:
                pass
    except Exception:
        pass

    # send menu
    user = tokens.get(user_id or "") or {}
    try:
        if user.get("role") == "admin":
            msg = await bot.send_message(chat_id=message.chat.id, text="Выберите действие:", reply_markup=build_admin_menu(user_id))
        else:
            msg = await bot.send_message(chat_id=message.chat.id, text="Выберите действие:", reply_markup=build_user_menu(user_id))
        # store prompt id
        try:
            user_states.setdefault(user_id, {})["prompt_message_id"] = msg.message_id
            save(user_states, USER_STATES_PATH)
        except Exception:
            pass
    except Exception:
        try:
            # fallback to message.answer
            if user.get("role") == "admin":
                await message.answer("Выберите действие:", reply_markup=build_admin_menu(user_id))
            else:
                await message.answer("Выберите действие:", reply_markup=build_user_menu(user_id))
        except Exception:
            pass


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

cancel_btn = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="Отменить", callback_data="btn_cancel")]
    ]
)


@dp.message(Command("start"))
async def start_command(message: types.Message):
    id = str(message.from_user.id)
    name = get_display_name(id, message.from_user)
    current = tokens.get(id)

    if is_authenticated(id):
        if current.get("role") == "admin":
            await message.answer(
                f"{name}, вы авторизованы как админ", reply_markup=build_admin_menu(id)
            )
            return
        else:
            await message.answer(
                f"{name}, вы авторизованы", reply_markup=build_user_menu(id)
            )
            return

    start_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Авторизоваться", callback_data="btn_login"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Зарегистрироваться", callback_data="btn_register"
                )
            ],
        ]
    )

    await message.answer(
        f"{name}, привет! Я бот для учёта посещаемости.\n\nВыберите действие:",
        reply_markup=start_kb,
    )


@dp.message(Command("reset"))
async def reset_state(message: types.Message):
    id = str(message.from_user.id)
    clear_user_state(id)
    await message.answer("Состояние сброшено")


@dp.message(Command("status"))
async def status_command(message: types.Message):
    id = str(message.from_user.id)
    user = tokens.get(id)
    auth = is_authenticated(id)
    if not user:
        await message.answer(f"Auth: {auth}\nNo token record for id {id}.")
        return
    await message.answer(
        f"Auth: {auth}\nLogin: {user.get('login')}\nEmail: {user.get('email')}\nRole: {user.get('role')}\nPractice points: {user.get('practice_points', 0)}"
    )


async def login(message: types.Message):
    id = str(message.from_user.id)
    current = tokens.get(id)
    if is_authenticated(id):
        await message.answer(
            "Вы уже авторизованы. Выйдите, чтобы войти другим аккаунтом."
        )
        return

    user_states[id] = {"state": "waiting_login", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer(
        "Если вы уже авторизованы - введите свой логин \nДля регистрации нового пользователя выберите логин",
        reply_markup=cancel_btn,
    )


@dp.message(
    lambda message: user_states.get(str(message.from_user.id), {}).get("state")
    in (
        "waiting_login",
        "waiting_password",
        "register_waiting_firstname",
        "register_waiting_lastname",
        "register_waiting_email",
        "register_waiting_new_login",
        "register_waiting_password",
    )
)
async def receive_login_or_register(message: types.Message):
    id = str(message.from_user.id)
    user_state = user_states.get(id, {})
    state = user_state.get("state")

    if state == "waiting_login":
        login_input = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass

        if login_input.lower() == "admin":
            user_state["login"] = "admin"
            user_state["is_admin_login"] = True
            user_state["state"] = "waiting_password"
            prev_mid = user_state.get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer("Введите ваш пароль.", reply_markup=cancel_btn)
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            return

        if login_input in user_info:
            user_state["login"] = login_input
            user_state["state"] = "waiting_password"
            prev_mid = user_state.get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer("Введите ваш пароль.", reply_markup=cancel_btn)
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            return

        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["pending_login"] = login_input
        user_state["state"] = "register_waiting_firstname"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer(
            "Новый пользователь. Начнём регистрацию. Введите ваше имя:",
            reply_markup=cancel_btn,
        )
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "waiting_password":
        password = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass

        if user_state.get("is_admin_login"):
            if password != "admin":
                await message.answer("Неверный пароль для admin. Попробуйте снова.")
                return
            email = "admin"
            fake_token = f"ADMIN_{id}_{int(time.time())}"
            prev = tokens.get(id)
            points = (
                prev.get("practice_points", 0)
                if prev and prev.get("email") == email
                else 0
            )
            tokens[id] = {
                "email": email,
                "login": "admin",
                "token": fake_token,
                "role": "admin",
                "practice_points": points,
            }
            save(tokens, USER_TOKENS_PATH)
            prev_mid = user_states.get(id, {}).get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
            clear_user_state(id)
            name = get_display_name(id, message.from_user)
            first = name
            await message.answer(
                f"{first}, авторизация успешна!\n"
                f"Логин: admin\n"
                f"ФИО: {first}\n"
                f"Роль: администратор",
                reply_markup=build_admin_menu(id),
            )
            return

        login = user_state.get("login")
        if not login:
            await message.answer("Неизвестный логин. Начните регистрацию повторно")
            return

        record = user_info.get(login)
        if not record:
            await message.answer("Профиль не найден. Начните регистрацию повторно")
            return

        passwd_hash = hashlib.sha256(password.encode()).hexdigest()
        if record.get("password_hash") != passwd_hash:
            await message.answer("Неверный пароль. Попробуйте снова")
            return

        email = record.get("email")
        fake_token = f"TOKEN_{id}"
        prev = tokens.get(id)
        points = (
            prev.get("practice_points", 0) if prev and prev.get("email") == email else 0
        )
        tokens[id] = {
            "email": email,
            "login": login,
            "token": fake_token,
            "role": record.get("role", "student"),
            "practice_points": points,
        }
        save(tokens, USER_TOKENS_PATH)
        prev = user_states.get(id, {})
        prev_mid = prev.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        clear_user_state(id)
        fn = record.get("first_name", "")
        first = fn or get_display_name(id, message.from_user)
        role = record.get("role", "student")
        if role == "admin":
            await message.answer(
                f"{first}, авторизация успешна!\n"
                f"Логин: {login}\n"
                f"Email: {email}\n"
                f"Роль: {role}",
                reply_markup=build_admin_menu(id),
            )
        else:
            await message.answer(
                f"{first}, авторизация успешна!\n"
                f"Логин: {login}\n"
                f"Email: {email}\n"
                f"Роль: {role}\n"
                f"Баллы практики: {points}",
                reply_markup=build_user_menu(id),
            )
        return

    if state == "register_waiting_firstname":
        user_state["first_name"] = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["state"] = "register_waiting_lastname"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer("Введите вашу фамилию:", reply_markup=cancel_btn)
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_lastname":
        user_state["last_name"] = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["state"] = "register_waiting_email"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer("Введите ваш email:", reply_markup=cancel_btn)
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_email":
        email = message.text.strip()
        if not validate_mail(email):
            await message.answer("Некорректный email. Попробуйте снова.")
            return
        user_state["email"] = email
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        if user_state.get("pending_login"):
            user_state["state"] = "register_waiting_password"
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer(
                "Введите желаемый пароль (минимум 8 символов, буквы, цифры и символ из !@#$%^&*):",
                reply_markup=cancel_btn,
            )
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
        else:
            user_state["state"] = "register_waiting_new_login"
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer(
                "Укажите желаемый логин (username):", reply_markup=cancel_btn
            )
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_new_login":
        desired = message.text.strip()
        if desired.lower() == "admin" or desired in user_info:
            await message.answer("Логин недоступен. Выберите другой логин.")
            return
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["pending_login"] = desired
        user_state["state"] = "register_waiting_password"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer(
            "Введите желаемый пароль (минимум 8 символов, буквы, цифры и символ из !@#$%^&*):",
            reply_markup=cancel_btn,
        )
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_password":
        pwd = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass
        if not validate_password(pwd):
            await message.answer(
                "Некорректный пароль. Пароль должен быть минимум 8 символов, содержать буквы, цифры и один из символов !@#$%^&*."
            )
            return

        login = user_state.get("pending_login")
        if not login:
            await message.answer(
                "Ошибка регистрации: отсутствует логин. Начните заново."
            )
            clear_user_state(id)
            return

        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        user_info[login] = {
            "first_name": user_state.get("first_name", ""),
            "last_name": user_state.get("last_name", ""),
            "email": user_state.get("email", ""),
            "password_hash": pwd_hash,
            "role": "student",
        }
        save(user_info, USER_INFO_PATH)

        fake_token = f"TOKEN_{id}"
        tokens[id] = {
            "email": user_state.get("email", ""),
            "login": login,
            "token": fake_token,
            "role": "student",
            "practice_points": 0,
        }
        save(tokens, USER_TOKENS_PATH)

        try:
            prev_mid = user_states.get(id, {}).get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
        except Exception:
            pass
        clear_user_state(id)

        fn = user_state.get("first_name", "")
        first = fn or get_display_name(id, message.from_user)
        await message.answer(
            f"{first}, регистрация завершена.\n"
            f"Логин: {login}\n"
            f"Email: {user_state.get('email', '')}\n"
            f"Вы автоматически вошли.",
            reply_markup=build_user_menu(id),
        )
        return


async def profile(message: types.Message, user_id: str = None):
    # Accept optional user_id when called from a callback.
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id)
    if not is_authenticated(id):
        await message.answer("Сначала авторизуйтесь через меню (Залогиниться)")
        return

    if user.get("role") == "admin":
        await message.answer(
            f"Профиль:\n" f"Email: {user['email']}\n" f"Роль: {user['role']}"
        )
    else:
        await message.answer(
            f"Профиль:\n"
            f"Email: {user['email']}\n"
            f"Роль: {user['role']}\n"
            f"Баллы практики: {user['practice_points']}"
        )
    try:
        await show_menu_for_user(message, id)
    except Exception:
        pass


async def logout(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    if id in tokens:
        try:
            del tokens[id]
            save(tokens, USER_TOKENS_PATH)
        except Exception:
            pass
    clear_user_state(id)

    start_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Авторизоваться", callback_data="btn_login"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Зарегистрироваться", callback_data="btn_register"
                )
            ],
        ]
    )
    await message.answer("Вы вышли из аккаунта.", reply_markup=start_kb)
    # delete previous prompts and show start menu as a clean message
    try:
        prev = user_states.get(id, {})
        prev_mid = prev.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
            try:
                del user_states[id]["prompt_message_id"]
                save(user_states, USER_STATES_PATH)
            except Exception:
                pass
    except Exception:
        pass
    try:
        # delete triggering bot message if any
        if getattr(message, "from_user", None) and getattr(message.from_user, "is_bot", False):
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
            except Exception:
                pass
    except Exception:
        pass
    try:
        msg = await bot.send_message(chat_id=message.chat.id, text="Вы вышли из аккаунта.", reply_markup=start_kb)
        user_states.setdefault(id or "", {})["prompt_message_id"] = msg.message_id
        save(user_states, USER_STATES_PATH)
    except Exception:
        pass


async def check_events(message: types.Message, user_id: str = None):
    # message may come from callback; user_id is accepted for correctness
    try:
        events = load(EVENTS_PATH)
    except Exception:
        await message.answer("Файл событий не найден или пуст.")
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    if not events:
        await message.answer("Событий не найдено.")
        return

    lines = []
    for i, ev in enumerate(events, start=1):
        name = ev.get("event_name") or "(название не указано)"
        ts = ev.get("timestamp")
        if ts:
            try:
                tstr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            except Exception:
                tstr = str(ts)
        else:
            tstr = "-"
        lines.append(f"{i}. {name} — {tstr}")

    text = "\n".join(lines)
    if len(text) <= 4000:
        await message.answer(text)
    else:
        chunk = []
        cur_len = 0
        for l in lines:
            if cur_len + len(l) + 1 > 3500:
                await message.answer("\n".join(chunk))
                chunk = [l]
                cur_len = len(l) + 1
            else:
                chunk.append(l)
                cur_len += len(l) + 1
        if chunk:
            await message.answer("\n".join(chunk))


async def admin_list_users(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id)
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может использовать эту команду.")
        return

    if not tokens:
        await message.answer("Пользователи не найдены.")
        return

    lines = []
    for uid, info in tokens.items():
        email = info.get("email") or "-"
        role = info.get("role") or "-"
        points = info.get("practice_points", "-")
        has_token = "yes" if info.get("token") else "no"
        lines.append(
            f"{uid}: {email} | role={role} | token={has_token} | points={points}"
        )

    text = "\n".join(lines)
    if len(text) <= 4000:
        await message.answer(text)
    else:
        chunk = []
        cur_len = 0
        for l in lines:
            if cur_len + len(l) + 1 > 3500:
                await message.answer("\n".join(chunk))
                chunk = [l]
                cur_len = len(l) + 1
            else:
                chunk.append(l)
                cur_len += len(l) + 1
        if chunk:
            await message.answer("\n".join(chunk))


async def admin_list_events(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id)
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может использовать эту команду.")
        return

    try:
        events = load(EVENTS_PATH)
    except Exception:
        await message.answer("Файл событий не найден или пуст.")
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    if not events:
        await message.answer("Событий не найдено.")
        return

    lines = []
    for i, ev in enumerate(events, start=1):
        name = ev.get("event_name") or "(название не указано)"
        date = ev.get("event_date") or ev.get("timestamp") or "-"
        creator = ev.get("created_by") or ev.get("user_id") or "-"
        is_profile = ev.get("is_profile")
        tag = "Да" if is_profile else "Нет"
        lines.append(
            f"{i}. {name} | дата: {date} | создал: {creator} | профильное: {tag}"
        )

    text = "\n".join(lines)
    if len(text) <= 4000:
        await message.answer(text)
    else:
        chunk = []
        cur_len = 0
        for l in lines:
            if cur_len + len(l) + 1 > 3500:
                await message.answer("\n".join(chunk))
                chunk = [l]
                cur_len = len(l) + 1
            else:
                chunk.append(l)
                cur_len += len(l) + 1
        if chunk:
            await message.answer("\n".join(chunk))


async def admin_delete_event(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id)
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может выполнять это действие.")
        return

    parts = message.text.strip().split()
    if len(parts) > 1:
        try:
            idx = int(parts[1])
        except Exception:
            await message.answer("Неверный индекс. Используйте: /delete_event <номер>")
            return
        try:
            events = load(EVENTS_PATH)
        except Exception:
            await message.answer("Файл событий не найден или пуст.")
            return

        if isinstance(events, dict):
            events = events.get("events") or []

        if idx < 1 or idx > len(events):
            await message.answer("Индекс вне диапазона.")
            return

        removed = events.pop(idx - 1)
        try:
            with open(EVENTS_PATH, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=3)
        except Exception:
            await message.answer("Ошибка при сохранении файла событий.")
            return

        await message.answer(f"Событие удалено: {removed.get('event_name')}")
        return

    user_states[id] = {"state": "admin_waiting_delete_index", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer(
        "Введите номер события для удаления (см. /list_events):",
        reply_markup=cancel_btn,
    )


from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import httpx, asyncio, json, re
from email_validator import validate_email, EmailNotValidError
import hashlib
import time
import os


USER_TOKENS_PATH = "user_tokens.json"
USER_INFO_PATH = "user_info.json"
USER_STATES_PATH = "user_states.json"
BOT_TOKEN = "8105586935:AAFOSia4-_neziYsd02pkp8pBPfbvXQ6hfk"
GATEWAY_URL = "http://localhost:8000"
PHOTOS_DIR = "photos"
EVENTS_PATH = "events.json"


def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save(dictionary: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=3)


tokens = load(USER_TOKENS_PATH)
user_info = load(USER_INFO_PATH)
user_states = load(USER_STATES_PATH)


def is_authenticated(user_id: str) -> bool:
    try:
        u = tokens.get(user_id)
        return bool(u and u.get("token"))
    except Exception:
        return False


def validate_mail(email: str) -> str:
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError as e:
        return None


def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not (re.search(r"[A-Z]", password) or re.search(r"[a-z]", password)):
        return False
    if not (re.search(r"\d", password)):
        return False
    if not re.search(r"[!@#$%^&*]", password):
        return False
    return True


def get_display_name(user_id: str, tg_user: types.User = None) -> str:
    try:
        tok = tokens.get(user_id) or {}
        login = tok.get("login")
        if login and login in user_info:
            fi = user_info.get(login, {})
            fn = fi.get("first_name") or ""
            if fn:
                return fn
    except Exception:
        pass
    if tg_user:
        return getattr(tg_user, "first_name", "Пользователь") or "Пользователь"
    return "Пользователь"


def clear_user_state(user_id: str):
    if user_id in user_states:
        photo_path = user_states[user_id].get("photo_path")
        if photo_path and os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except Exception:
                pass
        try:
            del user_states[user_id]
            save(user_states, USER_STATES_PATH)
        except Exception:
            pass


def build_user_menu(user_id: str):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Отметиться на мероприятии", callback_data="btn_submit_event"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Мои мероприятия", callback_data="btn_my_events"
                )
            ],
            [types.InlineKeyboardButton(text="Профиль", callback_data="btn_profile")],
            [types.InlineKeyboardButton(text="Выйти", callback_data="btn_logout")],
        ]
    )
    return kb


def build_admin_menu(user_id: str):
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Создать мероприятие", callback_data="btn_create_event"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Список событий", callback_data="btn_list_events"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Список пользователей", callback_data="btn_list_users"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Удалить событие", callback_data="btn_delete_event"
                )
            ],
            [types.InlineKeyboardButton(text="Профиль", callback_data="btn_profile")],
            [types.InlineKeyboardButton(text="Выйти", callback_data="btn_logout")],
        ]
    )
    return kb


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

cancel_btn = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="Отменить", callback_data="btn_cancel")]
    ]
)


@dp.message(Command("start"))
async def start_command(message: types.Message):
    id = str(message.from_user.id)
    name = get_display_name(id, message.from_user)
    current = tokens.get(id)

    if is_authenticated(id):
        if current.get("role") == "admin":
            await message.answer(
                f"{name}, вы авторизованы как админ", reply_markup=build_admin_menu(id)
            )
            return
        else:
            await message.answer(
                f"{name}, вы авторизованы", reply_markup=build_user_menu(id)
            )
            return

    start_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Авторизоваться", callback_data="btn_login"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Зарегистрироваться", callback_data="btn_register"
                )
            ],
        ]
    )

    await message.answer(
        f"{name}, привет! Я бот для учёта посещаемости.\n\nВыберите действие:",
        reply_markup=start_kb,
    )


@dp.message(Command("reset"))
async def reset_state(message: types.Message):
    id = str(message.from_user.id)
    clear_user_state(id)
    await message.answer("Состояние сброшено")


@dp.message(Command("status"))
async def status_command(message: types.Message):
    id = str(message.from_user.id)
    user = tokens.get(id)
    auth = is_authenticated(id)
    if not user:
        await message.answer(f"Auth: {auth}\nNo token record for id {id}.")
        return
    await message.answer(
        f"Auth: {auth}\nLogin: {user.get('login')}\nEmail: {user.get('email')}\nRole: {user.get('role')}\nPractice points: {user.get('practice_points', 0)}"
    )


async def login(message: types.Message):
    id = str(message.from_user.id)
    current = tokens.get(id)
    if is_authenticated(id):
        await message.answer(
            "Вы уже авторизованы. Выйдите, чтобы войти другим аккаунтом."
        )
        return

    user_states[id] = {"state": "waiting_login", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer(
        "Если вы уже авторизованы - введите свой логин \nДля регистрации нового пользователя выберите логин",
        reply_markup=cancel_btn,
    )


@dp.message(
    lambda message: user_states.get(str(message.from_user.id), {}).get("state")
    in (
        "waiting_login",
        "waiting_password",
        "register_waiting_firstname",
        "register_waiting_lastname",
        "register_waiting_email",
        "register_waiting_new_login",
        "register_waiting_password",
    )
)
async def receive_login_or_register(message: types.Message):
    id = str(message.from_user.id)
    user_state = user_states.get(id, {})
    state = user_state.get("state")

    if state == "waiting_login":
        login_input = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass

        if login_input.lower() == "admin":
            user_state["login"] = "admin"
            user_state["is_admin_login"] = True
            user_state["state"] = "waiting_password"
            prev_mid = user_state.get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer("Введите ваш пароль.", reply_markup=cancel_btn)
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            return

        if login_input in user_info:
            user_state["login"] = login_input
            user_state["state"] = "waiting_password"
            prev_mid = user_state.get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer("Введите ваш пароль.", reply_markup=cancel_btn)
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            return

        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["pending_login"] = login_input
        user_state["state"] = "register_waiting_firstname"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer(
            "Новый пользователь. Начнём регистрацию. Введите ваше имя:",
            reply_markup=cancel_btn,
        )
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "waiting_password":
        password = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass

        if user_state.get("is_admin_login"):
            if password != "admin":
                await message.answer("Неверный пароль для admin. Попробуйте снова.")
                return
            email = "admin"
            fake_token = f"ADMIN_{id}_{int(time.time())}"
            prev = tokens.get(id)
            points = (
                prev.get("practice_points", 0)
                if prev and prev.get("email") == email
                else 0
            )
            tokens[id] = {
                "email": email,
                "login": "admin",
                "token": fake_token,
                "role": "admin",
                "practice_points": points,
            }
            save(tokens, USER_TOKENS_PATH)
            prev_mid = user_states.get(id, {}).get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
            clear_user_state(id)
            name = get_display_name(id, message.from_user)
            first = name
            await message.answer(
                f"{first}, авторизация успешна!\n"
                f"Логин: admin\n"
                f"ФИО: {first}\n"
                f"Роль: администратор",
                reply_markup=build_admin_menu(id),
            )
            return

        login = user_state.get("login")
        if not login:
            await message.answer("Неизвестный логин. Начните регистрацию повторно")
            return

        record = user_info.get(login)
        if not record:
            await message.answer("Профиль не найден. Начните регистрацию повторно")
            return

        passwd_hash = hashlib.sha256(password.encode()).hexdigest()
        if record.get("password_hash") != passwd_hash:
            await message.answer("Неверный пароль. Попробуйте снова")
            return

        email = record.get("email")
        fake_token = f"TOKEN_{id}"
        prev = tokens.get(id)
        points = (
            prev.get("practice_points", 0) if prev and prev.get("email") == email else 0
        )
        tokens[id] = {
            "email": email,
            "login": login,
            "token": fake_token,
            "role": record.get("role", "student"),
            "practice_points": points,
        }
        save(tokens, USER_TOKENS_PATH)
        prev = user_states.get(id, {})
        prev_mid = prev.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        clear_user_state(id)
        fn = record.get("first_name", "")
        first = fn or get_display_name(id, message.from_user)
        role = record.get("role", "student")
        if role == "admin":
            await message.answer(
                f"{first}, авторизация успешна!\n"
                f"Логин: {login}\n"
                f"Email: {email}\n"
                f"Роль: {role}",
                reply_markup=build_admin_menu(id),
            )
        else:
            await message.answer(
                f"{first}, авторизация успешна!\n"
                f"Логин: {login}\n"
                f"Email: {email}\n"
                f"Роль: {role}\n"
                f"Баллы практики: {points}",
                reply_markup=build_user_menu(id),
            )
        return

    if state == "register_waiting_firstname":
        user_state["first_name"] = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["state"] = "register_waiting_lastname"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer("Введите вашу фамилию:", reply_markup=cancel_btn)
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_lastname":
        user_state["last_name"] = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["state"] = "register_waiting_email"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer("Введите ваш email:", reply_markup=cancel_btn)
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_email":
        email = message.text.strip()
        if not validate_mail(email):
            await message.answer("Некорректный email. Попробуйте снова.")
            return
        user_state["email"] = email
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        if user_state.get("pending_login"):
            user_state["state"] = "register_waiting_password"
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer(
                "Введите желаемый пароль (минимум 8 символов, буквы, цифры и символ из !@#$%^&*):",
                reply_markup=cancel_btn,
            )
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
        else:
            user_state["state"] = "register_waiting_new_login"
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
            msg = await message.answer(
                "Укажите желаемый логин (username):", reply_markup=cancel_btn
            )
            user_state["prompt_message_id"] = msg.message_id
            user_states[id] = user_state
            save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_new_login":
        desired = message.text.strip()
        if desired.lower() == "admin" or desired in user_info:
            await message.answer("Логин недоступен. Выберите другой логин.")
            return
        try:
            await message.delete()
        except Exception:
            pass
        prev_mid = user_state.get("prompt_message_id")
        if prev_mid:
            try:
                await bot.delete_message(chat_id=message.chat.id, message_id=prev_mid)
            except Exception:
                pass
        user_state["pending_login"] = desired
        user_state["state"] = "register_waiting_password"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        msg = await message.answer(
            "Введите желаемый пароль (минимум 8 символов, буквы, цифры и символ из !@#$%^&*):",
            reply_markup=cancel_btn,
        )
        user_state["prompt_message_id"] = msg.message_id
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        return

    if state == "register_waiting_password":
        pwd = message.text.strip()
        try:
            await message.delete()
        except Exception:
            pass
        if not validate_password(pwd):
            await message.answer(
                "Некорректный пароль. Пароль должен быть минимум 8 символов, содержать буквы, цифры и один из символов !@#$%^&*."
            )
            return

        login = user_state.get("pending_login")
        if not login:
            await message.answer(
                "Ошибка регистрации: отсутствует логин. Начните заново."
            )
            clear_user_state(id)
            return

        pwd_hash = hashlib.sha256(pwd.encode()).hexdigest()
        user_info[login] = {
            "first_name": user_state.get("first_name", ""),
            "last_name": user_state.get("last_name", ""),
            "email": user_state.get("email", ""),
            "password_hash": pwd_hash,
            "role": "student",
        }
        save(user_info, USER_INFO_PATH)

        fake_token = f"TOKEN_{id}"
        tokens[id] = {
            "email": user_state.get("email", ""),
            "login": login,
            "token": fake_token,
            "role": "student",
            "practice_points": 0,
        }
        save(tokens, USER_TOKENS_PATH)

        try:
            prev_mid = user_states.get(id, {}).get("prompt_message_id")
            if prev_mid:
                try:
                    await bot.delete_message(
                        chat_id=message.chat.id, message_id=prev_mid
                    )
                except Exception:
                    pass
        except Exception:
            pass
        clear_user_state(id)

        fn = user_state.get("first_name", "")
        first = fn or get_display_name(id, message.from_user)
        await message.answer(
            f"{first}, регистрация завершена.\n"
            f"Логин: {login}\n"
            f"Email: {user_state.get('email', '')}\n"
            f"Вы автоматически вошли.",
            reply_markup=build_user_menu(id),
        )
        return


async def profile(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id or "")
    if not is_authenticated(id):
        await message.answer("Сначала авторизуйтесь через меню (Залогиниться)")
        return

    if user.get("role") == "admin":
        await message.answer(
            f"Профиль:\n" f"Email: {user['email']}\n" f"Роль: {user['role']}"
        )
    else:
        await message.answer(
            f"Профиль:\n"
            f"Email: {user['email']}\n"
            f"Роль: {user['role']}\n"
            f"Баллы практики: {user['practice_points']}"
        )


async def logout(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    if id and id in tokens:
        try:
            del tokens[id]
            save(tokens, USER_TOKENS_PATH)
        except Exception:
            pass
    clear_user_state(id)

    start_kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Авторизоваться", callback_data="btn_login"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="Зарегистрироваться", callback_data="btn_register"
                )
            ],
        ]
    )
    await message.answer("Вы вышли из аккаунта.", reply_markup=start_kb)


async def check_events(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    try:
        events = load(EVENTS_PATH)
    except Exception:
        await message.answer("Файл событий не найден или пуст.")
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    if not events:
        await message.answer("Событий не найдено.")
        return

    lines = []
    for i, ev in enumerate(events, start=1):
        name = ev.get("event_name") or "(название не указано)"
        ts = ev.get("timestamp")
        if ts:
            try:
                tstr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            except Exception:
                tstr = str(ts)
        else:
            tstr = "-"
        lines.append(f"{i}. {name} — {tstr}")

    text = "\n".join(lines)
    if len(text) <= 4000:
        await message.answer(text)
    else:
        chunk = []
        cur_len = 0
        for l in lines:
            if cur_len + len(l) + 1 > 3500:
                await message.answer("\n".join(chunk))
                chunk = [l]
                cur_len = len(l) + 1
            else:
                chunk.append(l)
                cur_len += len(l) + 1
        if chunk:
            await message.answer("\n".join(chunk))


async def admin_list_users(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id or "")
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может использовать эту команду.")
        return

    if not tokens:
        await message.answer("Пользователи не найдены.")
        return

    lines = []
    for uid, info in tokens.items():
        email = info.get("email") or "-"
        role = info.get("role") or "-"
        points = info.get("practice_points", "-")
        has_token = "yes" if info.get("token") else "no"
        lines.append(
            f"{uid}: {email} | role={role} | token={has_token} | points={points}"
        )

    text = "\n".join(lines)
    if len(text) <= 4000:
        await message.answer(text)
    else:
        chunk = []
        cur_len = 0
        for l in lines:
            if cur_len + len(l) + 1 > 3500:
                await message.answer("\n".join(chunk))
                chunk = [l]
                cur_len = len(l) + 1
            else:
                chunk.append(l)
                cur_len += len(l) + 1
        if chunk:
            await message.answer("\n".join(chunk))


async def admin_list_events(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id or "")
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может использовать эту команду.")
        return

    try:
        events = load(EVENTS_PATH)
    except Exception:
        await message.answer("Файл событий не найден или пуст.")
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    if not events:
        await message.answer("Событий не найдено.")
        return

    lines = []
    for i, ev in enumerate(events, start=1):
        name = ev.get("event_name") or "(название не указано)"
        date = ev.get("event_date") or ev.get("timestamp") or "-"
        creator = ev.get("created_by") or ev.get("user_id") or "-"
        is_profile = ev.get("is_profile")
        tag = "Да" if is_profile else "Нет"
        lines.append(
            f"{i}. {name} | дата: {date} | создал: {creator} | профильное: {tag}"
        )

    text = "\n".join(lines)
    if len(text) <= 4000:
        await message.answer(text)
    else:
        chunk = []
        cur_len = 0
        for l in lines:
            if cur_len + len(l) + 1 > 3500:
                await message.answer("\n".join(chunk))
                chunk = [l]
                cur_len = len(l) + 1
            else:
                chunk.append(l)
                cur_len += len(l) + 1
        if chunk:
            await message.answer("\n".join(chunk))


async def admin_delete_event(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id or "")
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может выполнять это действие.")
        return

    parts = message.text.strip().split()
    if len(parts) > 1:
        try:
            idx = int(parts[1])
        except Exception:
            await message.answer("Неверный индекс. Используйте: /delete_event <номер>")
            return
        try:
            events = load(EVENTS_PATH)
        except Exception:
            await message.answer("Файл событий не найден или пуст.")
            return

        if isinstance(events, dict):
            events = events.get("events") or []

        if idx < 1 or idx > len(events):
            await message.answer("Индекс вне диапазона.")
            return

        removed = events.pop(idx - 1)
        try:
            with open(EVENTS_PATH, "w", encoding="utf-8") as f:
                json.dump(events, f, ensure_ascii=False, indent=3)
        except Exception:
            await message.answer("Ошибка при сохранении файла событий.")
            return

        await message.answer(f"Событие удалено: {removed.get('event_name')}")
        return

    user_states[id] = {"state": "admin_waiting_delete_index", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer(
        "Введите номер события для удаления (см. /list_events):",
        reply_markup=cancel_btn,
    )


@dp.message(
    lambda message: user_states.get(str(message.from_user.id), {}).get("state")
    == "admin_waiting_delete_index"
)
async def admin_receive_delete_index(message: types.Message):
    id = str(message.from_user.id)
    user = tokens.get(id)
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может использовать эту команду.")
        return

    try:
        idx = int(message.text.strip())
    except Exception:
        await message.answer("Неверный номер. Введите число.")
        return

    try:
        events = load(EVENTS_PATH)
    except Exception:
        await message.answer("Файл событий не найден или пуст.")
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    if idx < 1 or idx > len(events):
        await message.answer("Индекс вне диапазона.")
        return

    removed = events.pop(idx - 1)
    try:
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=3)
    except Exception:
        await message.answer("Ошибка при сохранении файла событий.")
        return

    clear_user_state(id)
    await message.answer(f"Событие удалено: {removed.get('event_name')}")


async def start_submit_event(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id)
    if not is_authenticated(id):
        await message.answer("Сначала авторизуйтесь через меню (Залогиниться)")
        return

    try:
        events = load(EVENTS_PATH)
    except Exception:
        await message.answer("Файл событий не найден или пуст.")
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    templates = []
    for idx, ev in enumerate(events):
        if ev.get("is_template"):
            templates.append((idx, ev))

    if not templates:
        await message.answer(
            "Пока нет доступных мероприятий. Подождите, пока админ создаст их."
        )
        return

    rows = []
    for idx, ev in templates:
        name = ev.get("event_name") or "(название)"
        date = ev.get("event_date") or ""
        base_points = 2
        multiplier = 1.5 if ev.get("is_profile") else 0.5
        try:
            awarded_preview = int(base_points * multiplier)
        except Exception:
            awarded_preview = base_points
        text = f"{name} — +{awarded_preview} баллов — {date}".strip()
        rows.append(
            [types.InlineKeyboardButton(text=text, callback_data=f"select_event:{idx}")]
        )
    rows.append(
        [types.InlineKeyboardButton(text="Отменить", callback_data="btn_cancel")]
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=rows)

    user_states[id] = {"state": "selecting_event", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer("Выберите мероприятие из списка:", reply_markup=kb)


async def admin_create_event(message: types.Message, user_id: str = None):
    id = user_id or (str(message.from_user.id) if message and getattr(message, "from_user", None) else None)
    user = tokens.get(id)
    if not is_authenticated(id) or user.get("role") != "admin":
        await message.answer("Только администратор может использовать эту команду.")
        return

    user_states[id] = {"state": "admin_waiting_event_name", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer("Введите название мероприятия:", reply_markup=cancel_btn)


@dp.message(
    lambda message: user_states.get(str(message.from_user.id), {}).get("state")
    == "admin_waiting_event_name"
)
async def admin_receive_event_name(message: types.Message):
    id = str(message.from_user.id)
    user_state = user_states.get(id, {})

    event_name = message.text.strip()
    if not event_name:
        await message.answer(
            "Название не может быть пустым. Введите название мероприятия:"
        )
        return

    user_state["admin_event_name"] = event_name
    user_state["state"] = "admin_waiting_event_profile"
    user_states[id] = user_state
    save(user_states, USER_STATES_PATH)

    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="Да", callback_data="admin_profile:yes")],
            [types.InlineKeyboardButton(text="Нет", callback_data="admin_profile:no")],
            [types.InlineKeyboardButton(text="Отменить", callback_data="btn_cancel")],
        ]
    )

    await message.answer("Профильное ли мероприятие?", reply_markup=kb)


@dp.message(
    lambda message: user_states.get(str(message.from_user.id), {}).get("state")
    == "admin_waiting_event_profile"
)
async def admin_receive_event_profile(message: types.Message):
    id = str(message.from_user.id)
    user_state = user_states.get(id, {})
    txt = message.text.strip().lower()
    if txt in ("да", "д", "yes", "y"):
        is_profile = True
    elif txt in ("нет", "н", "no", "n"):
        is_profile = False
    else:
        await message.answer(
            "Неверный формат. Ответьте 'Да' или 'Нет' (или нажмите соответствующую кнопку)."
        )
        return

    user_state["admin_is_profile"] = is_profile
    user_state["state"] = "admin_waiting_event_date"
    user_states[id] = user_state
    save(user_states, USER_STATES_PATH)

    await message.answer(
        "Укажите дату мероприятия в формате ДД-MM-ГГГГ (например, 31-12-2025):",
        reply_markup=cancel_btn,
    )


@dp.message(
    lambda message: user_states.get(str(message.from_user.id), {}).get("state")
    == "admin_waiting_event_date"
)
async def admin_receive_event_date(message: types.Message):
    id = str(message.from_user.id)
    user_state = user_states.get(id, {})

    date_text = message.text.strip()
    try:
        dt = time.strptime(date_text, "%d-%m-%Y")
        event_date_ts = int(time.mktime(dt))
    except Exception:
        await message.answer(
            "Неверный формат даты. Пожалуйста, используйте ДД-ММ-ГГГГ."
        )
        return

    event_name = user_state.get("admin_event_name")
    is_profile = user_state.get("admin_is_profile", False)

    try:
        events = load(EVENTS_PATH)
    except Exception:
        events = []

    if isinstance(events, dict):
        events = events.get("events") if events.get("events") is not None else []
        if events is None:
            events = []

    event_record = {
        "user_id": id,
        "created_by": id,
        "timestamp": int(time.time()),
        "event_name": event_name,
        "is_profile": is_profile,
        "is_template": True,
        "template_id": int(time.time()),
        "event_date": date_text,
        "event_date_ts": event_date_ts,
    }

    events.append(event_record)
    try:
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=3)
    except Exception:
        await message.answer("Ошибка при сохранении события.")
        return

    clear_user_state(id)

    tag = "(профильное)" if is_profile else "(непрофильное)"
    await message.answer(f"Мероприятие создано: {event_name} {tag} на {date_text}")


@dp.callback_query(lambda c: c.data and c.data.startswith("admin_profile:"))
async def admin_profile_callback(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = tokens.get(uid)
    if not is_authenticated(uid) or user.get("role") != "admin":
        await callback.answer("Только администратор может выполнять это действие.")
        return

    state = user_states.get(uid, {})
    if state.get("state") != "admin_waiting_event_profile":
        await callback.answer("Нет ожидаемого запроса на профильность.")
        return

    choice = callback.data.split(":", 1)[1]
    is_profile = True if choice == "yes" else False

    state["admin_is_profile"] = is_profile
    state["state"] = "admin_waiting_event_date"
    user_states[uid] = state
    save(user_states, USER_STATES_PATH)

    try:
        await callback.message.edit_text(
            "Укажите дату мероприятия в формате ДД-MM-ГГГГ (например, 31-12-2025):",
            reply_markup=cancel_btn,
        )
    except Exception:
        await callback.message.answer(
            "Укажите дату мероприятия в формате ДД-MM-ГГГГ (например, 31-12-2025):",
            reply_markup=cancel_btn,
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_submit_event")
async def cb_submit_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)

    if uid in user_states and user_states[uid].get("state") in [
        "waiting_photo",
        "selecting_event",
    ]:
        clear_user_state(uid)

    user = tokens.get(uid)
    if not is_authenticated(uid):
        await callback.message.answer("Сначала авторизуйтесь через меню (Залогиниться)")
        await callback.answer()
        return

    try:
        await start_submit_event(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer(
            "Не удалось открыть список мероприятий. Попробуйте /submit_event."
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_login")
async def cb_btn_login(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user_states[uid] = {"state": "waiting_login", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    try:
        await callback.message.edit_text("Введите логин", reply_markup=cancel_btn)
        user_states[uid]["prompt_message_id"] = callback.message.message_id
        save(user_states, USER_STATES_PATH)
    except Exception:
        msg = await callback.message.answer("Введите логин", reply_markup=cancel_btn)
        user_states[uid]["prompt_message_id"] = msg.message_id
        save(user_states, USER_STATES_PATH)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_register")
async def cb_btn_register(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user_states[uid] = {"state": "register_waiting_firstname", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    try:
        await callback.message.edit_text(
            "Авторизация нового пользователя. Введите ваше имя:",
            reply_markup=cancel_btn,
        )
        user_states[uid]["prompt_message_id"] = callback.message.message_id
        save(user_states, USER_STATES_PATH)
    except Exception:
        msg = await callback.message.answer(
            "Авторизация нового пользователя. Введите ваше имя:",
            reply_markup=cancel_btn,
        )
        user_states[uid]["prompt_message_id"] = msg.message_id
        save(user_states, USER_STATES_PATH)
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_profile")
async def cb_btn_profile(callback: types.CallbackQuery):
    try:
        await profile(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer("Не удалось показать профиль.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_logout")
async def cb_btn_logout(callback: types.CallbackQuery):
    try:
        await logout(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer("Не удалось выйти из аккаунта.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_check_events")
async def cb_btn_check_events(callback: types.CallbackQuery):
    try:
        await check_events(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer("Не удалось получить список событий.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_list_users")
async def cb_btn_list_users(callback: types.CallbackQuery):
    try:
        await admin_list_users(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer("Не удалось получить список пользователей.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_list_events")
async def cb_btn_list_events(callback: types.CallbackQuery):
    try:
        await admin_list_events(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer("Не удалось получить список событий.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_delete_event")
async def cb_btn_delete_event(callback: types.CallbackQuery):
    try:
        await admin_delete_event(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer("Не удалось инициировать удаление события.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_create_event")
async def cb_btn_create_event(callback: types.CallbackQuery):
    try:
        await admin_create_event(callback.message, user_id=str(callback.from_user.id))
    except Exception:
        await callback.message.answer("Не удалось начать создание события.")
    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_my_events")
async def cb_btn_my_events(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    if not is_authenticated(uid):
        await callback.message.answer("Сначала авторизуйтесь через меню")
        await callback.answer()
        return

    try:
        events = load(EVENTS_PATH)
    except Exception:
        await callback.message.answer("Файл событий не найден или пуст.")
        await callback.answer()
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    user_events = [
        ev for ev in events if ev.get("user_id") == uid and not ev.get("is_template")
    ]

    if not user_events:
        await callback.message.answer("У вас пока нет отметок о мероприятиях.")
        await callback.answer()
        return

    lines = []
    for i, ev in enumerate(user_events, start=1):
        name = ev.get("event_name") or "(название не указано)"
        awarded = ev.get("awarded_points", 0)
        ts = ev.get("timestamp")
        if ts:
            try:
                tstr = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
            except Exception:
                tstr = str(ts)
        else:
            tstr = "-"
        lines.append(f"{i}. {name} (+{awarded} баллов) — {tstr}")

    text = "Ваши мероприятия:\n\n" + "\n".join(lines)
    if len(text) <= 4000:
        await callback.message.answer(text)
    else:
        await callback.message.answer("Ваши мероприятия:\n\n" + "\n".join(lines[:20]))

    await callback.answer()


@dp.callback_query(lambda c: c.data == "btn_cancel")
async def cb_cancel(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    clear_user_state(uid)
    await callback.message.answer("Действие отменено.")
    await callback.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith("select_event:"))
async def cb_select_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = tokens.get(uid)
    if not is_authenticated(uid):
        await callback.message.answer("Сначала авторизуйтесь через меню (Залогиниться)")
        await callback.answer()
        return

    try:
        idx = int(callback.data.split(":", 1)[1])
    except Exception:
        await callback.answer("Неверный выбор.")
        return

    try:
        events = load(EVENTS_PATH)
    except Exception:
        await callback.message.answer("Файл событий не найден или пуст.")
        await callback.answer()
        return

    if isinstance(events, dict):
        events = events.get("events") or []

    if idx < 0 or idx >= len(events):
        await callback.answer("Выбранное мероприятие не найдено.")
        return

    ev = events[idx]
    if not ev.get("is_template"):
        await callback.answer("Это мероприятие нельзя выбрать.")
        return

    user_states[uid] = {
        "state": "waiting_photo",
        "timestamp": time.time(),
        "event_name": ev.get("event_name"),
        "is_profile": ev.get("is_profile", False),
        "event_template_index": idx,
    }
    save(user_states, USER_STATES_PATH)

    try:
        await callback.message.edit_text(
            f"Вы выбрали: {ev.get('event_name')}\nТеперь отправьте фото с мероприятия.",
            reply_markup=cancel_btn,
        )
    except Exception:
        await callback.message.answer(
            f"Вы выбрали: {ev.get('event_name')}\nТеперь отправьте фото с мероприятия.",
            reply_markup=cancel_btn,
        )

    await callback.answer()


@dp.message(
    lambda message: message.photo
    and user_states.get(str(message.from_user.id), {}).get("state") == "waiting_photo"
)
async def receive_event_photo(message: types.Message):
    id = str(message.from_user.id)
    user = tokens.get(id)
    if not is_authenticated(id):
        await message.answer("Сначала авторизуйтесь через меню (Залогиниться)")
        return

    photo = message.photo[-1]
    file_id = photo.file_id

    os.makedirs(PHOTOS_DIR, exist_ok=True)

    filename = f"{id}_{int(time.time())}.jpg"
    destination = os.path.join(PHOTOS_DIR, filename)

    try:
        file_obj = await bot.get_file(file_id)
        file_path = file_obj.file_path
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(file_url)
            if resp.status_code == 200:
                with open(destination, "wb") as f:
                    f.write(resp.content)
            else:
                await message.answer("Не удалось скачать файл с сервера Telegram.")
                return
    except Exception:
        try:
            await photo.download(destination_file=destination)
        except Exception:
            await message.answer("Ошибка при сохранении фото.")
            return

    name_display = get_display_name(id, message.from_user)

    try:
        events = load(EVENTS_PATH)
    except Exception:
        events = []

    if isinstance(events, dict):
        events = events.get("events") if events.get("events") is not None else []
        if events is None:
            events = []

    try:
        current = tokens.get(id, {})
        previous_points = current.get("practice_points", 0)
        base_points = 2
        awarded = 0

        tpl_idx = user_states.get(id, {}).get("event_template_index")
        if tpl_idx is not None:
            try:
                if isinstance(events, dict):
                    ev_list = events.get("events") or []
                else:
                    ev_list = events
                ev = ev_list[tpl_idx]
                is_profile = ev.get("is_profile", False)
                multiplier = 1.5 if is_profile else 0.5
                awarded = int(base_points * multiplier)
                event_name = ev.get("event_name")
            except Exception:
                awarded = 0
                event_name = user_states.get(id, {}).get("event_name")
        else:
            is_profile = user_states.get(id, {}).get("is_profile", False)
            multiplier = 1.5 if is_profile else 0.5
            awarded = int(base_points * multiplier)
            event_name = user_states.get(id, {}).get("event_name")

        new_points = previous_points + awarded
        tokens[id]["practice_points"] = new_points
        save(tokens, USER_TOKENS_PATH)
    except Exception:
        previous_points = tokens.get(id, {}).get("practice_points", 0)
        awarded = 0
        new_points = previous_points
        event_name = user_states.get(id, {}).get("event_name")

    bot_reply = f"Фото получено! Спасибо за участие в мероприятии. (+{awarded} баллов). Текущий баланс: {new_points}"

    event_record = {
        "user_id": id,
        "timestamp": int(time.time()),
        "event_name": event_name,
        "is_profile": user_states.get(id, {}).get("is_profile", False),
        "event_template_index": user_states.get(id, {}).get("event_template_index"),
        "awarded_points": awarded,
        "previous_points": previous_points,
        "new_points": new_points,
        "file_id": photo.file_id,
        "file_path": destination,
        "bot_reply": bot_reply,
    }

    events.append(event_record)

    try:
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=3)
    except Exception:
        pass

    clear_user_state(id)

    await message.answer(bot_reply)

async def work():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(work())