from aiogram import Router, types, F
from aiogram.filters import Command
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
    lc = parts[1]
    tg_id = m.from_user.id
    db.upsert_user(tg_id, m.from_user.username or "", lc)
    await m.reply(f"Linked to LeetCode: {lc}. I’ll track first-time ACs and post to groups you join.")

@router.message(Command("unlink"))
async def unlink(m: types.Message):
    # simplest: set lc_username to NULL not allowed; you can delete row
    await m.reply("Not implemented yet (MVP keeps it simple).")

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
