import sqlite3
import time
from contextlib import contextmanager
from typing import Optional


@contextmanager
def conn(db_path: str = "bot.db"):
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA foreign_keys=ON;")
    c.execute("PRAGMA busy_timeout=5000;")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init(db_path: str = "bot.db"):
    with conn(db_path) as c:
        if _needs_legacy_migration(c):
            _migrate_telegram_primary_schema(c)
        _create_current_schema(c)
        _ensure_indexes(c)


def _table_exists(c: sqlite3.Connection, table: str) -> bool:
    row = c.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def _table_columns(c: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(c, table):
        return set()
    return {row["name"] for row in c.execute(f"PRAGMA table_info({table})").fetchall()}


def _needs_legacy_migration(c: sqlite3.Connection) -> bool:
    cols = _table_columns(c, "users")
    if not cols:
        return False
    return "telegram_user_id" in cols


def _create_current_schema(c: sqlite3.Connection):
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
          id         INTEGER PRIMARY KEY,
          lc_username TEXT UNIQUE NOT NULL,
          created_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS telegram_links (
          telegram_user_id INTEGER PRIMARY KEY,
          user_id          INTEGER UNIQUE NOT NULL,
          tg_username      TEXT,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS discord_links (
          discord_user_id   TEXT PRIMARY KEY,
          user_id           INTEGER UNIQUE NOT NULL,
          discord_username  TEXT,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chats (
          chat_id       INTEGER PRIMARY KEY,
          title         TEXT,
          tz            TEXT NOT NULL DEFAULT 'America/Chicago',
          post_on_solve INTEGER NOT NULL DEFAULT 1,
          scoring       TEXT NOT NULL DEFAULT '1,2,5'
        );

        CREATE TABLE IF NOT EXISTS memberships (
          chat_id  INTEGER NOT NULL,
          user_id  INTEGER NOT NULL,
          PRIMARY KEY (chat_id, user_id),
          FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS discord_channels (
          guild_id       TEXT NOT NULL,
          channel_id     TEXT NOT NULL,
          post_on_solve  INTEGER NOT NULL DEFAULT 1,
          scoring        TEXT NOT NULL DEFAULT '1,2,5',
          PRIMARY KEY (guild_id, channel_id)
        );

        CREATE TABLE IF NOT EXISTS discord_channel_memberships (
          guild_id   TEXT NOT NULL,
          channel_id TEXT NOT NULL,
          user_id    INTEGER NOT NULL,
          PRIMARY KEY (guild_id, channel_id, user_id),
          FOREIGN KEY (guild_id, channel_id) REFERENCES discord_channels(guild_id, channel_id) ON DELETE CASCADE,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS problems (
          slug        TEXT PRIMARY KEY,
          title       TEXT NOT NULL,
          difficulty  TEXT NOT NULL CHECK (difficulty IN ('Easy','Medium','Hard'))
        );

        CREATE TABLE IF NOT EXISTS completions (
          id            INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id       INTEGER NOT NULL,
          slug          TEXT NOT NULL,
          solved_at_utc INTEGER NOT NULL,
          is_deleted    INTEGER NOT NULL DEFAULT 0,
          FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
          FOREIGN KEY (slug) REFERENCES problems(slug) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS last_seen (
          lc_username   TEXT PRIMARY KEY,
          last_seen_ts  INTEGER NOT NULL
        );
        """
    )


def _migrate_telegram_primary_schema(c: sqlite3.Connection):
    completion_cols = _table_columns(c, "completions")
    has_is_deleted = "is_deleted" in completion_cols

    c.execute("PRAGMA foreign_keys=OFF;")
    try:
        c.execute("BEGIN IMMEDIATE;")
        c.executescript(
            """
            CREATE TABLE users_new (
              id          INTEGER PRIMARY KEY,
              lc_username TEXT UNIQUE NOT NULL,
              created_at  INTEGER NOT NULL
            );

            CREATE TABLE telegram_links_new (
              telegram_user_id INTEGER PRIMARY KEY,
              user_id          INTEGER UNIQUE NOT NULL,
              tg_username      TEXT,
              FOREIGN KEY (user_id) REFERENCES users_new(id) ON DELETE CASCADE
            );

            CREATE TABLE memberships_new (
              chat_id  INTEGER NOT NULL,
              user_id  INTEGER NOT NULL,
              PRIMARY KEY (chat_id, user_id),
              FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
              FOREIGN KEY (user_id) REFERENCES users_new(id) ON DELETE CASCADE
            );

            CREATE TABLE completions_new (
              id            INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id       INTEGER NOT NULL,
              slug          TEXT NOT NULL,
              solved_at_utc INTEGER NOT NULL,
              is_deleted    INTEGER NOT NULL DEFAULT 0,
              FOREIGN KEY (user_id) REFERENCES users_new(id) ON DELETE CASCADE,
              FOREIGN KEY (slug) REFERENCES problems(slug) ON DELETE CASCADE
            );
            """
        )

        c.execute(
            """
            INSERT INTO users_new(id, lc_username, created_at)
            SELECT telegram_user_id, lc_username, created_at FROM users
            """
        )
        c.execute(
            """
            INSERT INTO telegram_links_new(telegram_user_id, user_id, tg_username)
            SELECT telegram_user_id, telegram_user_id, tg_username FROM users
            """
        )
        c.execute(
            """
            INSERT INTO memberships_new(chat_id, user_id)
            SELECT chat_id, telegram_user_id FROM memberships
            """
        )

        if has_is_deleted:
            c.execute(
                """
                INSERT INTO completions_new(id, user_id, slug, solved_at_utc, is_deleted)
                SELECT id, telegram_user_id, slug, solved_at_utc, is_deleted FROM completions
                """
            )
        else:
            c.execute(
                """
                INSERT INTO completions_new(id, user_id, slug, solved_at_utc, is_deleted)
                SELECT id, telegram_user_id, slug, solved_at_utc, 0 FROM completions
                """
            )

        c.execute("DROP TABLE memberships")
        c.execute("DROP TABLE completions")
        c.execute("DROP TABLE users")
        c.execute("ALTER TABLE users_new RENAME TO users")
        c.execute("ALTER TABLE telegram_links_new RENAME TO telegram_links")
        c.execute("ALTER TABLE memberships_new RENAME TO memberships")
        c.execute("ALTER TABLE completions_new RENAME TO completions")
        c.execute("COMMIT;")
    except Exception:
        c.execute("ROLLBACK;")
        raise
    finally:
        c.execute("PRAGMA foreign_keys=ON;")


def _ensure_indexes(c: sqlite3.Connection):
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id)"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_discord_channel_memberships_user ON discord_channel_memberships(user_id)"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_completions_user_time ON completions(user_id, solved_at_utc)"
    )
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_compl_user_slug_active ON completions(user_id, slug) WHERE is_deleted=0"
    )
    c.execute(
        "CREATE INDEX IF NOT EXISTS idx_compl_user_slug_deleted ON completions(user_id, slug, is_deleted)"
    )


def get_or_create_user(lc_username: str) -> int:
    now = int(time.time())
    with conn() as c:
        row = c.execute(
            "SELECT id FROM users WHERE lc_username=?",
            (lc_username,),
        ).fetchone()
        if row:
            return row["id"]
        cur = c.execute(
            "INSERT INTO users(lc_username, created_at) VALUES(?, ?)",
            (lc_username, now),
        )
        return cur.lastrowid


def get_user_by_id(user_id: int):
    with conn() as c:
        return c.execute(
            "SELECT id, lc_username, created_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()


def get_user_by_lc(lc_username: str):
    with conn() as c:
        return c.execute(
            "SELECT id, lc_username, created_at FROM users WHERE lc_username=?",
            (lc_username,),
        ).fetchone()


def get_user_by_telegram_id(telegram_user_id: int):
    with conn() as c:
        return c.execute(
            """
            SELECT u.id AS user_id, u.lc_username, tl.telegram_user_id, tl.tg_username
            FROM telegram_links tl
            JOIN users u ON u.id = tl.user_id
            WHERE tl.telegram_user_id=?
            """,
            (telegram_user_id,),
        ).fetchone()


def get_user_by_discord_id(discord_user_id: str):
    with conn() as c:
        return c.execute(
            """
            SELECT u.id AS user_id, u.lc_username, dl.discord_user_id, dl.discord_username
            FROM discord_links dl
            JOIN users u ON u.id = dl.user_id
            WHERE dl.discord_user_id=?
            """,
            (discord_user_id,),
        ).fetchone()


def get_telegram_link_for_user(user_id: int):
    with conn() as c:
        return c.execute(
            """
            SELECT telegram_user_id, tg_username
            FROM telegram_links
            WHERE user_id=?
            """,
            (user_id,),
        ).fetchone()


def get_discord_link_for_user(user_id: int):
    with conn() as c:
        return c.execute(
            """
            SELECT discord_user_id, discord_username
            FROM discord_links
            WHERE user_id=?
            """,
            (user_id,),
        ).fetchone()


def get_tracked_users():
    with conn() as c:
        return c.execute(
            """
            -- Only poll LC users that still have at least one live platform link.
            SELECT DISTINCT u.id AS user_id, u.lc_username
            FROM users u
            LEFT JOIN telegram_links tl ON tl.user_id = u.id
            LEFT JOIN discord_links dl ON dl.user_id = u.id
            WHERE tl.telegram_user_id IS NOT NULL OR dl.discord_user_id IS NOT NULL
            ORDER BY u.id
            """
        ).fetchall()


def ensure_last_seen(lc_username: str, ts: int):
    with conn() as c:
        row = c.execute(
            "SELECT 1 FROM last_seen WHERE lc_username=?",
            (lc_username,),
        ).fetchone()
        if row is None:
            c.execute(
                "INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)",
                (lc_username, ts),
            )


def get_or_set_last_seen(lc_username: str, ts: Optional[int] = None):
    with conn() as c:
        if ts is None:
            row = c.execute(
                "SELECT last_seen_ts FROM last_seen WHERE lc_username=?",
                (lc_username,),
            ).fetchone()
            return row["last_seen_ts"] if row else 0

        row = c.execute(
            "SELECT 1 FROM last_seen WHERE lc_username=?",
            (lc_username,),
        ).fetchone()
        if row:
            c.execute(
                "UPDATE last_seen SET last_seen_ts=? WHERE lc_username=?",
                (ts, lc_username),
            )
        else:
            c.execute(
                "INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)",
                (lc_username, ts),
            )
        return ts


def link_telegram_account(telegram_user_id: int, tg_username: str, lc_username: str):
    now = int(time.time())
    with conn() as c:
        # Look up the Telegram caller's current shared user, if they already have one.
        current = c.execute(
            """
            SELECT u.id AS user_id, u.lc_username
            FROM telegram_links tl
            JOIN users u ON u.id = tl.user_id
            WHERE tl.telegram_user_id=?
            """,
            (telegram_user_id,),
        ).fetchone()

        # Look up the requested LC username and see whether another Telegram account already owns it.
        target = c.execute(
            """
            SELECT u.id AS user_id, u.lc_username, tl.telegram_user_id AS linked_tg_id
            FROM users u
            LEFT JOIN telegram_links tl ON tl.user_id = u.id
            WHERE u.lc_username=?
            """,
            (lc_username,),
        ).fetchone()

        if target and target["linked_tg_id"] and target["linked_tg_id"] != telegram_user_id:
            return False, (
                "That LeetCode username is already linked by another Telegram user. "
                "Ask them to relink it from the correct Telegram account or use a different LeetCode account."
            )

        if current and current["lc_username"] == lc_username:
            # Same logical link, just refresh the cached Telegram username.
            c.execute(
                "UPDATE telegram_links SET tg_username=? WHERE telegram_user_id=?",
                (tg_username, telegram_user_id),
            )
            return True, (
                f"Linked to LeetCode: {lc_username}. "
                "Please use /join now. I'll track first-time ACs and post to groups you join."
            )

        if target is None:
            if current:
                # This is the non-destructive "switch my LC username" path for an existing Telegram user.
                # Reuse the same shared user row so memberships and solve history stay attached.
                user_id = current["user_id"]
                old_lc_username = current["lc_username"]
                c.execute(
                    "UPDATE users SET lc_username=? WHERE id=?",
                    (lc_username, user_id),
                )
                # Move the poll cursor to the new LC username so the bot does not backfill the old account.
                c.execute(
                    "DELETE FROM last_seen WHERE lc_username=?",
                    (old_lc_username,),
                )
                c.execute(
                    """
                    INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)
                    ON CONFLICT(lc_username) DO UPDATE SET last_seen_ts=excluded.last_seen_ts
                    """,
                    (lc_username, now),
                )
            else:
                # Brand-new shared user: create the identity row and start tracking from "now".
                cur = c.execute(
                    "INSERT INTO users(lc_username, created_at) VALUES(?, ?)",
                    (lc_username, now),
                )
                user_id = cur.lastrowid
                c.execute(
                    """
                    INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)
                    ON CONFLICT(lc_username) DO UPDATE SET last_seen_ts=excluded.last_seen_ts
                    """,
                    (lc_username, now),
                )
        else:
            # The target LC user already exists, so attach this Telegram account to that shared user.
            user_id = target["user_id"]
            row = c.execute(
                "SELECT 1 FROM last_seen WHERE lc_username=?",
                (lc_username,),
            ).fetchone()
            if row is None:
                c.execute(
                    """
                    INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)
                    ON CONFLICT(lc_username) DO UPDATE SET last_seen_ts=excluded.last_seen_ts
                    """,
                    (lc_username, now),
                )

        if current is None:
            # First Telegram link for this caller.
            c.execute(
                """
                INSERT INTO telegram_links(telegram_user_id, user_id, tg_username)
                VALUES(?, ?, ?)
                """,
                (telegram_user_id, user_id, tg_username),
            )
        else:
            old_user_id = current["user_id"]
            if old_user_id != user_id:
                # Moving a Telegram account onto another shared user should also move its Telegram chat memberships.
                c.execute(
                    """
                    INSERT OR IGNORE INTO memberships(chat_id, user_id)
                    SELECT chat_id, ? FROM memberships WHERE user_id=?
                    """,
                    (user_id, old_user_id),
                )
                c.execute(
                    "DELETE FROM memberships WHERE user_id=?",
                    (old_user_id,),
                )
            # Point the Telegram account at the final shared user row and refresh the cached username.
            c.execute(
                """
                UPDATE telegram_links
                SET user_id=?, tg_username=?
                WHERE telegram_user_id=?
                """,
                (user_id, tg_username, telegram_user_id),
            )

        return True, (
            f"Linked to LeetCode: {lc_username}. "
            "Please use /join now. I'll track first-time ACs and post to groups you join."
        )


def relink_telegram_account(telegram_user_id: int, tg_username: str, lc_username: str):
    with conn() as c:
        target = c.execute(
            """
            SELECT u.id AS user_id, tl.telegram_user_id AS linked_tg_id
            FROM users u
            LEFT JOIN telegram_links tl ON tl.user_id = u.id
            WHERE u.lc_username=?
            """,
            (lc_username,),
        ).fetchone()
        if not target:
            return False, (
                "That LeetCode username isn't linked yet. Use /link leetcode_username first."
            )

        current = c.execute(
            """
            SELECT user_id
            FROM telegram_links
            WHERE telegram_user_id=?
            """,
            (telegram_user_id,),
        ).fetchone()
        if current and current["user_id"] != target["user_id"]:
            other = c.execute(
                "SELECT lc_username FROM users WHERE id=?",
                (current["user_id"],),
            ).fetchone()
            return False, (
                f"Your Telegram is already linked to LeetCode '{other['lc_username']}'. "
                f"Use /link {lc_username} if you want to switch this Telegram account."
            )

        linked_tg_id = target["linked_tg_id"]
        if linked_tg_id == telegram_user_id:
            c.execute(
                "UPDATE telegram_links SET tg_username=? WHERE telegram_user_id=?",
                (tg_username, telegram_user_id),
            )
            return True, f"You're already linked to {lc_username}. I refreshed your Telegram username."

        if linked_tg_id is not None:
            c.execute(
                "DELETE FROM telegram_links WHERE telegram_user_id=?",
                (linked_tg_id,),
            )

        c.execute(
            """
            INSERT INTO telegram_links(telegram_user_id, user_id, tg_username)
            VALUES(?, ?, ?)
            """,
            (telegram_user_id, target["user_id"], tg_username),
        )
        return True, (
            f"Relinked {lc_username} to your Telegram account. "
            "If you were in groups, you're still on their leaderboards."
        )


def unlink_telegram_account(telegram_user_id: int):
    with conn() as c:
        # Resolve the Telegram account to the shared user before removing the Telegram-specific rows.
        link = c.execute(
            """
            SELECT tl.user_id, u.lc_username
            FROM telegram_links tl
            JOIN users u ON u.id = tl.user_id
            WHERE tl.telegram_user_id=?
            """,
            (telegram_user_id,),
        ).fetchone()
        if not link:
            return False, "You don't have a linked LeetCode account."

        user_id = link["user_id"]
        lc_username = link["lc_username"]
        # Leaving Telegram should also drop Telegram chat participation for that shared user.
        c.execute("DELETE FROM memberships WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM telegram_links WHERE telegram_user_id=?", (telegram_user_id,))

        if not _user_has_any_links(c, user_id):
            # If Telegram was the last link, clean up the shared user exactly like the old single-platform bot did.
            c.execute("DELETE FROM last_seen WHERE lc_username=?", (lc_username,))
            c.execute("DELETE FROM users WHERE id=?", (user_id,))

        return True, "Unlinked. You can /link another LeetCode username anytime."


def link_discord_account(discord_user_id: str, discord_username: str, lc_username: str):
    now = int(time.time())
    with conn() as c:
        # Look up the Discord caller's current shared user, if they already have one.
        current = c.execute(
            """
            SELECT u.id AS user_id, u.lc_username
            FROM discord_links dl
            JOIN users u ON u.id = dl.user_id
            WHERE dl.discord_user_id=?
            """,
            (discord_user_id,),
        ).fetchone()

        # Look up the requested LC username and see whether another Discord account already owns it.
        target = c.execute(
            """
            SELECT u.id AS user_id, dl.discord_user_id AS linked_discord_id
            FROM users u
            LEFT JOIN discord_links dl ON dl.user_id = u.id
            WHERE u.lc_username=?
            """,
            (lc_username,),
        ).fetchone()
        if target and target["linked_discord_id"] and target["linked_discord_id"] != discord_user_id:
            return False, "That LeetCode username is already linked by another Discord user."

        if current and current["lc_username"] == lc_username:
            # Same logical link, just refresh the cached Discord username.
            c.execute(
                "UPDATE discord_links SET discord_username=? WHERE discord_user_id=?",
                (discord_username, discord_user_id),
            )
            return True, (
                f"Linked to LeetCode: {lc_username}. "
                "Use /join in a channel to enter that leaderboard."
            )

        if target is None:
            if current:
                # This is the non-destructive "switch my LC username" path for an existing Discord user.
                # Reuse the same shared user row so Discord channel memberships and solve history stay attached.
                user_id = current["user_id"]
                old_lc_username = current["lc_username"]
                c.execute(
                    "UPDATE users SET lc_username=? WHERE id=?",
                    (lc_username, user_id),
                )
                # Move the poll cursor to the new LC username so the bot does not backfill the old account.
                c.execute(
                    "DELETE FROM last_seen WHERE lc_username=?",
                    (old_lc_username,),
                )
                c.execute(
                    """
                    INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)
                    ON CONFLICT(lc_username) DO UPDATE SET last_seen_ts=excluded.last_seen_ts
                    """,
                    (lc_username, now),
                )
            else:
                # Brand-new shared user: create the identity row and start tracking from "now".
                cur = c.execute(
                    "INSERT INTO users(lc_username, created_at) VALUES(?, ?)",
                    (lc_username, now),
                )
                user_id = cur.lastrowid
                c.execute(
                    "INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)",
                    (lc_username, now),
                )
        else:
            # The target LC user already exists, so attach this Discord account to that shared user.
            user_id = target["user_id"]
            row = c.execute(
                "SELECT 1 FROM last_seen WHERE lc_username=?",
                (lc_username,),
            ).fetchone()
            if row is None:
                c.execute(
                    "INSERT INTO last_seen(lc_username, last_seen_ts) VALUES(?, ?)",
                    (lc_username, now),
                )

        if current is None:
            # First Discord link for this caller.
            c.execute(
                """
                INSERT INTO discord_links(discord_user_id, user_id, discord_username)
                VALUES(?, ?, ?)
                """,
                (discord_user_id, user_id, discord_username),
            )
        else:
            old_user_id = current["user_id"]
            if old_user_id != user_id:
                # Moving a Discord account onto another shared user should also move its Discord channel memberships.
                c.execute(
                    """
                    INSERT OR IGNORE INTO discord_channel_memberships(guild_id, channel_id, user_id)
                    SELECT guild_id, channel_id, ? FROM discord_channel_memberships WHERE user_id=?
                    """,
                    (user_id, old_user_id),
                )
                c.execute(
                    "DELETE FROM discord_channel_memberships WHERE user_id=?",
                    (old_user_id,),
                )
            # Point the Discord account at the final shared user row and refresh the cached username.
            c.execute(
                """
                UPDATE discord_links
                SET user_id=?, discord_username=?
                WHERE discord_user_id=?
                """,
                (user_id, discord_username, discord_user_id),
            )

        return True, f"Linked to LeetCode: {lc_username}. Use /join in a channel to enter that leaderboard."


def relink_discord_account(discord_user_id: str, discord_username: str, lc_username: str):
    with conn() as c:
        target = c.execute(
            """
            SELECT u.id AS user_id, dl.discord_user_id AS linked_discord_id
            FROM users u
            LEFT JOIN discord_links dl ON dl.user_id = u.id
            WHERE u.lc_username=?
            """,
            (lc_username,),
        ).fetchone()
        if not target:
            return False, "That LeetCode username isn't linked yet. Use /link first."

        current = c.execute(
            """
            SELECT user_id
            FROM discord_links
            WHERE discord_user_id=?
            """,
            (discord_user_id,),
        ).fetchone()
        if current and current["user_id"] != target["user_id"]:
            other = c.execute(
                "SELECT lc_username FROM users WHERE id=?",
                (current["user_id"],),
            ).fetchone()
            return False, (
                f"Your Discord is already linked to LeetCode '{other['lc_username']}'. "
                f"Use /link {lc_username} if you want to switch this Discord account."
            )

        linked_discord_id = target["linked_discord_id"]
        if linked_discord_id == discord_user_id:
            c.execute(
                "UPDATE discord_links SET discord_username=? WHERE discord_user_id=?",
                (discord_username, discord_user_id),
            )
            return True, f"You're already linked to {lc_username}. I refreshed your Discord username."

        if linked_discord_id is not None:
            c.execute(
                "DELETE FROM discord_links WHERE discord_user_id=?",
                (linked_discord_id,),
            )

        c.execute(
            """
            INSERT INTO discord_links(discord_user_id, user_id, discord_username)
            VALUES(?, ?, ?)
            """,
            (discord_user_id, target["user_id"], discord_username),
        )
        return True, f"Relinked {lc_username} to your Discord account."


def unlink_discord_account(discord_user_id: str):
    with conn() as c:
        link = c.execute(
            """
            SELECT dl.user_id, u.lc_username
            FROM discord_links dl
            JOIN users u ON u.id = dl.user_id
            WHERE dl.discord_user_id=?
            """,
            (discord_user_id,),
        ).fetchone()
        if not link:
            return False, "You don't have a linked LeetCode account."

        user_id = link["user_id"]
        lc_username = link["lc_username"]
        c.execute(
            "DELETE FROM discord_channel_memberships WHERE user_id=?",
            (user_id,),
        )
        c.execute(
            "DELETE FROM discord_links WHERE discord_user_id=?",
            (discord_user_id,),
        )

        if not _user_has_any_links(c, user_id):
            c.execute("DELETE FROM last_seen WHERE lc_username=?", (lc_username,))
            c.execute("DELETE FROM users WHERE id=?", (user_id,))

        return True, "Unlinked your Discord account from LeetCode."


def _user_has_any_links(c: sqlite3.Connection, user_id: int) -> bool:
    tg = c.execute(
        "SELECT 1 FROM telegram_links WHERE user_id=?",
        (user_id,),
    ).fetchone()
    if tg:
        return True
    dc = c.execute(
        "SELECT 1 FROM discord_links WHERE user_id=?",
        (user_id,),
    ).fetchone()
    return dc is not None


def set_chat(chat_id: int, title: str, tz: str = None, post_on_solve: int = None, scoring: str = None):
    with conn() as c:
        c.execute(
            """
            INSERT INTO chats(chat_id, title) VALUES(?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title
            """,
            (chat_id, title),
        )
        if tz:
            c.execute("UPDATE chats SET tz=? WHERE chat_id=?", (tz, chat_id))
        if post_on_solve is not None:
            c.execute(
                "UPDATE chats SET post_on_solve=? WHERE chat_id=?",
                (post_on_solve, chat_id),
            )
        if scoring:
            c.execute("UPDATE chats SET scoring=? WHERE chat_id=?", (scoring, chat_id))


def set_discord_channel(guild_id: str, channel_id: str, post_on_solve: int = None, scoring: str = None):
    with conn() as c:
        c.execute(
            """
            INSERT INTO discord_channels(guild_id, channel_id) VALUES(?, ?)
            ON CONFLICT(guild_id, channel_id) DO NOTHING
            """,
            (guild_id, channel_id),
        )
        if post_on_solve is not None:
            c.execute(
                """
                UPDATE discord_channels
                SET post_on_solve=?
                WHERE guild_id=? AND channel_id=?
                """,
                (post_on_solve, guild_id, channel_id),
            )
        if scoring:
            c.execute(
                """
                UPDATE discord_channels
                SET scoring=?
                WHERE guild_id=? AND channel_id=?
                """,
                (scoring, guild_id, channel_id),
            )


def join_chat(chat_id: int, telegram_user_id: int):
    with conn() as c:
        link = c.execute(
            "SELECT user_id FROM telegram_links WHERE telegram_user_id=?",
            (telegram_user_id,),
        ).fetchone()
        if not link:
            return False
        c.execute(
            "INSERT OR IGNORE INTO memberships(chat_id, user_id) VALUES(?, ?)",
            (chat_id, link["user_id"]),
        )
        return True


def leave_chat(chat_id: int, telegram_user_id: int):
    with conn() as c:
        link = c.execute(
            "SELECT user_id FROM telegram_links WHERE telegram_user_id=?",
            (telegram_user_id,),
        ).fetchone()
        if not link:
            return False
        c.execute(
            "DELETE FROM memberships WHERE chat_id=? AND user_id=?",
            (chat_id, link["user_id"]),
        )
        return True


def join_discord_channel(guild_id: str, channel_id: str, discord_user_id: str):
    with conn() as c:
        link = c.execute(
            "SELECT user_id FROM discord_links WHERE discord_user_id=?",
            (discord_user_id,),
        ).fetchone()
        if not link:
            return False
        c.execute(
            """
            INSERT OR IGNORE INTO discord_channel_memberships(guild_id, channel_id, user_id)
            VALUES(?, ?, ?)
            """,
            (guild_id, channel_id, link["user_id"]),
        )
        return True


def leave_discord_channel(guild_id: str, channel_id: str, discord_user_id: str):
    with conn() as c:
        link = c.execute(
            "SELECT user_id FROM discord_links WHERE discord_user_id=?",
            (discord_user_id,),
        ).fetchone()
        if not link:
            return False
        c.execute(
            """
            DELETE FROM discord_channel_memberships
            WHERE guild_id=? AND channel_id=? AND user_id=?
            """,
            (guild_id, channel_id, link["user_id"]),
        )
        return True


def get_user_chats(user_id: int):
    with conn() as c:
        return c.execute(
            """
            SELECT c.chat_id, c.post_on_solve, c.scoring
            FROM memberships m
            JOIN chats c ON c.chat_id = m.chat_id
            WHERE m.user_id=?
            """,
            (user_id,),
        ).fetchall()


def get_user_discord_channels(user_id: int):
    with conn() as c:
        return c.execute(
            """
            SELECT dc.guild_id, dc.channel_id, dc.post_on_solve, dc.scoring
            FROM discord_channel_memberships dcm
            JOIN discord_channels dc
              ON dc.guild_id = dcm.guild_id
             AND dc.channel_id = dcm.channel_id
            WHERE dcm.user_id=?
            """,
            (user_id,),
        ).fetchall()


def get_all_telegram_chats():
    with conn() as c:
        return c.execute(
            "SELECT chat_id, scoring FROM chats ORDER BY chat_id"
        ).fetchall()


def get_all_discord_channels():
    with conn() as c:
        return c.execute(
            """
            SELECT guild_id, channel_id, scoring
            FROM discord_channels
            ORDER BY guild_id, channel_id
            """
        ).fetchall()


def get_chat_scoring(chat_id: int) -> Optional[str]:
    with conn() as c:
        row = c.execute(
            "SELECT scoring FROM chats WHERE chat_id=?",
            (chat_id,),
        ).fetchone()
        return row["scoring"] if row else None


def get_discord_channel_scoring(guild_id: str, channel_id: str) -> Optional[str]:
    with conn() as c:
        row = c.execute(
            """
            SELECT scoring
            FROM discord_channels
            WHERE guild_id=? AND channel_id=?
            """,
            (guild_id, channel_id),
        ).fetchone()
        return row["scoring"] if row else None


def upsert_problem(slug: str, title: str, difficulty: str):
    with conn() as c:
        c.execute(
            "INSERT OR IGNORE INTO problems(slug, title, difficulty) VALUES(?, ?, ?)",
            (slug, title, difficulty),
        )


def get_problem(slug: str):
    with conn() as c:
        return c.execute(
            "SELECT slug, title, difficulty FROM problems WHERE slug=?",
            (slug,),
        ).fetchone()


def insert_completion(user_id: int, slug: str, solved_at_utc: int) -> bool:
    thirty_days = 30 * 86400
    with conn() as c:
        row = c.execute(
            """
            SELECT id, solved_at_utc
            FROM completions
            WHERE user_id=? AND slug=? AND is_deleted=0
            """,
            (user_id, slug),
        ).fetchone()

        if row is None:
            c.execute(
                """
                INSERT INTO completions(user_id, slug, solved_at_utc, is_deleted)
                VALUES(?, ?, ?, 0)
                """,
                (user_id, slug, solved_at_utc),
            )
            return True

        if solved_at_utc - row["solved_at_utc"] >= thirty_days:
            c.execute("UPDATE completions SET is_deleted=1 WHERE id=?", (row["id"],))
            c.execute(
                """
                INSERT INTO completions(user_id, slug, solved_at_utc, is_deleted)
                VALUES(?, ?, ?, 0)
                """,
                (user_id, slug, solved_at_utc),
            )
            return True

        return False


def get_user_counts(user_id: int, start: Optional[int] = None, end: Optional[int] = None):
    sql = """
        SELECT p.difficulty, COUNT(*) AS c
        FROM completions co
        JOIN problems p ON p.slug = co.slug
        WHERE co.user_id=? AND co.is_deleted=0
    """
    params: list[int] = [user_id]
    if start is not None:
        sql += " AND co.solved_at_utc>=?"
        params.append(start)
    if end is not None:
        sql += " AND co.solved_at_utc<?"
        params.append(end)
    sql += " GROUP BY p.difficulty"
    with conn() as c:
        rows = c.execute(sql, params).fetchall()
    return {row["difficulty"]: row["c"] for row in rows}


def weekly_counts(chat_id: int, start: int, end: int):
    with conn() as c:
        return c.execute(
            """
            SELECT co.user_id, p.difficulty, COUNT(*) AS c
            FROM completions co
            JOIN problems p ON p.slug = co.slug
            JOIN memberships m ON m.user_id = co.user_id
            WHERE m.chat_id = ?
              AND co.solved_at_utc >= ?
              AND co.solved_at_utc < ?
              AND co.is_deleted = 0
            GROUP BY co.user_id, p.difficulty
            """,
            (chat_id, start, end),
        ).fetchall()


def weekly_counts_discord(guild_id: str, channel_id: str, start: int, end: int):
    with conn() as c:
        return c.execute(
            """
            SELECT co.user_id, p.difficulty, COUNT(*) AS c
            FROM completions co
            JOIN problems p ON p.slug = co.slug
            JOIN discord_channel_memberships dcm ON dcm.user_id = co.user_id
            WHERE dcm.guild_id = ?
              AND dcm.channel_id = ?
              AND co.solved_at_utc >= ?
              AND co.solved_at_utc < ?
              AND co.is_deleted = 0
            GROUP BY co.user_id, p.difficulty
            """,
            (guild_id, channel_id, start, end),
        ).fetchall()


def get_any_platform_identity(user_id: int):
    with conn() as c:
        row = c.execute(
            """
            SELECT
              u.lc_username,
              tl.telegram_user_id,
              tl.tg_username,
              dl.discord_user_id,
              dl.discord_username
            FROM users u
            LEFT JOIN telegram_links tl ON tl.user_id = u.id
            LEFT JOIN discord_links dl ON dl.user_id = u.id
            WHERE u.id=?
            """,
            (user_id,),
        ).fetchone()
        return row
