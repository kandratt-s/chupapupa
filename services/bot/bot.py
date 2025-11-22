from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import httpx, asyncio, json, re
from email_validator import validate_email, EmailNotValidError

USER_TOKENS_PATH = "user_tokens.json"
USER_INFO_PATH = "user_info.json"
BOT_TOKEN = "8105586935:AAFOSia4-_neziYsd02pkp8pBPfbvXQ6hfk"
GATEWAY_URL = "http://localhost:8000"

def load(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save(dictionary: dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, indent=3)

tokens = load(USER_TOKENS_PATH)
user_info = load(USER_INFO_PATH)

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

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я бот для учёта посещаемости.\n" \
        "Авторизуйся командой: /login email пароль"
    )

@dp.message(Command("login"))
async def login(message: types.Message):
    try:
        _, email, password = message.text.split()
    except ValueError:
        await message.answer("Используй формат: /login email пароль")
        return

    if not validate_mail(email):
        await message.answer("Некорректный email")
        return

    if not validate_password(password):
        await message.answer("Некорректный пароль")
        return

    '''async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{GATEWAY_URL}/auth/login",
            json={"email":email, "password": password}
        )

    if response.status_code == 200:
        token = response.json().get("access_token")
        if token:
            tokens[str(message.from_user.id)] = token
            save(tokens, USER_TOKENS_PATH)
            await message.answer("Авторизация успешна! Токен сохранён.")
        else:
            await message.answer("Не удалось получить токен")
    else:
        await message.answer("Ошибка авторизации")'''

    # Заглушка: вместо реального токена и профиля
    fake_token = f"TOKEN_{message.from_user.id}"
    tokens[str(message.from_user.id)] = {
        "email": email,
        "token": fake_token,
        "role": "student",
        "practice_points": 10,
    }
    save(tokens, USER_TOKENS_PATH)

    await message.answer(
        f"Авторизация успешна!\n"
        f"Почта: {email}\n"
        f"Токен: {fake_token}\n"
        f"Баллы практики: 10"
    )

@dp.message(Command("profile"))
async def profile(message: types.Message):
    user = tokens.get(str(message.from_user.id))
    if not user:
        await message.answer("Сначала авторизуйся командой /login")
        return

    await message.answer(
        f"Профиль:\n"
        f"Email: {user['email']}\n"
        f"Роль: {user['role']}\n"
        f"Баллы практики: {user['practice_points']}"
    )


'''
@dp.message(Command("profile"))
async def profile(message: types.Message):
    token = tokens.get(str(message.from_user.id))
    if not token:
        await message.answer("Сначала авторизуйся командой /login")
        return

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{GATEWAY_URL}/users/profile", headers={"Authorization": f"Bearer {token}"}
        )

    if response.status_code == 200:
        profile_data = response.json()
        await message.answer(f"Профиль:\n{profile_data}")
    else:
        await message.answer("Ошибка получения профиля")
'''

async def work():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(work())
