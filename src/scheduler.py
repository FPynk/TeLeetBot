# src/scheduler.py
import asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bot import bot, poll_loop   # reuse your existing poller
from src import db
from src.scoring import parse_weights
from src.timeutil import week_window_cst

_SCHEDULER = None # keep strong reference to prevent garbage collection

async def weekly_leaderboards():
    tz = ZoneInfo("America/Chicago")
    start, end = week_window_cst(datetime.now(timezone.utc))
    # logging
    print(f"Posting weekly leaderboard for {start}-{end}")
    # get all chats + their weights
    with db.conn() as c:
        chats = c.execute("SELECT chat_id, scoring FROM chats").fetchall()

    for chat_id, scoring in chats:
        # get users and problem completions per chat 
        rows = db.weekly_counts(chat_id, start, end)
        if not rows:
            continue
        # aggregate counts per user
        agg = {}
        for uid, diff, cnt in rows:
            agg.setdefault(uid, {"Easy":0,"Medium":0,"Hard":0})
            agg[uid][diff] = cnt

        e, m, h = parse_weights(scoring)
        scored = []
        # calculate total scores
        for uid, counts in agg.items():
            total = counts["Easy"]*e + counts["Medium"]*m + counts["Hard"]*h
            scored.append((uid, total, counts))
        # sort leaderboard
        scored.sort(key=lambda x: (-x[1], -x[2]["Hard"], -x[2]["Medium"]))

        # format leaderboard text
        lines = [f"🏆 <b>Weekly leaderboard</b> (E={e}, M={m}, H={h})\n"]
        rank = 1
        for uid, total, cts in scored[:10]:
            try:
                member = await bot.get_chat_member(chat_id, uid)
                name = f"@{member.user.username}" if member.user.username else (member.user.full_name or str(uid))
            except Exception:
                name = str(uid)
            lines.append(f"{rank}. {name} — <b>{total}</b>  (E:{cts['Easy']} M:{cts['Medium']} H:{cts['Hard']})")
            rank += 1
        try:
            await bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")
        except Exception:
            pass

async def weekly_champion():
    """
    Announces the champion(s) for the current CST/CDT week and prints the top 10.
    Runs every Sunday 23:59 America/Chicago (right before the week window ends).
    """
    tz = ZoneInfo("America/Chicago")
    start, end = week_window_cst(datetime.now(timezone.utc))
    print(f"Announcing weekly champion for window {start}–{end}")

    with db.conn() as c:
        chats = c.execute("SELECT chat_id, scoring FROM chats").fetchall()

    for chat_id, scoring in chats:
        rows = db.weekly_counts(chat_id, start, end)
        if not rows:
            continue

        # aggregate + score (same as leaderboard)
        agg = {}
        for uid, diff, cnt in rows:
            agg.setdefault(uid, {"Easy": 0, "Medium": 0, "Hard": 0})
            agg[uid][diff] = cnt

        e, m, h = parse_weights(scoring)
        scored = []
        for uid, counts in agg.items():
            total = counts["Easy"]*e + counts["Medium"]*m + counts["Hard"]*h
            scored.append((uid, total, counts))
        scored.sort(key=lambda x: (-x[1], -x[2]["Hard"], -x[2]["Medium"]))

        # winners (handle ties on total)
        top_total = scored[0][1]
        winners = [uid for uid, total, _ in scored if total == top_total]

        # names for winners
        winner_names = []
        for uid in winners:
            try:
                member = await bot.get_chat_member(chat_id, uid)
                nm = f"@{member.user.username}" if member.user.username else (member.user.full_name or str(uid))
            except Exception:
                nm = str(uid)
            winner_names.append(nm)

        # message
        lines = [f"👑 <b>Weekly Champion</b> — {' & '.join(winner_names)}  (score <b>{top_total}</b>)\n"]
        lines.append("<i>Final standings</i>")
        rank = 1
        for uid, total, cts in scored[:10]:
            try:
                member = await bot.get_chat_member(chat_id, uid)
                name = f"@{member.user.username}" if member.user.username else (member.user.full_name or str(uid))
            except Exception:
                name = str(uid)
            lines.append(f"{rank}. {name} — <b>{total}</b> (E:{cts['Easy']} M:{cts['Medium']} H:{cts['Hard']})")
            rank += 1

        try:
            await bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")
        except Exception:
            pass

async def start_schedulers():
    global _SCHEDULER
    # 1) keep the LeetCode poller running continuously
    asyncio.get_event_loop().create_task(poll_loop())
    # 2) schedule weekly leaderboard: Monday 09:00 CST
    now_time = datetime.now(ZoneInfo("America/Chicago"))
    print(f"[setup] Setting scheduler to America/Chicago time, current time: {now_time}")
    if _SCHEDULER is None:
        _SCHEDULER = AsyncIOScheduler(timezone=ZoneInfo("America/Chicago"))
    print("[setup] Scheduler adding weekly leaderboards cron job")
    scheduler = _SCHEDULER

    # this works but inconsistent, i dont think its an issue with python or the scheduler?
    # maybe the thread is going to sleep or something to do with how the server handles processes?
    job = scheduler.add_job(
        weekly_leaderboards,
        'cron',
        # day_of_week='sat',
        hour=20,                    # daily 8pm
        timezone="America/Chicago",
        id="weekly_leaderboard",
        name="weekly_leaderboard",
        replace_existing=True,
        misfire_grace_time=86400,   # within 24 hr, still run once
        coalesce=True,              # roll mutiple misses into 1 fire
        max_instances=1,             # no overlaps
    )

    # Sundays at 23:59 — announce the week champion
    tz = ZoneInfo("America/Chicago")
    champ_trig = CronTrigger(day_of_week='sun', hour=23, minute=59, timezone=tz)
    print(f"[setup] weekly champion next: {champ_trig.get_next_fire_time(None, now_time)}")
    scheduler.add_job(
        weekly_champion,
        champ_trig,
        id="weekly_champion",
        replace_existing=True,
        name="weekly_champion",
        misfire_grace_time=86400,   # within 24 hr, still run once
        coalesce=True,              # roll mutiple misses into 1 fire
        max_instances=1,             # no overlaps
    )

    # Fire once 10s after startup so you can see it working
    # scheduler.add_job(
    #     weekly_leaderboards,
    #     trigger="date",
    #     run_date=datetime.now(ZoneInfo("America/Chicago")) + timedelta(seconds=10),
    #     id="weekly_leaderboard_smoke",
    #     replace_existing=True,
    # )
    if not scheduler.running:
        scheduler.start()
