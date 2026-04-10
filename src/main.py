import asyncio

from src import db
from src.bot import start_telegram
from src.config import discord_enabled
from src.discord_bot import start_discord, wait_for_discord_ready
from src.scheduler import start_poller, start_schedulers


async def main():
    db.init()

    tasks = [asyncio.create_task(start_telegram(), name="telegram-client")]
    if discord_enabled():
        discord_task = asyncio.create_task(start_discord(), name="discord-client")
        tasks.append(discord_task)
        # Do not start the shared poller until Discord can actually send messages.
        await wait_for_discord_ready(discord_task)
    else:
        print("[Discord] disabled - set DISCORD_BOT_TOKEN and DISCORD_APP_ID to enable it")

    await start_schedulers()
    start_poller()

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    print("Bot running")
    asyncio.run(main())
