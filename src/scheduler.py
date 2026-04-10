import asyncio

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from . import db
from .bot import post_telegram_champion, post_telegram_leaderboard
from .discord_bot import post_discord_champion, post_discord_leaderboard
from .leaderboard import rank_rows
from .poller import poll_loop
from .timeutil import week_window_cst

_SCHEDULER = None
_POLL_TASK = None


async def weekly_leaderboards():
    start, end = week_window_cst(datetime.now(timezone.utc))
    print(f"Posting leaderboard snapshot for {start}-{end}")

    for chat in db.get_all_telegram_chats():
        rows = db.weekly_counts(chat["chat_id"], start, end)
        if not rows:
            continue
        scored, _ = rank_rows(rows, chat["scoring"])
        await post_telegram_leaderboard(
            chat["chat_id"],
            chat["scoring"],
            scored,
            "Weekly leaderboard",
        )

    for channel in db.get_all_discord_channels():
        rows = db.weekly_counts_discord(
            channel["guild_id"],
            channel["channel_id"],
            start,
            end,
        )
        if not rows:
            continue
        scored, _ = rank_rows(rows, channel["scoring"])
        await post_discord_leaderboard(
            channel["guild_id"],
            channel["channel_id"],
            channel["scoring"],
            scored,
            "Weekly leaderboard",
        )


async def weekly_champion():
    start, end = week_window_cst(datetime.now(timezone.utc))
    print(f"Announcing weekly champion for window {start}-{end}")

    for chat in db.get_all_telegram_chats():
        rows = db.weekly_counts(chat["chat_id"], start, end)
        if not rows:
            continue
        scored, _ = rank_rows(rows, chat["scoring"])
        await post_telegram_champion(chat["chat_id"], scored)

    for channel in db.get_all_discord_channels():
        rows = db.weekly_counts_discord(
            channel["guild_id"],
            channel["channel_id"],
            start,
            end,
        )
        if not rows:
            continue
        scored, _ = rank_rows(rows, channel["scoring"])
        await post_discord_champion(
            channel["guild_id"],
            channel["channel_id"],
            scored,
        )


async def start_schedulers():
    global _SCHEDULER
    now_time = datetime.now(ZoneInfo("America/Chicago"))
    print(f"[setup] Setting scheduler to America/Chicago time, current time: {now_time}")
    if _SCHEDULER is None:
        _SCHEDULER = AsyncIOScheduler(timezone=ZoneInfo("America/Chicago"))

    scheduler = _SCHEDULER
    scheduler.add_job(
        weekly_leaderboards,
        "cron",
        hour=20,
        timezone="America/Chicago",
        id="weekly_leaderboard",
        name="weekly_leaderboard",
        replace_existing=True,
        misfire_grace_time=86400,
        coalesce=True,
        max_instances=1,
    )

    champ_trig = CronTrigger(
        day_of_week="sun",
        hour=23,
        minute=59,
        timezone=ZoneInfo("America/Chicago"),
    )
    print(f"[setup] weekly champion next: {champ_trig.get_next_fire_time(None, now_time)}")
    scheduler.add_job(
        weekly_champion,
        champ_trig,
        id="weekly_champion",
        replace_existing=True,
        name="weekly_champion",
        misfire_grace_time=86400,
        coalesce=True,
        max_instances=1,
    )

    if not scheduler.running:
        scheduler.start()


def start_poller():
    global _POLL_TASK

    if _POLL_TASK is None or _POLL_TASK.done():
        _POLL_TASK = asyncio.create_task(poll_loop())
