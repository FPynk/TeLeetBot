import asyncio

from src import db
from src.bot import start_telegram
from src.config import discord_enabled
from src.discord_bot import start_discord
from src.scheduler import start_schedulers


async def main():
    db.init()
    await start_schedulers()

    tasks = [start_telegram()]
    if discord_enabled():
        tasks.append(start_discord())
    else:
        print("[Discord] disabled - set DISCORD_BOT_TOKEN and DISCORD_APP_ID to enable it")

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    print("Bot running")
    asyncio.run(main())
