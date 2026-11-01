from contextlib import contextmanager
import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "guardian.db")

# Canonical lock columns and display titles in Arabic
LOCK_COLUMNS = {
    "chat": "الشات",
    "photos": "الصور",
    "videos": "الفيديو",
    "gifs": "المتحركات",
    "stickers": "الستكرات",
    "voice": "الصوت",
    "forward": "التوجيه",
    "links": "الروابط",
    "usernames": "المعرفات",
    "tags": "التاك",
    "files": "الملفات",
    "contacts": "جهات الاتصال",
    "spam": "الكلايش",
    "bots": "البوتات",
}

# Aliases mapped to lock column keys for flexible command parsing
LOCK_ALIASES = {
    # Chat
    "الشات": "chat",
    "شات": "chat",
    "الدردشة": "chat",
    "دردشة": "chat",
    # Photos
    "الصور": "photos",
    "صور": "photos",
    "الصوره": "photos",
    "صوره": "photos",
    # Videos
    "الفيديو": "videos",
    "فيديو": "videos",
    "الفيديوهات": "videos",
    "فيديوهات": "videos",
    # GIFs
    "المتحركات": "gifs",
    "متحركات": "gifs",
    "المتحركه": "gifs",
    "متحركه": "gifs",
    "جيف": "gifs",
    # Stickers
    "الستكرات": "stickers",
    "ستكرات": "stickers",
    "الستيكرات": "stickers",
    "ستيكرات": "stickers",
    "الملصقات": "stickers",
    "ملصقات": "stickers",
    # Voice / Audio
    "الصوت": "voice",
    "صوت": "voice",
    "البصمات": "voice",
    "بصمات": "voice",
    "البصمه": "voice",
    "بصمة": "voice",
    "الصوتيات": "voice",
    "صوتيات": "voice",
    # Forwards
    "التوجيه": "forward",
    "توجيه": "forward",
    "اعادة توجيه": "forward",
    "إعادة توجيه": "forward",
    # Links
    "الروابط": "links",
    "روابط": "links",
    "الرابط": "links",
    "رابط": "links",
    "اللينكات": "links",
    "لينكات": "links",
    # Usernames
    "المعرفات": "usernames",
    "معرفات": "usernames",
    "المعرف": "usernames",
    "معرف": "usernames",
    "اليوزرات": "usernames",
    "يوزرات": "usernames",
    # Tags / Mentions
    "التاك": "tags",
    "تاك": "tags",
    "المنشن": "tags",
    "منشن": "tags",
    # Files
    "الملفات": "files",
    "ملفات": "files",
    "الملف": "files",
    "ملف": "files",
    "المستندات": "files",
    "مستندات": "files",
    # Contacts
    "جهات الاتصال": "contacts",
    "جهات اتصال": "contacts",
    "الجهات": "contacts",
    "جهات": "contacts",
    # Spam / long text
    "الكلايش": "spam",
    "كلايش": "spam",
    "الكليشه": "spam",
    "كليشه": "spam",
    "التكرار": "spam",
    # Bots
    "البوتات": "bots",
    "بوتات": "bots",
    "البوت": "bots",
    "بوت": "bots",
}


@contextmanager
def get_connection(db_path=None):
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path=None):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_locks (
                chat_id INTEGER PRIMARY KEY,
                chat INTEGER DEFAULT 0,
                photos INTEGER DEFAULT 0,
                videos INTEGER DEFAULT 0,
                gifs INTEGER DEFAULT 0,
                stickers INTEGER DEFAULT 0,
                voice INTEGER DEFAULT 0,
                forward INTEGER DEFAULT 0,
                links INTEGER DEFAULT 0,
                usernames INTEGER DEFAULT 0,
                tags INTEGER DEFAULT 0,
                files INTEGER DEFAULT 0,
                contacts INTEGER DEFAULT 0,
                spam INTEGER DEFAULT 0,
                bots INTEGER DEFAULT 0
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS muted_members (
                chat_id INTEGER,
                user_id INTEGER,
                name TEXT,
                until_date TEXT,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS banned_members (
                chat_id INTEGER,
                user_id INTEGER,
                name TEXT,
                PRIMARY KEY (chat_id, user_id)
            )
            """
        )
        conn.commit()


def get_chat_locks(chat_id: int, db_path=None) -> dict:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM chat_locks WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if not row:
            columns = list(LOCK_COLUMNS.keys())
            placeholders = ", ".join(["0"] * len(columns))
            cols_str = ", ".join(columns)
            cursor.execute(
                f"INSERT INTO chat_locks (chat_id, {cols_str}) VALUES (?, {placeholders})",
                (chat_id,),
            )
            conn.commit()
            return {k: False for k in LOCK_COLUMNS}
        return {k: bool(row[k]) for k in LOCK_COLUMNS}


def set_chat_lock(chat_id: int, lock_name: str, status: bool, db_path=None) -> bool:
    if lock_name not in LOCK_COLUMNS:
        return False
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Ensure row exists
        get_chat_locks(chat_id, db_path)
        cursor.execute(
            f"UPDATE chat_locks SET {lock_name} = ? WHERE chat_id = ?",
            (1 if status else 0, chat_id),
        )
        conn.commit()
        return True


def set_all_chat_locks(chat_id: int, status: bool, db_path=None):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        get_chat_locks(chat_id, db_path)
        set_statements = ", ".join([f"{col} = ?" for col in LOCK_COLUMNS])
        val = 1 if status else 0
        params = [val] * len(LOCK_COLUMNS) + [chat_id]
        cursor.execute(
            f"UPDATE chat_locks SET {set_statements} WHERE chat_id = ?",
            params,
        )
        conn.commit()


def save_muted_member(chat_id: int, user_id: int, name: str, until_date, db_path=None):
    until_str = until_date.isoformat() if isinstance(until_date, datetime) else str(until_date) if until_date else None
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO muted_members (chat_id, user_id, name, until_date) VALUES (?, ?, ?, ?)",
            (chat_id, user_id, name, until_str),
        )
        conn.commit()


def remove_muted_member(chat_id: int, user_id: int, db_path=None):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM muted_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        conn.commit()


def get_muted_members(chat_id: int, db_path=None) -> dict:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, name, until_date FROM muted_members WHERE chat_id = ?",
            (chat_id,),
        )
        rows = cursor.fetchall()
        result = {}
        for r in rows:
            until_dt = None
            if r["until_date"]:
                try:
                    until_dt = datetime.fromisoformat(r["until_date"])
                except Exception:
                    until_dt = None
            result[r["user_id"]] = (r["name"], until_dt)
        return result


def save_banned_member(chat_id: int, user_id: int, name: str, db_path=None):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO banned_members (chat_id, user_id, name) VALUES (?, ?, ?)",
            (chat_id, user_id, name),
        )
        conn.commit()


def remove_banned_member(chat_id: int, user_id: int, db_path=None):
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM banned_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        )
        conn.commit()


def get_banned_members(chat_id: int, db_path=None) -> dict:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, name FROM banned_members WHERE chat_id = ?",
            (chat_id,),
        )
        rows = cursor.fetchall()
        return {r["user_id"]: r["name"] for r in rows}
