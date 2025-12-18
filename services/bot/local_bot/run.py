# services/bot/local_bot/run.py
import asyncio

from services.bot.local_bot.bot import main

if __name__ == "__main__":
    asyncio.run(main())
