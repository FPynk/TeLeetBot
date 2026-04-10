import discord

from .scoring import parse_weights


def solve_announcement(user_mention: str, title: str, difficulty: str, total: int, counts: dict[str, int]) -> str:
    safe_title = discord.utils.escape_markdown(title)
    safe_difficulty = discord.utils.escape_markdown(difficulty)
    return (
        f"{user_mention} solved **{safe_title}** (*{safe_difficulty}*).\n"
        f"Weekly score: **{total}** - "
        f"E:{counts.get('Easy', 0)} M:{counts.get('Medium', 0)} H:{counts.get('Hard', 0)}"
    )


def leaderboard_message(header: str, scoring: str, ranked_lines: list[str]) -> str:
    e, m, h = parse_weights(scoring)
    lines = [f"**{header}**", f"Point allocation: (E={e}, M={m}, H={h})", ""]
    lines.extend(ranked_lines)
    return "\n".join(lines)


def champion_message(winner_mentions: list[str], top_total: int, ranked_lines: list[str]) -> str:
    lines = [f"**Weekly Champion** - {' & '.join(winner_mentions)} (score **{top_total}**)", ""]
    lines.append("*Final standings*")
    lines.extend(ranked_lines)
    return "\n".join(lines)
