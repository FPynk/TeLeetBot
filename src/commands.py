from aiogram import Router, types, F
from aiogram.filters import Command
import time, sqlite3
from . import db

router = Router()
START_TS = int(time.time())

def _format_uptime(seconds: int) -> str:
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    mins, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours}h")
    if mins or hours or days:
        parts.append(f"{mins}m")
    parts.append(f"{secs}s")
    return " ".join(parts)

@router.message(Command("start"))
async def start(m: types.Message):
    await m.answer("Hi! Link your LeetCode with /link leetcode_username. In groups, use /join to enter the leaderboard.")

@router.message(Command("help"))
async def help(m: types.Message):
    uptime = _format_uptime(int(time.time()) - START_TS)
    await m.answer(
        "Hello! Link your LeetCode with /link leetcode_username. Then, in each group, use /join to begin showing your progress and enter the leaderboard.\n"
        f"Uptime: {uptime}"
    )

@router.message(Command("link"))
async def link(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2:
        return await m.reply("Usage: /link leetcode_username")

    lc = parts[1].strip()
    tg_id = m.from_user.id
    tg_un = m.from_user.username or ""

    try:
        # Create or update your row
        db.upsert_user(tg_id, tg_un, lc)

        # Optional: start tracking from NOW to avoid immediate backfill announcements
        db.get_or_set_last_seen(lc, int(time.time()))

        await m.reply(f"Linked to LeetCode: {lc}. Please use /join now. I'll track first-time ACs and post to groups you join.")
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
            return await m.reply("You don't have a linked LeetCode account.")
        lc = row[0]
        # remove memberships, user, and last_seen
        c.execute("DELETE FROM memberships WHERE telegram_user_id=?", (tg_id,))
        c.execute("DELETE FROM users WHERE telegram_user_id=?", (tg_id,))
        c.execute("DELETE FROM last_seen WHERE lc_username=?", (lc,))
    await m.reply("Unlinked. You can /link another LeetCode username anytime.")

# Used to swap the telegram_user_id and telegram_username to new ones based on the LC account
# To fix an issue where telegram_user_id would change over time for some reason
@router.message(Command("relink"))
async def relink(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2:
        return await m.reply("Usage: /relink leetcode_username")

    lc = parts[1].strip()
    tg_id = m.from_user.id
    tg_un = m.from_user.username or ""

    msg = None
    with db.conn() as c:
        # Look up the existing Telegram owner for this LC username.
        row = c.execute(
            "SELECT telegram_user_id FROM users WHERE lc_username=?",
            (lc,),
        ).fetchone()
        if not row:
            # LC username isn't linked yet.
            msg = "That LeetCode username isn't linked yet. Use /link leetcode_username first."
        else:
            old_tg_id = row[0]
            if old_tg_id == tg_id:
                # Same Telegram user; only refresh their @username.
                c.execute(
                    "UPDATE users SET tg_username=? WHERE telegram_user_id=?",
                    (tg_un, tg_id),
                )
                msg = f"You're already linked to {lc}. I refreshed your Telegram username."
            else:
                # Prevent a Telegram account from linking to two different LC accounts.
                other = c.execute(
                    "SELECT lc_username FROM users WHERE telegram_user_id=?",
                    (tg_id,),
                ).fetchone()
                if other and other[0] != lc:
                    msg = (
                        f"Your Telegram is already linked to LeetCode '{other[0]}'. "
                        f"Use /unlink first, then /relink {lc}."
                    )
                else:
                    # Temporarily disable FK checks to swap user IDs safely.
                    c.execute("PRAGMA foreign_keys=OFF;")
                    # Copy old memberships to the new Telegram ID.
                    c.execute(
                        """
                        INSERT OR IGNORE INTO memberships(chat_id, telegram_user_id)
                        SELECT chat_id, ? FROM memberships WHERE telegram_user_id=?
                        """,
                        (tg_id, old_tg_id),
                    )
                    # Remove memberships attached to the old Telegram ID.
                    c.execute(
                        "DELETE FROM memberships WHERE telegram_user_id=?",
                        (old_tg_id,),
                    )
                    # Move historical completions to the new Telegram ID.
                    c.execute(
                        "UPDATE completions SET telegram_user_id=? WHERE telegram_user_id=?",
                        (tg_id, old_tg_id),
                    )
                    # Update the user row to use the new Telegram ID + username.
                    c.execute(
                        "UPDATE users SET telegram_user_id=?, tg_username=? WHERE lc_username=?",
                        (tg_id, tg_un, lc),
                    )
                    # Restore FK enforcement.
                    c.execute("PRAGMA foreign_keys=ON;")
                    msg = (
                        f"Relinked {lc} to your Telegram account. "
                        "If you were in groups, you're still on their leaderboards."
                    )

    await m.reply(msg)

@router.message(Command("join"))
async def join(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /join inside a group.")
    db.set_chat(m.chat.id, m.chat.title or "")
    db.join_chat(m.chat.id, m.from_user.id)
    await m.reply("You're in! I'll count your first ACs for this chat's weekly board.")

@router.message(Command("leave"))
async def leave(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /leave in the group you want to leave.")
    db.leave_chat(m.chat.id, m.from_user.id)
    await m.reply("Left this chat's leaderboard.")

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
