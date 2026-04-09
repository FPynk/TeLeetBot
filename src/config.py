import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
assert BOT_TOKEN, "Set BOT_TOKEN in .env"

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_APP_ID = os.getenv("DISCORD_APP_ID")
DISCORD_DEV_GUILD_ID = os.getenv("DISCORD_DEV_GUILD_ID")

if bool(DISCORD_BOT_TOKEN) != bool(DISCORD_APP_ID):
    raise AssertionError("Set both DISCORD_BOT_TOKEN and DISCORD_APP_ID, or neither.")

if DISCORD_DEV_GUILD_ID:
    DISCORD_DEV_GUILD_ID = int(DISCORD_DEV_GUILD_ID)

DEFAULT_TZ = "America/Chicago"
DEFAULT_WEIGHTS = (1, 2, 5)
POLL_SEC = 120
LC_GRAPHQL = "https://leetcode.com/graphql"


def discord_enabled() -> bool:
    return bool(DISCORD_BOT_TOKEN and DISCORD_APP_ID)
