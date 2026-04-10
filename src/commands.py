import logging
import sqlite3
import time

from aiogram import Router, types
from aiogram.filters import Command

from . import db

router = Router()
START_TS = int(time.time())
logger = logging.getLogger(__name__)


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


def _log_db_error(command: str, m: types.Message, exc: Exception, lc_username: str | None = None):
    # Keep enough request context in the logs to debug bad migrations or conflicting rows.
    logger.exception(
        "Telegram command failed: command=%s chat_id=%s chat_type=%s from_id=%s "
        "from_username=%s lc_username=%s error=%s",
        command,
        m.chat.id if m.chat else None,
        m.chat.type if m.chat else None,
        m.from_user.id if m.from_user else None,
        m.from_user.username if m.from_user else None,
        lc_username,
        exc,
    )


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

    lc_username = parts[1].strip()
    try:
        # The DB layer now owns all link/switch logic so Telegram and Discord stay consistent.
        ok, msg = db.link_telegram_account(
            m.from_user.id,
            m.from_user.username or "",
            lc_username,
        )
    except sqlite3.IntegrityError as exc:
        # Surface a useful user reply, but keep the detailed failure in server logs.
        _log_db_error("/link", m, exc, lc_username)
        return await m.reply(
            "Link failed because the database found a conflicting Telegram or LeetCode mapping. "
            "If this keeps happening after /debug_me, check the server logs."
        )
    except Exception as exc:
        _log_db_error("/link", m, exc, lc_username)
        return await m.reply("Link failed due to a database error. Please try again.")
    await m.reply(msg)


@router.message(Command("unlink"))
async def unlink(m: types.Message):
    try:
        # Unlink removes only the Telegram side unless this was the user's last remaining platform link.
        ok, msg = db.unlink_telegram_account(m.from_user.id)
    except sqlite3.IntegrityError as exc:
        _log_db_error("/unlink", m, exc)
        return await m.reply(
            "Unlink failed because the database found conflicting rows. Check the server logs."
        )
    except Exception as exc:
        _log_db_error("/unlink", m, exc)
        return await m.reply("Unlink failed due to a database error. Please try again.")
    await m.reply(msg)


@router.message(Command("relink"))
async def relink(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2:
        return await m.reply("Usage: /relink leetcode_username")

    lc_username = parts[1].strip()
    try:
        # /relink is now focused on repairing a broken Telegram mapping to an existing LC user.
        ok, msg = db.relink_telegram_account(
            m.from_user.id,
            m.from_user.username or "",
            lc_username,
        )
    except sqlite3.IntegrityError as exc:
        _log_db_error("/relink", m, exc, lc_username)
        return await m.reply(
            "Relink failed because the database found a conflicting Telegram or LeetCode mapping. "
            "If this keeps happening after /debug_me, check the server logs."
        )
    except Exception as exc:
        _log_db_error("/relink", m, exc, lc_username)
        return await m.reply("Relink failed due to a database error. Please try again.")
    await m.reply(msg)


@router.message(Command("join"))
async def join(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /join inside a group.")

    try:
        db.set_chat(m.chat.id, m.chat.title or "")
        if not db.join_chat(m.chat.id, m.from_user.id):
            return await m.reply("Link your LeetCode first with /link leetcode_username.")
    except sqlite3.IntegrityError as exc:
        _log_db_error("/join", m, exc)
        return await m.reply(
            "Join failed because the database found conflicting membership rows. Check the server logs."
        )
    except Exception as exc:
        _log_db_error("/join", m, exc)
        return await m.reply("Join failed due to a database error. Please try again.")
    await m.reply("You're in! I'll count your first ACs for this chat's weekly board.")


@router.message(Command("leave"))
async def leave(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /leave in the group you want to leave.")

    try:
        if not db.leave_chat(m.chat.id, m.from_user.id):
            return await m.reply("Link your LeetCode first with /link leetcode_username.")
    except sqlite3.IntegrityError as exc:
        _log_db_error("/leave", m, exc)
        return await m.reply(
            "Leave failed because the database found conflicting membership rows. Check the server logs."
        )
    except Exception as exc:
        _log_db_error("/leave", m, exc)
        return await m.reply("Leave failed due to a database error. Please try again.")
    await m.reply("Left this chat's leaderboard.")


@router.message(Command("postonsolve"))
async def postflag(m: types.Message):
    if m.chat.type == "private":
        return

    arg = (m.text or "").split()[1:] or []
    if not arg or arg[0].lower() not in ("on", "off"):
        return await m.reply("Usage: /postonsolve on|off")

    try:
        db.set_chat(
            m.chat.id,
            m.chat.title or "",
            post_on_solve=1 if arg[0].lower() == "on" else 0,
        )
    except sqlite3.IntegrityError as exc:
        _log_db_error("/postonsolve", m, exc)
        return await m.reply(
            "Updating the announcement flag failed because the database found conflicting chat rows. Check the server logs."
        )
    except Exception as exc:
        _log_db_error("/postonsolve", m, exc)
        return await m.reply("Updating the announcement flag failed due to a database error. Please try again.")
    await m.reply(f"Post-on-solve set to {arg[0].lower()}.")
