"""database.py - SQLite operations."""

# This file handles all the database stuff for storing land listings.
# It uses SQLite, which is just a lightweight database that lives in a single file.
# No server needed, no config hassle. Perfect for a scraper like this.

import sqlite3, pathlib  # sqlite3 talks to the database, pathlib helps us handle file paths
from config import DB_PATH  # pull in the database file path from our config

# path setup
# We need the database file to exist somewhere on disk before we can use it.
# This makes sure the folder it lives in is there, even on first run.

# create the database connection
def get_connection():
    # First, figure out which folder the database file sits in.
    pathlib.Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)  # parents=True means "create any missing parent folders too"
    return sqlite3.connect(DB_PATH, check_same_thread=False)  # check_same_thread=False lets scrapers running in different threads use the same connection


# set up the tables if they don't exist
def init_db():
    # Grab a connection so we can run queries
    conn = get_connection()
    # Create the lands table if it's not already there.
    # Each column holds one piece of info about a land listing.
    conn.execute('''CREATE TABLE IF NOT EXISTS lands (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT, source_id TEXT, title TEXT, price REAL,
        url TEXT, location TEXT, description TEXT, score INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source, source_id))''')
    conn.commit()  # actually write the table creation to disk
    return conn  # hand back the connection so the caller can use it


# wipe all listings so we start fresh
def clear_old(conn):
    # Deletes every row in the lands table. We do this at the start of each scrape
    # so we're only working with current data, not stale stuff from last week.
    conn.execute("DELETE FROM lands")
    conn.commit()  # make sure the deletes actually stick


# save a single listing to the database
def save_listing(conn, source, source_id, title, price, url, location, description, score):
    # We need a cursor to execute queries one at a time
    c = conn.cursor()
    # INSERT OR IGNORE means: if this exact source+source_id combo already exists,
    # just skip it silently instead of throwing an error.
    # The ? marks are placeholders that get filled in by the tuple below,
    # which keeps us safe from SQL injection attacks.
    c.execute('INSERT OR IGNORE INTO lands (source,source_id,title,price,url,location,description,score) VALUES (?,?,?,?,?,?,?,?)',
        (source, source_id, title[:150], price, url, location, (description or '')[:500], score))
        # title[:150] clips the title to 150 chars so we don't store junk
        # (description or '')[:500] does the same for the description, but first
        # handles the case where description is None by swapping in an empty string
    conn.commit()  # flush the insert to disk
    return c.rowcount > 0  # returns True if a new row was actually inserted, False if it was a duplicate


# grab the best listings by score
def get_top_listings(conn, limit=20):
    # Fetches the top `limit` listings, sorted by score (highest first)
    # then by price (lowest first) as a tiebreaker.
    # Only grabs the columns we actually display in the CLI output.
    return conn.execute('SELECT title,price,url,location,score,source FROM lands ORDER BY score DESC,price ASC LIMIT ?', (limit,)).fetchall()
    # .fetchall() runs the query and returns all matching rows as a list of tuples


# get a quick count of how many listings we have total and how many are good
def get_stats(conn):
    # Count every row in the table
    total = conn.execute('SELECT COUNT(*) FROM lands').fetchone()[0]  # fetchone() returns a tuple like (42,)
    # Count only the ones scoring 50 or higher (our "worth looking at" threshold)
    good = conn.execute('SELECT COUNT(*) FROM lands WHERE score>=50').fetchone()[0]
    return total, good  # returns both counts as a simple tuple
