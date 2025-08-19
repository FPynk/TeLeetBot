# src/main.py
import asyncio
from src import db
from src.bot import bot, dp
from src.scheduler import start_schedulers

async def main():
    db.init()                 # create tables if missing
    await start_schedulers()  # poller + weekly leaderboard cron
    await dp.start_polling(bot)

if __name__ == "__main__":
    print("Bot running")
    asyncio.run(main())