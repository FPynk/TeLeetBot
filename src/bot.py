import asyncio, time
from datetime import datetime, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from .config import BOT_TOKEN, POLL_SEC, DEFAULT_WEIGHTS
from . import db
from .leetcode import LCClient
from .scoring import parse_weights, score_counts
from .timeutil import week_window_cst
from .commands import router as cmd_router

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
dp.include_router(cmd_router)
lc = LCClient()

async def poll_loop():
    # let bot boot up
    await asyncio.sleep(3)
    # main logic loop
    while True:
        users = db.get_tracked_users()  # [(tg_id, lc_username, tg_username)]
        for tg_id, lc_user, tg_un in users:
            tg_un = tg_un or ""
            try:
                # get last processed AC timestamp
                cutoff = db.get_or_set_last_seen(lc_user) or 0

                # filter out for most recent ACs
                subs = await lc.recent_ac(lc_user, limit=12)
                new = [s for s in subs if int(s["timestamp"]) > cutoff]
                print(f"[poll] {lc_user}, cutoff={cutoff}, {len(new)} new")   # logging
                new.sort(key=lambda s: s["timestamp"])  # sort olderst to newest
                for s in new:
                    slug = s["titleSlug"]; ts = int(s["timestamp"])
                    # fetch problem meta/cached
                    from sqlite3 import Row
                    # naive cache check
                    inserted = False

                    # cache meta if needed
                    with db.conn() as c:
                        r = c.execute("SELECT slug FROM problems WHERE slug=?", (slug,)).fetchone()
                    if not r:
                        # incase problem meta data not stored
                        meta = await lc.problem_meta(slug)
                        db.upsert_problem(slug, meta["title"], meta["difficulty"])

                    # insert completion (dedup by UNIQUE(user, slug))
                    inserted = db.insert_completion(tg_id, slug, ts)
                    if inserted:
                        # announce to all chats user joined
                        chats = db.get_user_chats(tg_id)
                        for chat_id, post_on_solve, scoring in chats:
                            # skip if option disabled
                            if not post_on_solve: continue

                            # compute user's week counts quick
                            start,end = week_window_cst(datetime.now(timezone.utc))
                            with db.conn() as c:
                                rows = c.execute("""
                                  SELECT p.difficulty, COUNT(*) FROM completions co
                                  JOIN problems p ON p.slug=co.slug
                                  WHERE co.telegram_user_id=? AND co.solved_at_utc>=? AND co.solved_at_utc<?
                                  GROUP BY 1
                                """,(tg_id,start,end)).fetchall()
                            counts = {r[0]: r[1] for r in rows}
                            e,m,h = parse_weights(scoring)
                            total = score_counts(counts,(e,m,h))
                            # get title/difficulty for message
                            with db.conn() as c:
                                title, diff = c.execute("SELECT title,difficulty FROM problems WHERE slug=?", (slug,)).fetchone()
                            
                            # format message
                            try:
                                member = await bot.get_chat_member(chat_id, tg_id)
                                uname = member.user.username
                                name = f"@{uname}" if uname else (member.user.full_name or "A member")
                            except Exception as e:
                                print(
                                    f"[Error] get_chat_member failed chat_id={chat_id} "
                                    f"tg_id={tg_id} lc_username={lc_user} tg_username={tg_un} exc={e}"
                                )
                                name = f"@{tg_un}" if tg_un else "A member"
                            msg = f"🎉 {name} solved <b>{title}</b> (<i>{diff}</i>).\nWeekly score: <b>{total}</b>  — E:{counts.get('Easy',0)} M:{counts.get('Medium',0)} H:{counts.get('Hard',0)}"
                            try:
                                await bot.send_message(chat_id, msg, parse_mode="HTML", disable_web_page_preview=True)
                            except Exception:
                                pass
                    # bump last_seen as we walk forward
                    db.get_or_set_last_seen(lc_user, ts)
            except Exception:
                # swallow per-user errors; continue
                pass
            await asyncio.sleep(0.5)  # mild pacing
        await asyncio.sleep(POLL_SEC)

@dp.message(Command("leaderboard"))
async def leaderboard(m: types.Message):
    requester = m.from_user
    print(
        f"[Info] /leaderboard used chat_id={m.chat.id} chat_type={m.chat.type} "
        f"chat_title={m.chat.title or ''} from_id={requester.id} "
        f"from_username={requester.username or ''}"
    )
    chat_id = m.chat.id
    # ensure chat exists
    try:
        db.set_chat(chat_id, m.chat.title or "")
        print(f"[Info] leaderboard set_chat ok chat_id={chat_id}")
    except Exception as e:
        print(f"[Error] leaderboard set_chat failed chat_id={chat_id} exc={e}")
        raise
    # get weights
    try:
        with db.conn() as c:
            scoring = c.execute(
                "SELECT scoring FROM chats WHERE chat_id=?", (chat_id,)
            ).fetchone()[0]
        print(f"[Info] leaderboard scoring fetched chat_id={chat_id} scoring={scoring}")
    except Exception as e:
        print(f"[Error] leaderboard scoring fetch failed chat_id={chat_id} exc={e}")
        raise
    e,mw,h = parse_weights(scoring)
    start,end = week_window_cst(datetime.now(timezone.utc))
    try:
        rows = db.weekly_counts(chat_id, start, end)  # [(tg_id, diff, count)]
        print(f"[Info] leaderboard weekly_counts chat_id={chat_id} rows={len(rows)}")
    except Exception as e:
        print(f"[Error] leaderboard weekly_counts failed chat_id={chat_id} exc={e}")
        raise
    # aggregate
    agg = {}
    for uid, diff, c in rows:
        agg.setdefault(uid, {"Easy":0,"Medium":0,"Hard":0})
        agg[uid][diff] = c
    # score
    scored = []
    for uid, counts in agg.items():
        total = counts["Easy"]*e + counts["Medium"]*mw + counts["Hard"]*h
        scored.append((uid, total, counts))
    scored.sort(key=lambda x: (-x[1], -x[2]["Hard"], -x[2]["Medium"]))
    if not scored:
        print(f"[Info] leaderboard no scores chat_id={chat_id}")
        return await m.reply("No solves yet this week.")
    print(f"[Info] leaderboard scored_users chat_id={chat_id} count={len(scored)}")
    lines = [f"🏆 <b>This week's leaderboard</b>\nPoint allocation: (E={e}, M={mw}, H={h})\n"]
    rank = 1
    failed_unames = []
    for uid, total, cts in scored[:10]:
        with db.conn() as c:
            row = c.execute(
                "SELECT tg_username FROM users WHERE telegram_user_id=?",
                (uid,),
            ).fetchone()
        tg_un = row[0] if row and row[0] else ""
        try:
            member = await bot.get_chat_member(chat_id, uid)
            name = f"@{member.user.username}" if member.user.username else (member.user.full_name or str(uid))
        except Exception as e:
            print(
                f"[Error] get_chat_member failed chat_id={chat_id} tg_id={uid} tg_username={tg_un} exc={e}"
            )
            name = f"@{tg_un}" if tg_un else str(uid)
            if tg_un:
                failed_unames.append(f"@{tg_un}")
        lines.append(f"{rank}. {name} — <b>{total}</b> (E:{cts['Easy']} M:{cts['Medium']} H:{cts['Hard']})")
        rank += 1
    if failed_unames:
        lines.append(
            "Debug: " + ", ".join(failed_unames) + ", please use /relink leetcode_username"
        )
    try:
        await m.reply("\n".join(lines), parse_mode="HTML")
        print(f"[Info] leaderboard reply sent chat_id={chat_id}")
    except Exception as e:
        print(f"[Error] leaderboard reply failed chat_id={chat_id} exc={e}")
        raise

@dp.message(Command("stats"))
async def stats(m: types.Message):
    target_id = m.from_user.id
    if m.entities:
        # crude: if they mention a user, use that
        for ent in m.entities:
            if ent.type == "mention":  # e.g., @user
                # resolve not trivial without a mapping; keep MVP simple
                pass
    start,end = week_window_cst(datetime.now(timezone.utc))
    with db.conn() as c:
        rows = c.execute("""
          SELECT p.difficulty, COUNT(*) FROM completions co
          JOIN problems p ON p.slug=co.slug
          WHERE co.telegram_user_id=? GROUP BY 1
        """,(target_id,)).fetchall()
        week = c.execute("""
          SELECT p.difficulty, COUNT(*) FROM completions co
          JOIN problems p ON p.slug=co.slug
          WHERE co.telegram_user_id=? AND co.solved_at_utc>=? AND co.solved_at_utc<?
          GROUP BY 1
        """,(target_id,start,end)).fetchall()
    total = {r[0]: r[1] for r in rows}
    wk = {r[0]: r[1] for r in week}
    await m.reply(f"Lifetime — E:{total.get('Easy',0)} M:{total.get('Medium',0)} H:{total.get('Hard',0)}\n"
                  f"This week — E:{wk.get('Easy',0)} M:{wk.get('Medium',0)} H:{wk.get('Hard',0)}")

async def main():
    db.init()
    loop = asyncio.get_event_loop()
    loop.create_task(poll_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

@dp.message(Command("debug_me"))
async def debug_me(m: types.Message):
    parts = (m.text or "").split()
    lcname = parts[1].strip() if len(parts) == 2 else None

    current_tg_id = m.from_user.id
    current_tg_un = m.from_user.username or ""

    if lcname:
        with db.conn() as c:
            row = c.execute(
                "SELECT telegram_user_id, tg_username, lc_username FROM users WHERE lc_username=?",
                (lcname,),
            ).fetchone()
        if not row:
            return await m.reply(f"No Telegram user linked to LC '{lcname}'.")
        stored_tg_id, stored_tg_un, lc = row
    else:
        with db.conn() as c:
            row = c.execute(
                "SELECT telegram_user_id, tg_username, lc_username FROM users WHERE telegram_user_id=?",
                (current_tg_id,),
            ).fetchone()
        if not row:
            return await m.reply("No mapping found. Link first with /link leetcode_username.")
        stored_tg_id, stored_tg_un, lc = row

    # last_seen
    with db.conn() as c:
        seen = c.execute("SELECT last_seen_ts FROM last_seen WHERE lc_username=?", (lc,)).fetchone()
    ls = seen[0] if seen else 0
    ls_h = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ls)) if ls else "0"

    match = "YES" if stored_tg_id == current_tg_id else "NO"
    lines = [
        f"LC: {lc}",
        f"Stored TG ID: {stored_tg_id}",
        f"Stored TG @: {stored_tg_un or '(none)'}",
        f"Current TG ID: {current_tg_id}",
        f"Current TG @: {current_tg_un or '(none)'}",
        f"Match: {match}",
        f"last_seen: {ls} ({ls_h})",
    ]
    if match == "NO":
        lines.append(f"Suggestion: Use /relink {lc} from the correct account.")

    await m.reply("\n".join(lines))

@dp.message(Command("debug_recent"))
async def debug_recent(m: types.Message):
    # Usage: /debug_recent [leetcode_username]
    parts = (m.text or "").split()
    lcname = parts[1] if len(parts) > 1 else None
    if not lcname:
        # default to the caller's linked LC
        with db.conn() as c:
            r = c.execute("SELECT lc_username FROM users WHERE telegram_user_id=?", (m.from_user.id,)).fetchone()
            if not r:
                return await m.reply("Link first with /link leetcode_username or pass a username: /debug_recent foo")
            lcname = r[0]

    # find the TG user mapped to this LC (for duplicate checks)
    with db.conn() as c:
        r = c.execute("SELECT telegram_user_id FROM users WHERE lc_username=?", (lcname,)).fetchone()
    if not r:
        return await m.reply(f"No Telegram user linked to LC '{lcname}'.")
    tg_id = r[0]

    cutoff = db.get_or_set_last_seen(lcname) or 0
    subs = await lc.recent_ac(lcname, limit=20)
    subs.sort(key=lambda s: int(s["timestamp"]))
    lines = [f"cutoff last_seen={cutoff}"]
    shown = 0
    for s in reversed(subs):  # newest first
        t = int(s["timestamp"]); slug = s["titleSlug"]; title = s["title"]
        # check if first-time completion already recorded
        with db.conn() as c:
            seen = c.execute("SELECT 1 FROM completions WHERE telegram_user_id=? AND slug=?", (tg_id, slug)).fetchone()
        status = []
        status.append("new" if t > cutoff else "old")
        status.append("dup" if seen else "first?")
        lines.append(f"{t}  {title}  [{slug}]  -> {'/'.join(status)}")
        shown += 1
        if shown >= 12: break
    await m.reply("Recent ACs (newest first):\n" + "\n".join(lines[:30]))

@dp.message(Command("debug_lc"))
async def debug_lc(m: types.Message):
    # Usage: /debug_lc leetcode_username
    parts = (m.text or "").split()
    if len(parts) != 2:
        return await m.reply("Usage: /debug_lc leetcode_username")
    lcname = parts[1].strip()

    with db.conn() as c:
        row = c.execute(
            "SELECT telegram_user_id, tg_username FROM users WHERE lc_username=?",
            (lcname,),
        ).fetchone()
    if not row:
        return await m.reply(f"No Telegram user linked to LC '{lcname}'.")
    tg_id, tg_un = row

    # last_seen
    with db.conn() as c:
        seen = c.execute(
            "SELECT last_seen_ts FROM last_seen WHERE lc_username=?",
            (lcname,),
        ).fetchone()
    ls = seen[0] if seen else 0
    ls_h = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ls)) if ls else "0"

    chat_id = m.chat.id
    chat_type = m.chat.type
    try:
        await bot.get_chat_member(chat_id, tg_id)
        gm_status = "OK"
        gm_error = ""
    except Exception as e:
        gm_status = "FAILED"
        gm_error = f"{e}"

    lines = [
        f"LC: {lcname}",
        f"TG ID: {tg_id}",
        f"TG @: {tg_un or '(none)'}",
        f"last_seen: {ls} ({ls_h})",
        f"get_chat_member: {gm_status} (chat_id={chat_id}, chat_type={chat_type})",
    ]
    if gm_error:
        lines.append(f"get_chat_member error: {gm_error}")

    await m.reply("\n".join(lines))
