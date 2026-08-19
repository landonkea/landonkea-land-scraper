"""history.py - Append daily summary to history JSON for GitHub Pages."""
# This module saves a snapshot of each day's land listings to a JSON file
# so GitHub Pages can show charts of how the market changes over time.

import json, pathlib, statistics
# json lets me read and write the history file
# pathlib gives me cross-platform file path handling
# statistics has mean and median functions I use for price analysis

from datetime import datetime
# datetime gives me today's date for the summary record

from config import ROOT_DIR
# ROOT_DIR points to the project root so paths work no matter where I run this from

HISTORY_PATH = ROOT_DIR / 'docs' / 'data' / 'history.json'
# This is where the history JSON lives, inside the GitHub Pages docs folder

def save_daily_summary(conn):
    # conn is a SQLite database connection with all the current land listings

    """Append today's summary to history. Returns summary dict."""
    # The docstring tells other developers (or future me) what this function does

    pathlib.Path(HISTORY_PATH).parent.mkdir(parents=True, exist_ok=True)
    # Make sure the docs/data/ folder exists before I try to write the file
    # parents=True creates any missing parent dirs, exist_ok=True won't error if it's already there

    rows = conn.execute('SELECT title,price,location,score,source FROM lands').fetchall()
    # Pull every listing from the database so I can compute today's stats

    if not rows:
        return None
    # If there's nothing in the database yet, bail out early with None

    prices = [r[1] for r in rows if r[1] and r[1] > 0]
    # Grab just the prices from each row, skipping any that are missing or zero
    # This list gets used for mean and median calculations

    scores = [r[3] for r in rows]
    # Pull all the relevance scores so I can average them and count good listings

    sources = {}
    # I'll group stats by source (Zillow, Realtor, etc.) using this dictionary

    for r in rows:
        # Loop through every listing to break down numbers by source
        src = r[4]
        # r[4] is the source column, tells me which website this listing came from
        if src not in sources:
            sources[src] = {'count': 0, 'prices': []}
            # First time seeing this source, so set up its tracking dict
        sources[src]['count'] += 1
        # Bump the count for this source by one
        if r[1] and r[1] > 0:
            sources[src]['prices'].append(r[1])
            # Only add the price if it's a real positive number

    summary = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        # Today's date formatted as YYYY-MM-DD so it sorts nicely in JSON
        'total': len(rows),
        # How many listings we scraped today
        'good': len([s for s in scores if s >= 50]),
        # Count of listings with a score of 50 or higher, meaning they're worth looking at
        'avg_price': round(statistics.mean(prices)) if prices else 0,
        # The average price rounded to the nearest dollar, or 0 if there are no prices
        'median_price': round(statistics.median(prices)) if prices else 0,
        # Median price is less affected by outliers than the mean, useful for comparison
        'avg_score': round(statistics.mean(scores), 1),
        # Average relevance score with one decimal place for the charts
        'by_source': {
            # Break down the count and average price for each listing source
            src: {'count': d['count'], 'avg_price': round(statistics.mean(d['prices'])) if d['prices'] else 0}
            for src, d in sources.items()
            # Dictionary comprehension that builds a nested dict per source
        }
    }

    history = []
    # Start with an empty list in case the file doesn't exist yet

    if HISTORY_PATH.exists():
        # Only try to read the file if it's actually there
        try:
            history = json.loads(HISTORY_PATH.read_text())
            # Read the entire file as text and parse it into a Python list
        except (json.JSONDecodeError, OSError):
            # If the file is corrupted or unreadable, start fresh with an empty list
            history = []

    history.append(summary)
    # Add today's summary to the end of the history list

    HISTORY_PATH.write_text(json.dumps(history, indent=2))
    # Write the updated history back to disk with nice formatting so it's readable

    print(f'  History: day {len(history)} saved ({summary["total"]} listings, avg ${summary["avg_price"]:,.0f})')
    # Print a quick status line so I can see it worked when the script runs
    return summary
    # Hand back the summary dict in case the caller wants to do something with it
