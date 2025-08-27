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

async def start_schedulers():
    # 1) keep the LeetCode poller running continuously
    asyncio.get_event_loop().create_task(poll_loop())
    # 2) schedule weekly leaderboard: Monday 09:00 CST
    now_time = datetime.now(ZoneInfo("America/Chicago"))
    print(f"[setup] Setting scheduler to America/Chicago time, current time: {now_time}")
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("America/Chicago"))
    print("[setup] Scheduler adding weekly leaderboards cron job")
    cron = CronTrigger(day_of_week="mon", hour=12, minute=00, start_date=now_time)
    nxt = cron.get_next_fire_time(previous_fire_time=None, now=now_time)
    print(f"[setup] weekly_leaderboard next fire per trigger: {nxt}")

    job = scheduler.add_job(
        weekly_leaderboards,
        cron,
        id="weekly_leaderboard",
        replace_existing=True,
        misfire_grace_time=3600,   # run within an hour if missed
        max_instances=1,
    )

    # Fire once 10s after startup so you can see it working
    # scheduler.add_job(
    #     weekly_leaderboards,
    #     trigger="date",
    #     run_date=datetime.now(ZoneInfo("America/Chicago")) + timedelta(seconds=10),
    #     id="weekly_leaderboard_smoke",
    #     replace_existing=True,
    # )

    scheduler.start()
