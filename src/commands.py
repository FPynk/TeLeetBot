from aiogram import Router, types, F
from aiogram.filters import Command
import time, sqlite3
from . import db

router = Router()

@router.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Hi! Link your LeetCode with /link <username>. In groups, use /join to enter the leaderboard.")

@router.message(Command("link"))
async def link(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2:
        return await m.reply("Usage: /link <leetcode_username>")

    lc = parts[1].strip()
    tg_id = m.from_user.id
    tg_un = m.from_user.username or ""

    try:
        # Create or update your row
        db.upsert_user(tg_id, tg_un, lc)

        # Optional: start tracking from NOW to avoid immediate backfill announcements
        db.get_or_set_last_seen(lc, int(time.time()))

        await m.reply(f"Linked to LeetCode: {lc}. I’ll track first-time ACs and post to groups you join.")
    except sqlite3.IntegrityError as e:
        # This happens if someone else has already linked this lc_username
        if "users.lc_username" in str(e):
            return await m.reply("That LeetCode username is already linked by another Telegram user. "
                                 "Ask them to /unlink first or use a different LeetCode account.")
        raise

@router.message(Command("unlink"))
async def unlink(m: types.Message):
    tg_id = m.from_user.id
    with db.conn() as c:
        # get current lc_username (to clean last_seen)
        row = c.execute("SELECT lc_username FROM users WHERE telegram_user_id=?", (tg_id,)).fetchone()
        if not row:
            return await m.reply("You don’t have a linked LeetCode account.")
        lc = row[0]
        # remove memberships, user, and last_seen
        c.execute("DELETE FROM memberships WHERE telegram_user_id=?", (tg_id,))
        c.execute("DELETE FROM users WHERE telegram_user_id=?", (tg_id,))
        c.execute("DELETE FROM last_seen WHERE lc_username=?", (lc,))
    await m.reply("Unlinked. You can /link another LeetCode username anytime.")

@router.message(Command("join"))
async def join(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /join inside a group.")
    db.set_chat(m.chat.id, m.chat.title or "")
    db.join_chat(m.chat.id, m.from_user.id)
    await m.reply("You’re in! I’ll count your first ACs for this chat’s weekly board.")

@router.message(Command("leave"))
async def leave(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /leave in the group you want to leave.")
    db.leave_chat(m.chat.id, m.from_user.id)
    await m.reply("Left this chat’s leaderboard.")

@router.message(Command("postonsolve"))
async def postflag(m: types.Message):
    if m.chat.type == "private":
        return
    arg = (m.text or "").split()[1:] or []
    if not arg or arg[0].lower() not in ("on","off"):
        return await m.reply("Usage: /postonsolve on|off")
    db.set_chat(m.chat.id, m.chat.title or "", post_on_solve=1 if arg[0]=="on" else 0)
    await m.reply(f"Post-on-solve set to {arg[0]}.")

# /stats and /leaderboard implemented in bot.py where we have scoring/time helpers
