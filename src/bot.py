import html
import time
from datetime import datetime, timezone

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from . import db
from .commands import router as cmd_router
from .config import BOT_TOKEN
from .leaderboard import rank_rows
from .leetcode import LCClient
from .scoring import parse_weights
from .timeutil import week_window_cst

bot = Bot(BOT_TOKEN)
dp = Dispatcher()
dp.include_router(cmd_router)
lc = LCClient()


async def start_telegram():
    await dp.start_polling(bot)


async def resolve_telegram_name(chat_id: int, user_id: int) -> str:
    link = db.get_telegram_link_for_user(user_id)
    identity = db.get_any_platform_identity(user_id)
    lc_username = identity["lc_username"] if identity else str(user_id)

    if not link:
        return html.escape(lc_username)

    tg_id = link["telegram_user_id"]
    tg_username = link["tg_username"] or ""
    try:
        member = await bot.get_chat_member(chat_id, tg_id)
        username = member.user.username
        if username:
            return html.escape(f"@{username}")
        full_name = member.user.full_name or lc_username
        return html.escape(full_name)
    except Exception as exc:
        print(
            f"[Error] telegram get_chat_member failed chat_id={chat_id} "
            f"user_id={user_id} telegram_user_id={tg_id} exc={exc}"
        )
        if tg_username:
            return html.escape(f"@{tg_username}")
        return html.escape(lc_username)


async def send_telegram_solve_announcement(
    chat_id: int,
    user_id: int,
    title: str,
    difficulty: str,
    total: int,
    counts: dict[str, int],
):
    name = await resolve_telegram_name(chat_id, user_id)
    msg = (
        f"{name} solved <b>{html.escape(title)}</b> (<i>{html.escape(difficulty)}</i>).\n"
        f"Weekly score: <b>{total}</b> - "
        f"E:{counts.get('Easy', 0)} M:{counts.get('Medium', 0)} H:{counts.get('Hard', 0)}"
    )
    try:
        await bot.send_message(
            chat_id,
            msg,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as exc:
        print(f"[Error] telegram send_message failed chat_id={chat_id} exc={exc}")


async def _telegram_rank_lines(chat_id: int, scored) -> list[str]:
    lines = []
    rank = 1
    for entry in scored[:10]:
        name = await resolve_telegram_name(chat_id, entry["user_id"])
        counts = entry["counts"]
        lines.append(
            f"{rank}. {name} - <b>{entry['total']}</b> "
            f"(E:{counts['Easy']} M:{counts['Medium']} H:{counts['Hard']})"
        )
        rank += 1
    return lines


async def post_telegram_leaderboard(chat_id: int, scoring: str, scored, header: str):
    if not scored:
        return
    e, m, h = parse_weights(scoring)
    lines = [f"🏆 <b>{html.escape(header)}</b>\nPoint allocation: (E={e}, M={m}, H={h})\n"]
    lines.extend(await _telegram_rank_lines(chat_id, scored))
    try:
        await bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")
    except Exception as exc:
        print(f"[Error] telegram leaderboard send failed chat_id={chat_id} exc={exc}")


async def post_telegram_champion(chat_id: int, scored):
    if not scored:
        return
    top_total = scored[0]["total"]
    winners = [entry for entry in scored if entry["total"] == top_total]
    winner_names = [await resolve_telegram_name(chat_id, entry["user_id"]) for entry in winners]
    lines = [f"👑 <b>Weekly Champion</b> - {' & '.join(winner_names)} (score <b>{top_total}</b>)\n"]
    lines.append("<i>Final standings</i>")
    lines.extend(await _telegram_rank_lines(chat_id, scored))
    try:
        await bot.send_message(chat_id, "\n".join(lines), parse_mode="HTML")
    except Exception as exc:
        print(f"[Error] telegram champion send failed chat_id={chat_id} exc={exc}")


@dp.message(Command("leaderboard"))
async def leaderboard(m: types.Message):
    chat_id = m.chat.id
    db.set_chat(chat_id, m.chat.title or "")
    scoring = db.get_chat_scoring(chat_id) or "1,2,5"
    start, end = week_window_cst(datetime.now(timezone.utc))
    rows = db.weekly_counts(chat_id, start, end)
    scored, weights = rank_rows(rows, scoring)
    if not scored:
        return await m.reply("No solves yet this week.")

    e, mw, h = weights
    lines = [f"🏆 <b>This week's leaderboard</b>\nPoint allocation: (E={e}, M={mw}, H={h})\n"]
    lines.extend(await _telegram_rank_lines(chat_id, scored))
    await m.reply("\n".join(lines), parse_mode="HTML")


@dp.message(Command("stats"))
async def stats(m: types.Message):
    user = db.get_user_by_telegram_id(m.from_user.id)
    if not user:
        return await m.reply("Link first with /link leetcode_username.")

    start, end = week_window_cst(datetime.now(timezone.utc))
    total = db.get_user_counts(user["user_id"])
    week = db.get_user_counts(user["user_id"], start, end)
    await m.reply(
        f"Lifetime - E:{total.get('Easy', 0)} M:{total.get('Medium', 0)} H:{total.get('Hard', 0)}\n"
        f"This week - E:{week.get('Easy', 0)} M:{week.get('Medium', 0)} H:{week.get('Hard', 0)}"
    )


@dp.message(Command("debug_me"))
async def debug_me(m: types.Message):
    parts = (m.text or "").split()
    lcname = parts[1].strip() if len(parts) == 2 else None

    current_tg_id = m.from_user.id
    current_tg_un = m.from_user.username or ""

    if lcname:
        user = db.get_user_by_lc(lcname)
        if not user:
            return await m.reply(f"No user linked to LC '{lcname}'.")
    else:
        user = db.get_user_by_telegram_id(current_tg_id)
        if not user:
            return await m.reply("No mapping found. Link first with /link leetcode_username.")
        user = db.get_user_by_id(user["user_id"])

    link = db.get_telegram_link_for_user(user["id"])
    ls = db.get_or_set_last_seen(user["lc_username"]) or 0
    ls_h = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ls)) if ls else "0"

    stored_tg_id = link["telegram_user_id"] if link else None
    stored_tg_un = link["tg_username"] if link else ""
    match = "YES" if stored_tg_id == current_tg_id else "NO"
    lines = [
        f"LC: {user['lc_username']}",
        f"Stored TG ID: {stored_tg_id or '(none)'}",
        f"Stored TG @: {stored_tg_un or '(none)'}",
        f"Current TG ID: {current_tg_id}",
        f"Current TG @: {current_tg_un or '(none)'}",
        f"Match: {match}",
        f"last_seen: {ls} ({ls_h})",
    ]
    if link and match == "NO":
        lines.append(f"Suggestion: Use /relink {user['lc_username']} from the correct account.")

    await m.reply("\n".join(lines))


@dp.message(Command("debug_recent"))
async def debug_recent(m: types.Message):
    parts = (m.text or "").split()
    lcname = parts[1] if len(parts) > 1 else None
    if not lcname:
        user = db.get_user_by_telegram_id(m.from_user.id)
        if not user:
            return await m.reply("Link first with /link leetcode_username or pass a username: /debug_recent foo")
        lcname = user["lc_username"]

    target = db.get_user_by_lc(lcname)
    if not target:
        return await m.reply(f"No user linked to LC '{lcname}'.")

    cutoff = db.get_or_set_last_seen(lcname) or 0
    subs = await lc.recent_ac(lcname, limit=20)
    subs.sort(key=lambda s: int(s["timestamp"]))
    lines = [f"cutoff last_seen={cutoff}"]
    shown = 0
    for submission in reversed(subs):
        ts = int(submission["timestamp"])
        slug = submission["titleSlug"]
        title = submission["title"]
        with db.conn() as c:
            seen = c.execute(
                """
                SELECT 1 FROM completions
                WHERE user_id=? AND slug=? AND is_deleted=0
                """,
                (target["id"], slug),
            ).fetchone()
        status = ["new" if ts > cutoff else "old", "dup" if seen else "first?"]
        lines.append(f"{ts}  {title}  [{slug}]  -> {'/'.join(status)}")
        shown += 1
        if shown >= 12:
            break

    await m.reply("Recent ACs (newest first):\n" + "\n".join(lines[:30]))


@dp.message(Command("debug_lc"))
async def debug_lc(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2:
        return await m.reply("Usage: /debug_lc leetcode_username")
    lcname = parts[1].strip()

    user = db.get_user_by_lc(lcname)
    if not user:
        return await m.reply(f"No user linked to LC '{lcname}'.")

    link = db.get_telegram_link_for_user(user["id"])
    tg_id = link["telegram_user_id"] if link else None
    tg_un = link["tg_username"] if link else ""
    ls = db.get_or_set_last_seen(lcname) or 0
    ls_h = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(ls)) if ls else "0"

    chat_id = m.chat.id
    chat_type = m.chat.type
    if tg_id is None:
        gm_status = "NO_TELEGRAM_LINK"
        gm_error = ""
    else:
        try:
            await bot.get_chat_member(chat_id, tg_id)
            gm_status = "OK"
            gm_error = ""
        except Exception as exc:
            gm_status = "FAILED"
            gm_error = f"{exc}"

    lines = [
        f"LC: {lcname}",
        f"Shared user ID: {user['id']}",
        f"TG ID: {tg_id or '(none)'}",
        f"TG @: {tg_un or '(none)'}",
        f"last_seen: {ls} ({ls_h})",
        f"get_chat_member: {gm_status} (chat_id={chat_id}, chat_type={chat_type})",
    ]
    if gm_error:
        lines.append(f"get_chat_member error: {gm_error}")

    await m.reply("\n".join(lines))
