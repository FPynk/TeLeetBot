import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
assert BOT_TOKEN, "Set BOT_TOKEN in .env"

DEFAULT_TZ = "America/Chicago"
DEFAULT_WEIGHTS = (1, 2, 5)
POLL_SEC = 30  # ~2 min
LC_GRAPHQL = "https://leetcode.com/graphql"