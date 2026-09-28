import sqlite3
from config import DB_NAME


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE,
            username TEXT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            day1_sent INTEGER DEFAULT 0,
            day2_sent INTEGER DEFAULT 0,
            day3_sent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def save_user(telegram_id, username, full_name, phone):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, full_name, phone)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            full_name = excluded.full_name,
            phone = excluded.phone
    """, (telegram_id, username, full_name, phone))
    conn.commit()
    conn.close()


def mark_day_sent(telegram_id, day):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        f"UPDATE users SET day{day}_sent = 1 WHERE telegram_id = ?",
        (telegram_id,),
    )
    conn.commit()
    conn.close()


def user_exists(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_user(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT full_name FROM users WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def delete_user(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE telegram_id = ?", (telegram_id,))
    conn.commit()
    conn.close()


def get_users_for_restore():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT telegram_id, joined_at, day1_sent, day2_sent, day3_sent
        FROM users
        WHERE day1_sent = 0 OR day2_sent = 0 OR day3_sent = 0
    """)
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_full_user_info(telegram_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT full_name, phone, joined_at, 
        FROM users WHERE telegram_id = ?
    """, (telegram_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "full_name": row[0],
        "phone": row[1],
        "joined_at": row[2],
        "day1_sent": row[3],
        "day2_sent": row[4],
        "day3_sent": row[5],
    }