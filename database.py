"""
database.py - Database operations.
"""

import sqlite3
import pathlib
from config import DB_PATH


def get_connection():
    """Get a database connection."""
    pathlib.Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db():
    """Create tables if they don't exist."""
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS lands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        source_id TEXT,
        title TEXT,
        price REAL,
        url TEXT,
        location TEXT,
        description TEXT,
        score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, source_id)
    )''')
    conn.commit()
    return conn


def clear_old(conn):
    """Clear old listings."""
    conn.execute("DELETE FROM lands")
    conn.commit()


def save_listing(conn, source, source_id, title, price, url, location, description, score):
    """Save a listing. Returns True if new."""
    c = conn.cursor()
    c.execute('''INSERT OR IGNORE INTO lands
        (source, source_id, title, price, url, location, description, score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (source, source_id, title[:150], price, url, location, description[:500] if description else '', score))
    conn.commit()
    return c.rowcount > 0


def get_top_listings(conn, limit=20):
    """Get top scored listings."""
    c = conn.cursor()
    c.execute('''SELECT title, price, url, location, score, source FROM lands
        ORDER BY score DESC, price ASC LIMIT ?''', (limit,))
    return c.fetchall()


def get_stats(conn):
    """Get summary stats."""
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM lands')
    total = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM lands WHERE score >= 50')
    good = c.fetchone()[0]
    return total, good
