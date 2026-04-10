from datetime import datetime, timezone
from typing import Literal

import discord
from discord import app_commands

from . import db
from .help_text import discord_help_message
from .leaderboard import rank_rows
from .timeutil import week_window_cst


async def _send_response(interaction: discord.Interaction, content: str, ephemeral: bool = False):
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral)


def _guild_channel_ids(interaction: discord.Interaction) -> tuple[str, str]:
    return str(interaction.guild_id), str(interaction.channel_id)


def _discord_username(interaction: discord.Interaction) -> str:
    return str(interaction.user)


def register_discord_commands(tree: app_commands.CommandTree):
    @tree.command(name="help", description="Show a getting-started command overview")
    @app_commands.guild_only()
    async def help_command(interaction: discord.Interaction):
        await _send_response(
            interaction,
            discord_help_message(),
            ephemeral=True,
        )

    @tree.command(name="link", description="Link your LeetCode account")
    @app_commands.guild_only()
    async def link(interaction: discord.Interaction, leetcode_username: str):
        ok, msg = db.link_discord_account(
            str(interaction.user.id),
            _discord_username(interaction),
            leetcode_username.strip(),
        )
        await _send_response(interaction, msg, ephemeral=True)

    @tree.command(name="relink", description="Relink your Discord account to a LeetCode user")
    @app_commands.guild_only()
    async def relink(interaction: discord.Interaction, leetcode_username: str):
        ok, msg = db.relink_discord_account(
            str(interaction.user.id),
            _discord_username(interaction),
            leetcode_username.strip(),
        )
        await _send_response(interaction, msg, ephemeral=True)

    @tree.command(name="unlink", description="Unlink your Discord account from LeetCode")
    @app_commands.guild_only()
    async def unlink(interaction: discord.Interaction):
        ok, msg = db.unlink_discord_account(str(interaction.user.id))
        await _send_response(interaction, msg, ephemeral=True)

    @tree.command(name="join", description="Join this channel's leaderboard")
    @app_commands.guild_only()
    async def join(interaction: discord.Interaction):
        guild_id, channel_id = _guild_channel_ids(interaction)
        db.set_discord_channel(guild_id, channel_id)
        if not db.join_discord_channel(guild_id, channel_id, str(interaction.user.id)):
            return await _send_response(
                interaction,
                "Link your LeetCode first with /link.",
                ephemeral=True,
            )
        await _send_response(
            interaction,
            "You're in. I'll count your first ACs for this channel's weekly board.",
            ephemeral=True,
        )

    @tree.command(name="leave", description="Leave this channel's leaderboard")
    @app_commands.guild_only()
    async def leave(interaction: discord.Interaction):
        guild_id, channel_id = _guild_channel_ids(interaction)
        if not db.leave_discord_channel(guild_id, channel_id, str(interaction.user.id)):
            return await _send_response(
                interaction,
                "Link your LeetCode first with /link.",
                ephemeral=True,
            )
        await _send_response(interaction, "Left this channel's leaderboard.", ephemeral=True)

    @tree.command(name="leaderboard", description="Show this channel's weekly leaderboard")
    @app_commands.guild_only()
    async def leaderboard(interaction: discord.Interaction):
        guild_id, channel_id = _guild_channel_ids(interaction)
        db.set_discord_channel(guild_id, channel_id)
        scoring = db.get_discord_channel_scoring(guild_id, channel_id) or "1,2,5"
        start, end = week_window_cst(datetime.now(timezone.utc))
        rows = db.weekly_counts_discord(guild_id, channel_id, start, end)
        scored, weights = rank_rows(rows, scoring)
        if not scored:
            return await _send_response(interaction, "No solves yet this week.")

        from .discord_bot import build_discord_rank_lines

        e, m, h = weights
        lines = [f"**This week's leaderboard**", f"Point allocation: (E={e}, M={m}, H={h})", ""]
        lines.extend(await build_discord_rank_lines(scored))
        await _send_response(
            interaction,
            "\n".join(lines),
            ephemeral=False,
        )

    @tree.command(name="stats", description="Show your current and lifetime solve counts")
    @app_commands.guild_only()
    async def stats(interaction: discord.Interaction):
        user = db.get_user_by_discord_id(str(interaction.user.id))
        if not user:
            return await _send_response(
                interaction,
                "Link first with /link.",
                ephemeral=True,
            )

        start, end = week_window_cst(datetime.now(timezone.utc))
        total = db.get_user_counts(user["user_id"])
        week = db.get_user_counts(user["user_id"], start, end)
        await _send_response(
            interaction,
            (
                f"Lifetime - E:{total.get('Easy', 0)} M:{total.get('Medium', 0)} H:{total.get('Hard', 0)}\n"
                f"This week - E:{week.get('Easy', 0)} M:{week.get('Medium', 0)} H:{week.get('Hard', 0)}"
            ),
            ephemeral=True,
        )

    @tree.command(name="toggle_announcements", description="Toggle solve announcements in this channel")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    async def toggle_announcements(interaction: discord.Interaction, state: Literal["on", "off"]):
        member = interaction.user
        perms = getattr(member, "guild_permissions", None)
        if not perms or not (perms.manage_channels or perms.administrator):
            return await _send_response(
                interaction,
                "You need Manage Channels or Administrator to use this command.",
                ephemeral=True,
            )

        guild_id, channel_id = _guild_channel_ids(interaction)
        db.set_discord_channel(
            guild_id,
            channel_id,
            post_on_solve=1 if state == "on" else 0,
        )
        await _send_response(
            interaction,
            f"Announcements set to {state} for this channel.",
            ephemeral=True,
        )
