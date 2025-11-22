from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import asyncio

TOKEN = "8105586935:AAFOSia4-_neziYsd02pkp8pBPfbvXQ6hfk"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.answer("Привет. Я бот для учета посещаемости мероприятий.")

@dp.message_handler()
async def echo(message: types.Message):
    await message.answer(f"Ты написал: {message.text}")

if __name__ == '__main__':
  executor.start_polling(dp, skip_updates=True)
