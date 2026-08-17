"""database.py - SQLite operations."""

import sqlite3, pathlib
from config import DB_PATH


def get_connection():
    pathlib.Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS lands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT, source_id TEXT, title TEXT, price REAL,
        url TEXT, location TEXT, description TEXT, score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, source_id))''')
    conn.commit()
    return conn


def clear_old(conn):
    conn.execute("DELETE FROM lands")
    conn.commit()


def save_listing(conn, source, source_id, title, price, url, location, description, score):
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO lands (source,source_id,title,price,url,location,description,score) VALUES (?,?,?,?,?,?,?,?)',
        (source, source_id, title[:150], price, url, location, (description or '')[:500], score))
    conn.commit()
    return c.rowcount > 0


def get_top_listings(conn, limit=20):
    return conn.execute('SELECT title,price,url,location,score,source FROM lands ORDER BY score DESC,price ASC LIMIT ?', (limit,)).fetchall()


def get_stats(conn):
    total = conn.execute('SELECT COUNT(*) FROM lands').fetchone()[0]
    good = conn.execute('SELECT COUNT(*) FROM lands WHERE score>=50').fetchone()[0]
    return total, good
