"""main.py - Entry point."""  # docstring so I remember what this file is when I come back to it later

from datetime import datetime  # need the current timestamp so I can log when each run happened
from database import init_db, clear_old, get_top_listings, get_stats  # pull in the database helpers: setup, cleanup, querying
from scraper import scrape_all  # the function that actually goes out and grabs listings from the web
from history import save_daily_summary  # saves a snapshot of today's data so I can track trends over time


def main():
    conn = init_db()  # create the database file and tables if they don't exist yet, returns a connection I pass around
    clear_old(conn)  # wipe anything older than 30 days so the DB doesn't bloat with stale listings
    print(f'Land scrape {datetime.now()} — south Flagstaff, north Tucson')  # stamp the run with the current time and the areas I'm scanning
    saved = scrape_all(conn)  # hit every source site and store new/updated listings, count how many got saved
    total, good = get_stats(conn)  # grab the total listing count and how many scored 50 or above
    print(f'\nNew: {saved} | DB: {total} total, {good} good (>=50)')  # quick summary so I can see at a glance if anything looks off
    save_daily_summary(conn)  # write today's numbers to the history table for long-term tracking
    print('\n--- TOP LISTINGS ---')  # header for the best stuff about to print
    for t, p, u, loc, sc, src in get_top_listings(conn):  # loop through the highest-scoring listings, unpacking title, price, URL, location, score, and source
        print(f'[{sc}] ${p:,.0f} - {t[:55]}')  # show the score, price formatted with commas, and the first 55 chars of the title so it stays readable
        print(f'    {src} | {u}')  # print the source site and the full link underneath so I can click through
    conn.close()  # close the database connection cleanly, don't want to leave file handles dangling


if __name__ == '__main__':  # only run main() if I execute this file directly, not if something else imports it
    main()  # kick off the whole scrape-and-report flow
