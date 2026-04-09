import time

from aiogram import Router, types
from aiogram.filters import Command

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

    ok, msg = db.link_telegram_account(
        m.from_user.id,
        m.from_user.username or "",
        parts[1].strip(),
    )
    await m.reply(msg)


@router.message(Command("unlink"))
async def unlink(m: types.Message):
    ok, msg = db.unlink_telegram_account(m.from_user.id)
    await m.reply(msg)


@router.message(Command("relink"))
async def relink(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) != 2:
        return await m.reply("Usage: /relink leetcode_username")

    ok, msg = db.relink_telegram_account(
        m.from_user.id,
        m.from_user.username or "",
        parts[1].strip(),
    )
    await m.reply(msg)


@router.message(Command("join"))
async def join(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /join inside a group.")

    db.set_chat(m.chat.id, m.chat.title or "")
    if not db.join_chat(m.chat.id, m.from_user.id):
        return await m.reply("Link your LeetCode first with /link leetcode_username.")
    await m.reply("You're in! I'll count your first ACs for this chat's weekly board.")


@router.message(Command("leave"))
async def leave(m: types.Message):
    if m.chat.type == "private":
        return await m.reply("Use /leave in the group you want to leave.")

    if not db.leave_chat(m.chat.id, m.from_user.id):
        return await m.reply("Link your LeetCode first with /link leetcode_username.")
    await m.reply("Left this chat's leaderboard.")


@router.message(Command("postonsolve"))
async def postflag(m: types.Message):
    if m.chat.type == "private":
        return

    arg = (m.text or "").split()[1:] or []
    if not arg or arg[0].lower() not in ("on", "off"):
        return await m.reply("Usage: /postonsolve on|off")

    db.set_chat(
        m.chat.id,
        m.chat.title or "",
        post_on_solve=1 if arg[0].lower() == "on" else 0,
    )
    await m.reply(f"Post-on-solve set to {arg[0].lower()}.")
