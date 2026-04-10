from __future__ import annotations

import asyncio

import discord

from . import db
from .config import DISCORD_APP_ID, DISCORD_BOT_TOKEN, DISCORD_DEV_GUILD_ID, discord_enabled
from .discord_render import champion_message, leaderboard_message, solve_announcement


class TeLeetDiscordClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(intents=intents, application_id=int(DISCORD_APP_ID))
        self.tree = discord.app_commands.CommandTree(self)

    async def setup_hook(self):
        from .discord_commands import register_discord_commands

        register_discord_commands(self.tree)
        if DISCORD_DEV_GUILD_ID:
            guild = discord.Object(id=DISCORD_DEV_GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            print(f"[Discord] synced {len(synced)} guild commands to {DISCORD_DEV_GUILD_ID}")
        else:
            synced = await self.tree.sync()
            print(f"[Discord] synced {len(synced)} global commands")

    async def on_ready(self):
        print(f"[Discord] connected as {self.user}")


discord_client = TeLeetDiscordClient() if discord_enabled() else None


def enabled() -> bool:
    return discord_client is not None


async def start_discord():
    if discord_client is None:
        return
    await discord_client.start(DISCORD_BOT_TOKEN)


async def wait_for_discord_ready(discord_task: asyncio.Task | None):
    if discord_client is None or discord_task is None:
        return

    ready_waiter = asyncio.create_task(discord_client.wait_until_ready())
    done, pending = await asyncio.wait(
        {ready_waiter, discord_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    if ready_waiter in done:
        await ready_waiter
        return

    await discord_task
    raise RuntimeError("Discord client exited before becoming ready.")


async def _resolve_channel(channel_id: str):
    if discord_client is None:
        return None
    cid = int(channel_id)
    channel = discord_client.get_channel(cid)
    if channel is None:
        try:
            channel = await discord_client.fetch_channel(cid)
        except Exception as exc:
            print(f"[Discord] fetch_channel failed channel_id={channel_id} exc={exc}")
            return None
    return channel


async def resolve_discord_mention(user_id: int) -> str:
    link = db.get_discord_link_for_user(user_id)
    if link:
        return f"<@{link['discord_user_id']}>"
    identity = db.get_any_platform_identity(user_id)
    return discord.utils.escape_markdown(identity["lc_username"] if identity else str(user_id))


async def build_discord_rank_lines(scored) -> list[str]:
    lines = []
    rank = 1
    for entry in scored[:10]:
        mention = await resolve_discord_mention(entry["user_id"])
        counts = entry["counts"]
        lines.append(
            f"{rank}. {mention} - **{entry['total']}** "
            f"(E:{counts['Easy']} M:{counts['Medium']} H:{counts['Hard']})"
        )
        rank += 1
    return lines


async def send_discord_solve_announcement(
    guild_id: str,
    channel_id: str,
    user_id: int,
    title: str,
    difficulty: str,
    total: int,
    counts: dict[str, int],
):
    if discord_client is None:
        return
    channel = await _resolve_channel(channel_id)
    if channel is None:
        return
    mention = await resolve_discord_mention(user_id)
    message = solve_announcement(mention, title, difficulty, total, counts)
    try:
        await channel.send(
            message,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
    except Exception as exc:
        print(
            f"[Discord] solve announcement failed guild_id={guild_id} "
            f"channel_id={channel_id} exc={exc}"
        )


async def post_discord_leaderboard(guild_id: str, channel_id: str, scoring: str, scored, header: str):
    if discord_client is None or not scored:
        return
    channel = await _resolve_channel(channel_id)
    if channel is None:
        return
    ranked_lines = await build_discord_rank_lines(scored)
    message = leaderboard_message(header, scoring, ranked_lines)
    try:
        await channel.send(
            message,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
    except Exception as exc:
        print(
            f"[Discord] leaderboard send failed guild_id={guild_id} "
            f"channel_id={channel_id} exc={exc}"
        )


async def post_discord_champion(guild_id: str, channel_id: str, scored):
    if discord_client is None or not scored:
        return
    channel = await _resolve_channel(channel_id)
    if channel is None:
        return
    ranked_lines = await build_discord_rank_lines(scored)
    top_total = scored[0]["total"]
    winners = [entry for entry in scored if entry["total"] == top_total]
    winner_mentions = [await resolve_discord_mention(entry["user_id"]) for entry in winners]
    message = champion_message(winner_mentions, top_total, ranked_lines)
    try:
        await channel.send(
            message,
            allowed_mentions=discord.AllowedMentions(users=True),
        )
    except Exception as exc:
        print(
            f"[Discord] champion send failed guild_id={guild_id} "
            f"channel_id={channel_id} exc={exc}"
        )
