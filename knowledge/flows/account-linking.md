# Account Linking

## Trigger And Entry Point
- Telegram: `/link`, `/relink`, `/unlink` in `src/commands.py`
- Discord: `/link`, `/relink`, `/unlink` nested inside `src/discord_commands.py::register_discord_commands()`

## Step-By-Step Path
1. Platform command handler extracts the platform account id, cached display name, and requested LeetCode username.
2. Handler calls the matching DB function:
   - Telegram: `link_telegram_account()`, `relink_telegram_account()`, `unlink_telegram_account()`
   - Discord: `link_discord_account()`, `relink_discord_account()`, `unlink_discord_account()`
3. The DB layer resolves or creates a shared `users` row keyed by `lc_username`.
4. For a fresh link, the platform link row is inserted and `last_seen` is initialized to the current time.
5. For a switch to a new LeetCode username, the existing shared `user_id` is reused and its `users.lc_username` plus `last_seen` cursor are updated.
6. For a switch to an already-existing LeetCode user, the platform link is repointed to that shared user and platform memberships are copied across with `INSERT OR IGNORE`.
7. On unlink, platform-specific memberships are deleted first, then the platform link row is removed, and the shared user is deleted only if no platform links remain.

## Key Files And Symbols
- `src/commands.py`
- `src/discord_commands.py::register_discord_commands`
- `src/db.py::link_telegram_account`
- `src/db.py::relink_telegram_account`
- `src/db.py::unlink_telegram_account`
- `src/db.py::link_discord_account`
- `src/db.py::relink_discord_account`
- `src/db.py::unlink_discord_account`

## Side Effects
- Inserts, updates, or deletes from `users`, `telegram_links`, `discord_links`, `memberships`, `discord_channel_memberships`, and `last_seen`
- Can preserve existing leaderboard participation when moving a platform account onto another shared user

## Failure Points And Gotchas
- A LeetCode username cannot be linked to two Telegram users or two Discord users at the same time.
- Telegram and Discord can both point at the same shared user, so unlink logic must not assume single-platform ownership.
- Switching to a new LeetCode username intentionally keeps the same shared `user_id`, which means historical memberships and completions stay attached.
- Switching a platform account onto an already-existing shared user moves memberships, but the old shared user cleanup path is not explicit in `link_telegram_account()` or `link_discord_account()`. I did not find follow-up cleanup for that merge path.
