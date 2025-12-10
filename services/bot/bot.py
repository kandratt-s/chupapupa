from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import httpx, asyncio, json, re
from email_validator import validate_email, EmailNotValidError
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

def validate_mail(email: str) -> str:
    try:
        valid = validate_email(email)
        return valid.email
    except EmailNotValidError as e:
        return None

def validate_password(password: str) -> bool:
    if len(password) < 8: return False
    if not (re.search(r"[A-Z]", password) or re.search(r"[a-z]",password)): return False
    if not (re.search(r"\d",password)): return False
    if not re.search(r"[!@#$%^&*]", password): return False
    return True

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

cancel_btn = types.InlineKeyboardMarkup(
    inline_keyboard=[
        [types.InlineKeyboardButton(text="Отменить", callback_data="btn_cancel")]
    ]
)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я бот для учёта посещаемости.\n\n"\
        "Выберите действие в меню")

@dp.message(Command("login"))
async def login(message: types.Message):
    id = str(message.from_user.id)
    user_states[id] = {"state": "waiting_email_password", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer("Введите ваш email.", reply_markup=cancel_btn)


@dp.message(lambda message: user_states.get(str(message.from_user.id), {}).get("state") in ("waiting_email_password", "waiting_password"))
async def receive_email_password(message: types.Message):
    id = str(message.from_user.id)
    user_state = user_states.get(id, {})

    if user_state.get("state") == "waiting_email_password" and "email" not in user_state:
        email = message.text.strip()
        if not validate_mail(email):
            await message.answer("Некорректный email. Попробуйте снова.")
            return
        user_state["email"] = email
        user_state["state"] = "waiting_password"
        user_states[id] = user_state
        save(user_states, USER_STATES_PATH)
        await message.answer("Введите ваш пароль.", reply_markup=cancel_btn)
        return

    if user_state.get("state") == "waiting_password":
        password = message.text.strip()
        if not validate_password(password):
            await message.answer("Некорректный пароль. Пароль должен быть минимум 8 символов, содержать буквы, цифры и один из символов !@#$%^&*.")
            return

        email = user_state.get("email")
        fake_token = f"TOKEN_{id}"
        prev = tokens.get(id)
        if not prev or prev.get("email") != email: points = 0
        else: points = prev.get("practice_points", 0)

        tokens[id] = {
            "email": email,
            "token": fake_token,
            "role": "student",
            "practice_points": points,
        }
        save(tokens, USER_TOKENS_PATH)

        if id in user_states:
            del user_states[id]
            save(user_states, USER_STATES_PATH)

        await message.answer(
            f"Авторизация успешна!\n"
            f"Почта: {email}\n"
            f"Токен: {fake_token}\n"
            f"Баллы практики: {points}"
        )


@dp.message(Command("profile"))
async def profile(message: types.Message):
    id = str(message.from_user.id)
    user = tokens.get(id)
    if not user or not user.get("token"):
        await message.answer("Сначала авторизуйся командой /login")
        return

    await message.answer(
        f"Профиль:\n"
        f"Email: {user['email']}\n"
        f"Роль: {user['role']}\n"
        f"Баллы практики: {user['practice_points']}"
    )

@dp.message(Command("logout"))
async def logout(message: types.Message):
    id = str(message.from_user.id)
    if id in tokens:
        try:
            tokens[id]["token"] = None
            save(tokens, USER_TOKENS_PATH)
        except Exception:
            pass
    if id in user_states:
        try:
            del user_states[id]
            save(user_states, USER_STATES_PATH)
        except Exception:
            pass
    await message.answer("Вы вышли из аккаунта.")


@dp.message(Command("check_events"))
async def check_events(message: types.Message):
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


@dp.message(Command("submit_event"))
async def start_submit_event(message: types.Message):
    id = str(message.from_user.id)
    user = tokens.get(id)
    if not user or not user.get("token"):
        await message.answer("Сначала авторизуйся командой /login")
        return

    user_states[id] = {"state": "waiting_event_name", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    await message.answer("Введите название мероприятия:", reply_markup=cancel_btn)


@dp.callback_query(lambda c: c.data == "btn_submit_event")
async def cb_submit_event(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    user = tokens.get(uid)
    if not user or not user.get("token"):
        await callback.message.answer("Сначала авторизуйся командой /login")
        await callback.answer()
        return

    user_states[uid] = {"state": "waiting_event_name", "timestamp": time.time()}
    save(user_states, USER_STATES_PATH)
    try:
        await callback.message.edit_text("Введите название мероприятия:", reply_markup=cancel_btn)
    except Exception:
        await callback.message.answer("Введите название мероприятия:", reply_markup=cancel_btn)
    await callback.answer()


@dp.message(lambda message: user_states.get(str(message.from_user.id), {}).get("state") == "waiting_event_name")
async def receive_event_name(message: types.Message):
    id = str(message.from_user.id)
    user_state = user_states.get(id, {})

    event_name = message.text.strip()
    if not event_name:
        await message.answer("Название не может быть пустым. Введите название мероприятия:")
        return

    user_state["event_name"] = event_name
    user_state["state"] = "waiting_photo"
    user_states[id] = user_state
    save(user_states, USER_STATES_PATH)

    await message.answer(f"Название сохранено: {event_name}\nТеперь отправьте фото с мероприятия.", reply_markup=cancel_btn)


@dp.callback_query(lambda c: c.data == "btn_cancel")
async def cb_cancel(callback: types.CallbackQuery):
    uid = str(callback.from_user.id)
    state = user_states.get(uid)
    if not state:
        await callback.message.answer("Нечего отменять.")
        await callback.answer()
        return

    photo_path = state.get("photo_path")
    if photo_path and os.path.exists(photo_path):
        try:
            os.remove(photo_path)
        except Exception:
            pass

    try:
        del user_states[uid]
        save(user_states, USER_STATES_PATH)
    except KeyError:
        pass

    await callback.message.answer("Действие отменено.")
    await callback.answer()

@dp.message(lambda message: message.photo and user_states.get(str(message.from_user.id), {}).get("state") == "waiting_photo")
async def receive_event_photo(message: types.Message):
    id = str(message.from_user.id)
    user = tokens.get(id)
    if not user or not user.get("token"):
        await message.answer("Сначала авторизуйся командой /login")
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

    states = user_states.get(id, {})
    states["state"] = "waiting_description"
    states["photo_id"] = photo.file_id
    states["photo_path"] = destination
    states["timestamp"] = time.time()
    user_states[id] = states

    save(user_states, USER_STATES_PATH)

    bot_reply = "Фото получено! Спасибо за участие в мероприятии."
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
        new_points = current.get("practice_points", 0) + 2
        tokens[id]["practice_points"] = new_points
        save(tokens, USER_TOKENS_PATH)
    except Exception:
        new_points = tokens.get(id, {}).get("practice_points", 0)

    bot_reply = f"Фото получено! Спасибо за участие в мероприятии. +2 балла практики. Текущий баланс: {new_points}"

    event_name = user_states.get(id, {}).get("event_name")

    event_record = {
        "user_id": id,
        "timestamp": int(time.time()),
        "event_name": event_name,
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

    await message.answer(bot_reply)

async def work():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(work())
