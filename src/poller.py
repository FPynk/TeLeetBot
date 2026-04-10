import asyncio
from datetime import datetime, timezone

from . import db
from .config import POLL_SEC
from .leetcode import LCClient
from .scoring import parse_weights, score_counts
from .timeutil import week_window_cst

lc = LCClient()


async def poll_loop():
    await asyncio.sleep(3)
    while True:
        users = db.get_tracked_users()
        for user in users:
            user_id = user["user_id"]
            lc_username = user["lc_username"]
            try:
                cutoff = db.get_or_set_last_seen(lc_username) or 0
                submissions = await lc.recent_ac(lc_username, limit=12)
                new_submissions = [sub for sub in submissions if int(sub["timestamp"]) > cutoff]
                new_submissions.sort(key=lambda sub: sub["timestamp"])
                print(f"[poll] {lc_username}, cutoff={cutoff}, {len(new_submissions)} new")

                for submission in new_submissions:
                    slug = submission["titleSlug"]
                    ts = int(submission["timestamp"])

                    if not db.get_problem(slug):
                        meta = await lc.problem_meta(slug)
                        db.upsert_problem(slug, meta["title"], meta["difficulty"])

                    inserted = db.insert_completion(user_id, slug, ts)
                    if inserted:
                        problem = db.get_problem(slug)
                        title = problem["title"]
                        difficulty = problem["difficulty"]
                        start, end = week_window_cst(datetime.now(timezone.utc))
                        counts = db.get_user_counts(user_id, start, end)

                        from .bot import send_telegram_solve_announcement
                        from .discord_bot import send_discord_solve_announcement

                        for chat in db.get_user_chats(user_id):
                            if not chat["post_on_solve"]:
                                continue
                            total = score_counts(counts, parse_weights(chat["scoring"]))
                            await send_telegram_solve_announcement(
                                chat["chat_id"],
                                user_id,
                                title,
                                difficulty,
                                total,
                                counts,
                            )

                        for channel in db.get_user_discord_channels(user_id):
                            if not channel["post_on_solve"]:
                                continue
                            total = score_counts(counts, parse_weights(channel["scoring"]))
                            await send_discord_solve_announcement(
                                channel["guild_id"],
                                channel["channel_id"],
                                user_id,
                                title,
                                difficulty,
                                total,
                                counts,
                            )

                    db.get_or_set_last_seen(lc_username, ts)
            except Exception as exc:
                print(f"[poll] error lc_username={lc_username} user_id={user_id} exc={exc}")
            await asyncio.sleep(0.5)

        await asyncio.sleep(POLL_SEC)
