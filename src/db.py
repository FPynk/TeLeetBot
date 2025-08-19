import sqlite3, time
from contextlib import contextmanager
from typing import Optional

@contextmanager
def conn(db_path="bot.db"):
    c = sqlite3.connect(db_path)
    c.execute("PRAGMA journal_mode=WAL;")
    c.execute("PRAGMA foreign_keys=ON;")
    try:
        yield c
        c.commit()
    finally:
        c.close()

SCHEMA_SQL = open(__file__.replace("db.py","schema.sql"), "w+")  # not used; for brevity

def init():
    with conn() as c:
        c.executescript("""
        PRAGMA foreign_keys=ON;

        CREATE TABLE IF NOT EXISTS users (
          telegram_user_id INTEGER PRIMARY KEY,
          tg_username      TEXT,
          lc_username      TEXT UNIQUE NOT NULL,
          created_at       INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chats (
          chat_id       INTEGER PRIMARY KEY,
          title         TEXT,
          tz            TEXT NOT NULL DEFAULT 'America/Chicago',
          post_on_solve INTEGER NOT NULL DEFAULT 1,
          scoring       TEXT NOT NULL DEFAULT '1,2,5'
        );

        CREATE TABLE IF NOT EXISTS memberships (
          chat_id           INTEGER NOT NULL,
          telegram_user_id  INTEGER NOT NULL,
          PRIMARY KEY (chat_id, telegram_user_id),
          FOREIGN KEY (chat_id) REFERENCES chats(chat_id) ON DELETE CASCADE,
          FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS problems (
          slug        TEXT PRIMARY KEY,
          title       TEXT NOT NULL,
          difficulty  TEXT NOT NULL CHECK (difficulty IN ('Easy','Medium','Hard'))
        );

        CREATE TABLE IF NOT EXISTS completions (
          id               INTEGER PRIMARY KEY AUTOINCREMENT,
          telegram_user_id INTEGER NOT NULL,
          slug             TEXT NOT NULL,
          solved_at_utc    INTEGER NOT NULL,
          UNIQUE (telegram_user_id, slug),
          FOREIGN KEY (telegram_user_id) REFERENCES users(telegram_user_id) ON DELETE CASCADE,
          FOREIGN KEY (slug) REFERENCES problems(slug) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_completions_user_time ON completions(telegram_user_id, solved_at_utc);

        CREATE TABLE IF NOT EXISTS last_seen (
          lc_username TEXT PRIMARY KEY,
          last_seen_ts INTEGER NOT NULL
        );
        """)

def upsert_user(telegram_user_id:int, tg_username:str, lc_username:str):
    now=int(time.time())
    with conn() as c:
        c.execute("""
          INSERT INTO users(telegram_user_id,tg_username,lc_username,created_at)
          VALUES(?,?,?,?)
          ON CONFLICT(telegram_user_id) DO UPDATE SET
            tg_username=excluded.tg_username,
            lc_username=excluded.lc_username
        """,(telegram_user_id,tg_username,lc_username,now))

def set_chat(chat_id:int, title:str, tz:str=None, post_on_solve:int=None, scoring:str=None):
    with conn() as c:
        # upsert with defaults
        c.execute("""
          INSERT INTO chats(chat_id,title) VALUES(?,?)
          ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title
        """,(chat_id,title))
        if tz:
            c.execute("UPDATE chats SET tz=? WHERE chat_id=?", (tz,chat_id))
        if post_on_solve is not None:
            c.execute("UPDATE chats SET post_on_solve=? WHERE chat_id=?", (post_on_solve,chat_id))
        if scoring:
            c.execute("UPDATE chats SET scoring=? WHERE chat_id=?", (scoring,chat_id))

def join_chat(chat_id:int, telegram_user_id:int):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO memberships(chat_id,telegram_user_id) VALUES(?,?)",(chat_id,telegram_user_id))

def leave_chat(chat_id:int, telegram_user_id:int):
    with conn() as c:
        c.execute("DELETE FROM memberships WHERE chat_id=? AND telegram_user_id=?",(chat_id,telegram_user_id))

def get_tracked_users():
    with conn() as c:
        return c.execute("SELECT telegram_user_id, lc_username FROM users").fetchall()

def get_user_chats(telegram_user_id:int):
    with conn() as c:
        return c.execute("""
          SELECT c.chat_id, c.post_on_solve, c.scoring FROM memberships m
          JOIN chats c ON c.chat_id=m.chat_id
          WHERE m.telegram_user_id=?
        """,(telegram_user_id,)).fetchall()

def get_or_set_last_seen(lc_username: str, ts: Optional[int] = None):
    with conn() as c:
        if ts is None:
            row = c.execute(
                "SELECT last_seen_ts FROM last_seen WHERE lc_username=?",
                (lc_username,),
            ).fetchone()
            return row[0] if row else 0
        else:
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
                    "INSERT INTO last_seen(lc_username,last_seen_ts) VALUES(?,?)",
                    (lc_username, ts),
                )
            return ts

def upsert_problem(slug:str, title:str, difficulty:str):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO problems(slug,title,difficulty) VALUES(?,?,?)", (slug,title,difficulty))

def insert_completion(telegram_user_id:int, slug:str, solved_at_utc:int) -> bool:
    with conn() as c:
        try:
            c.execute("INSERT INTO completions(telegram_user_id,slug,solved_at_utc) VALUES(?,?,?)",
                      (telegram_user_id, slug, solved_at_utc))
            return True
        except sqlite3.IntegrityError:
            return False  # duplicate slug for this user

def weekly_counts(chat_id:int, start:int, end:int):
    with conn() as c:
        return c.execute("""
            SELECT co.telegram_user_id, p.difficulty, COUNT(*) AS c
            FROM completions AS co
            JOIN problems   AS p ON p.slug = co.slug
            JOIN memberships AS m ON m.telegram_user_id = co.telegram_user_id
            WHERE m.chat_id = ?
              AND co.solved_at_utc >= ?
              AND co.solved_at_utc < ?
            GROUP BY co.telegram_user_id, p.difficulty
        """, (chat_id, start, end)).fetchall()
