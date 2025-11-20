import telebot
import random

BOT_TOKEN = 'YOUR_BOT_TOKEN'
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
  responses = [
      "Привет!",
      "Hello!",
      "Aloha!",
      "Ola!",
      "Bonjorno!"
  ]
    response = random.choice(responses)
    bot.reply_to(message, response)

if __name__ == '__main__':
  print("Бот запущен!")
  bot.infinity_polling()