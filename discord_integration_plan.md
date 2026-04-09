# Discord Bot Integration Plan (Single Container)

## Goal

Add Discord support on top of the existing Telegram LeetCode bot while:

- reusing the same SQLite database
- keeping Telegram working throughout the migration
- running Telegram and Discord in the same process and container
- sharing the same LeetCode poller, scheduler, scoring rules, and week window
- keeping the first Discord release intentionally small

---

## Scope for v1

### Discord slash commands

Implement these as Discord slash commands:

- `/link <leetcode_username>`
- `/relink <leetcode_username>`
- `/unlink`
- `/join`
- `/leave`
- `/leaderboard`
- `/stats`
- `/toggle_announcements <on|off>`

### v1 behavior

- Discord is guild-channel-only in v1. No Discord DM support.
- One LeetCode account can be linked to both one Telegram account and one Discord account at the same time.
- Linking is identity-only.
- Channel participation is explicit through `/join` and `/leave`.
- Announcements should ping the Discord user with `<@discord_user_id>` when possible.
- Scoring and ranking must match Telegram.
- The same shared poller powers both platforms.
- The same shared scheduler posts to both platforms.

### Not in v1

- deep generic multi-platform framework extraction
- Discord parity for all Telegram debug commands
- moving off SQLite
- separate Discord container
- advanced admin tooling beyond announcement toggling

---

## High-Level Architecture

Run both bots in the same asyncio application:

- Telegram bot: existing `aiogram` bot
- Discord bot: new `discord.py` bot
- Scheduler: shared APScheduler instance
- Poller: one shared LeetCode poll loop
- Database: one shared SQLite file

### Why one process

- one deployment target
- one event loop
- no cross-container coordination
- no SQLite multi-container locking issues
- easier logging and debugging during the first rollout

### Suggested module layout

```text
src/
  bot.py
  commands.py
  scheduler.py
  db.py
  scoring.py
  timeutil.py
  leetcode.py

  discord_bot.py
  discord_commands.py
  discord_render.py
```

If shared ranking and notification assembly grows, move that logic into a separate shared module later.

---

## Shared Identity Model

The current project is Telegram-primary. Discord support should not be built by adding Discord columns onto the current Telegram-owned user row.

Use a shared app user plus platform link tables.

### Core idea

- `users` represents the shared app user
- `users.lc_username` is unique
- Telegram accounts resolve to a shared user through `telegram_links`
- Discord accounts resolve to a shared user through `discord_links`
- solve history and leaderboard aggregation attach to the shared user, not to a platform-specific account ID

### Why this model

- it allows one LeetCode account to be used from both Telegram and Discord
- it avoids making Telegram IDs the primary identity forever
- it keeps platform lookups simple
- it removes the need to migrate solve history between platforms later

### How caller lookup works

The bot never trusts a raw user ID argument from commands.

Instead:

- Telegram command: resolve `telegram_user_id -> telegram_links.user_id -> users`
- Discord command: resolve `discord_user_id -> discord_links.user_id -> users`

That means the shared identity is stable while the platform link remains easy to look up.

---

## Database Plan

### 1) Shared users table

Use `users` as the platform-agnostic identity table.

Suggested shape:

- `id INTEGER PRIMARY KEY`
- `lc_username TEXT UNIQUE NOT NULL`
- `created_at INTEGER NOT NULL`

### 2) Telegram link table

Move Telegram identity mapping into a dedicated table.

Suggested shape:

- `telegram_links`
- `telegram_user_id INTEGER PRIMARY KEY`
- `user_id INTEGER UNIQUE NOT NULL`
- `tg_username TEXT`

Purpose:

- resolve Telegram callers to shared users
- keep Telegram usernames available for rendering and fallback

### 3) Discord link table

Add a dedicated Discord identity mapping table.

Suggested shape:

- `discord_links`
- `discord_user_id TEXT PRIMARY KEY`
- `user_id INTEGER UNIQUE NOT NULL`
- `discord_username TEXT`

Purpose:

- resolve Discord callers to shared users
- support direct mention rendering

### 4) Telegram chat membership migration

Existing Telegram chat membership should stop pointing at Telegram user IDs and instead point at shared user IDs.

Suggested update:

- `memberships`
- `chat_id INTEGER NOT NULL`
- `user_id INTEGER NOT NULL`
- primary key: `(chat_id, user_id)`

### 5) Discord channel config table

Add a channel-level configuration table for Discord.

Suggested shape:

- `discord_channels`
- `guild_id TEXT NOT NULL`
- `channel_id TEXT NOT NULL`
- `post_on_solve INTEGER NOT NULL DEFAULT 1`
- `scoring TEXT NOT NULL DEFAULT '1,2,5'`
- primary key: `(guild_id, channel_id)`

### 6) Discord channel membership table

Track which shared users are opted into which Discord channels.

Suggested shape:

- `discord_channel_memberships`
- `guild_id TEXT NOT NULL`
- `channel_id TEXT NOT NULL`
- `user_id INTEGER NOT NULL`
- primary key: `(guild_id, channel_id, user_id)`

### 7) Completions migration

`completions` should stop referencing `telegram_user_id` and instead reference shared `user_id`.

Suggested direction:

- replace `telegram_user_id` with `user_id`
- keep `slug`, `solved_at_utc`, and `is_deleted`
- keep the active dedupe rule on the shared user and problem slug

This makes solve tracking platform-agnostic and prevents duplicate solve records when the same person uses both Telegram and Discord.

### 8) Last seen

Keep `last_seen` keyed by `lc_username`.

Reason:

- the poller is keyed by LeetCode username, not by platform identity

---

## Shared Logic Changes

### Poll loop

Keep one shared LeetCode poller.

For each new accepted submission:

1. fetch recent accepted submissions for the shared user’s LeetCode username
2. detect new solves using the shared `last_seen`
3. insert one completion for the shared user
4. fan out notifications to:
   - Telegram chats where that shared user is a member
   - Discord channels where that shared user is a member

### Scoring logic

Keep one scoring implementation shared across both platforms:

- same week window calculation
- same difficulty weights
- same ranking rules
- same tie-breakers

### Shared data assembly

Prefer this split:

- shared code assembles ranked rows, totals, winners, and counts
- Telegram rendering produces HTML
- Discord rendering produces Discord-safe text and mentions

This keeps score logic consistent and reduces duplicated ranking code.

---

## Discord Bot Design

### Library

Use `discord.py` with slash commands via `app_commands`.

Reason:

- modern UX
- no message-content parsing needed
- enough for the v1 command set

### Intents

Minimum expected intents:

- `guilds`

No privileged intents are needed for v1.

### Mentions

Use `<@discord_user_id>` for notifications and leaderboard rendering when a Discord link exists.

No Telegram-style member lookup fallback system is needed for the primary path because Discord mentions by user ID are straightforward.

---

## Discord Command Plan

## `/link <leetcode_username>`

Purpose:

- link the caller’s Discord account to a shared app user

Behavior:

- use the caller’s Discord account ID from the interaction
- if the LeetCode username does not exist, create a shared user and attach the caller’s Discord link
- if the LeetCode username exists and has no Discord link yet, attach the caller’s Discord link to that shared user
- if the caller is already linked to a different shared user, reject unless they `/unlink` first
- do not auto-enroll the caller in the current channel
- set `last_seen` to now for first-time links to avoid backfill spam

Important rule:

- never accept a raw Discord user ID from user input

## `/relink <leetcode_username>`

Purpose:

- repair a broken or outdated Discord identity mapping for the caller

Behavior:

- reassign the Discord link for the target LeetCode user to the caller’s current Discord account
- preserve the shared user, solve history, and Discord channel memberships
- refresh stored `discord_username`
- reject if the caller’s Discord account is already linked to another LeetCode user

## `/unlink`

Purpose:

- remove only the caller’s Discord link

Behavior:

- delete the caller’s row from `discord_links`
- delete the caller’s rows from `discord_channel_memberships`
- keep Telegram links untouched
- keep the shared user if a Telegram link still exists
- if no platform links remain for that shared user, delete the shared user’s memberships, completions, and `last_seen` to match current unlink semantics

## `/join`

Purpose:

- opt the caller into the current Discord channel’s leaderboard and announcements

Behavior:

- guild-only
- ensure the caller already has a Discord link
- ensure the current channel exists in `discord_channels`
- create a `discord_channel_memberships` row for the current channel and shared user

## `/leave`

Purpose:

- opt the caller out of the current Discord channel

Behavior:

- guild-only
- remove the caller’s membership row for the current channel

## `/leaderboard`

Purpose:

- show the current week’s leaderboard for the current Discord channel

Behavior:

- guild-only
- load the channel scoring config
- aggregate weekly solve counts for shared users in that channel
- render top users with Discord mentions when linked

## `/stats`

Purpose:

- show the caller’s lifetime and weekly solve totals

Behavior:

- caller-only in v1
- resolve the caller through `discord_links`
- return the same Easy/Medium/Hard breakdown used on Telegram

## `/toggle_announcements <on|off>`

Purpose:

- enable or disable solve announcements in the current Discord channel

Behavior:

- guild-only
- update `discord_channels.post_on_solve`
- do not modify channel membership rows

Permissions:

- require `Manage Channels` or `Administrator`

---

## Notification Behavior

### Per-solve notifications

When a shared user gets a new solve:

1. determine every Telegram chat membership for that user
2. determine every Discord channel membership for that user
3. filter out channels where `post_on_solve = 0`
4. send platform-specific messages

Suggested Discord format:

```text
<@DISCORD_USER_ID> solved **Two Sum** (*Easy*)
Weekly score: **7** - E:3 M:2 H:0
```

### Scheduled posts

Keep one shared APScheduler instance.

The current scheduler behavior remains:

- daily leaderboard snapshot at 8:00 PM America/Chicago
- weekly champion post on Sunday at 11:59 PM America/Chicago

Both jobs should fan out to:

- Telegram chats
- Discord channels

Suggested Discord champion format:

```text
**Weekly Champion** - <@USER_ID>
Final score: **X**

1. <@USER_ID> - **X** (E:a M:b H:c)
2. <@USER_ID> - **Y** (E:a M:b H:c)
```

---

## Startup Plan

### Current startup

The app currently:

- initializes the DB
- starts the scheduler and shared poller
- starts Telegram polling

### New startup flow

`main()` should:

1. initialize the DB
2. start the shared scheduler and poller
3. start Telegram polling task
4. start Discord client task
5. await both forever

Important detail:

- both bots run on the same asyncio loop
- the poller remains shared
- the scheduler remains shared

---

## SQLite Notes

This design still fits SQLite well because everything runs in one process.

Recommended pragmas and behavior:

- `PRAGMA journal_mode=WAL;`
- `PRAGMA busy_timeout=5000;`
- keep transactions short
- log send failures without aborting poller progress

---

## Environment And Dependency Changes

Add these environment variables:

- `DISCORD_BOT_TOKEN`
- `DISCORD_APP_ID`
- `DISCORD_DEV_GUILD_ID` optional for development-only fast slash command sync

Dependency changes:

- add `discord.py`

---

## Manual Setup Required

These steps cannot be completed automatically by the repo and must be done manually.

### Discord Developer Portal

1. create a Discord application
2. create a bot user for that application
3. copy the bot token and store it as `DISCORD_BOT_TOKEN`
4. copy the application ID and store it as `DISCORD_APP_ID`
5. optionally choose a development test server and store its ID as `DISCORD_DEV_GUILD_ID`

### Installation and invite setup

1. open the app Installation page in the Discord Developer Portal
2. configure Guild Install
3. include the `bot` and `applications.commands` scopes
4. generate or use the install link
5. invite the bot to a test server before wider rollout

### Bot permissions for v1

Grant the bot at least:

- `View Channels`
- `Send Messages`

If embeds are used later, also grant `Embed Links`.

### Important notes

- no Interaction Endpoint URL is needed for this design because `discord.py` will use the Gateway, not outgoing webhooks
- no privileged intents are needed for v1
- deployment secrets must be updated anywhere the Telegram token is currently configured, including local `.env`, Docker runtime env, and the deployed host

---

## Implementation Order

### Phase 1

1. add `discord.py`
2. add Discord env vars
3. scaffold the Discord bot and a minimal slash command for command sync validation

### Phase 2

1. migrate to shared users plus platform link tables
2. migrate Telegram memberships and completions to shared `user_id`
3. add Discord channel config and membership tables

### Phase 3

1. implement Discord `/link`
2. implement Discord `/relink`
3. implement Discord `/unlink`
4. implement Discord `/join`
5. implement Discord `/leave`

### Phase 4

1. implement Discord `/leaderboard`
2. implement Discord `/stats`
3. implement Discord `/toggle_announcements`

### Phase 5

1. fan out poll-loop notifications to Discord
2. fan out scheduled leaderboard posts to Discord
3. fan out weekly champion posts to Discord

### Phase 6

1. reduce duplicated ranking/rendering code
2. improve logs and failure visibility
3. update README and deployment docs

---

## Risks To Watch

### Identity conflicts

Make sure platform links stay one-to-one:

- one Telegram account links to at most one shared user
- one Discord account links to at most one shared user
- one shared user has at most one Telegram link and one Discord link

### Migration correctness

Existing Telegram users, memberships, completions, and `last_seen` rows must backfill cleanly into the new shared-user model.

### Channel expectations

Because Discord v1 uses explicit `/join` and `/leave`, users may link successfully but still not appear in a channel until they join it. The command responses must make that clear.

### Permissions

Discord send failures will happen if the bot lacks channel access. These should be logged clearly and should not crash the poller or scheduler jobs.

---

## v1 Success Criteria

The Discord integration is successful when:

- Telegram and Discord both run in the same process
- existing Telegram behavior still works after the identity migration
- one LeetCode account can be used from both Telegram and Discord
- Discord `/link`, `/relink`, `/unlink`, `/join`, and `/leave` work correctly
- Discord `/leaderboard` and `/stats` use the same scoring logic as Telegram
- solve announcements post to the correct Discord channels
- scheduled leaderboard and champion posts also post to Discord
