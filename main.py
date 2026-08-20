"""main.py - Entry point."""  # docstring so I remember what this file is when I come back to it later

import argparse  # handles command-line arguments so I can run different modes from the terminal
from datetime import datetime  # need the current timestamp so I can log when each run happened
from database import init_db, clear_old, get_top_listings, get_stats, get_all_listings  # pull in the database helpers
from scraper import scrape_all  # the function that actually goes out and grabs listings from the web
from history import save_daily_summary  # saves a snapshot of today's data so I can track trends over time


def list_mode(conn):
    """Prints all listings sorted by price, useful for browsing from the terminal."""
    listings = get_all_listings(conn)  # fetch every listing from the database
    if not listings:  # nothing in the database yet
        print('No listings found. Run a scrape first.')  # tell the user to scrape first
        return  # bail out
    print(f'\n{"="*80}')  # opening separator line
    print(f'  ALL LISTINGS ({len(listings)} total, sorted by price)')  # header showing count
    print(f'{"="*80}\n')  # closing separator
    for score, price, title, url, location, source in listings:  # loop through every listing
        print(f'[{score:3d}] ${price:>9,.0f}  {title[:55]}')  # score, price, title
        print(f'      {source:20s} | {location or "":20s} | {url}')  # source, location, link
    print(f'\n{"="*80}')  # closing separator
    print(f'  Total: {len(listings)} listings')  # final count


def scrape_mode(conn):
    """Runs the full scrape and sends Discord alerts."""
    clear_old(conn)  # wipe anything older than 30 days so the DB doesn't bloat with stale listings
    print(f'Land scrape {datetime.now()} — south Flagstaff, north Tucson')  # stamp the run with the current time
    saved = scrape_all(conn)  # hit every source site and store new/updated listings
    total, good = get_stats(conn)  # grab the total listing count and how many scored 50 or above
    print(f'\nNew: {saved} | DB: {total} total, {good} good (>=50)')  # quick summary
    save_daily_summary(conn)  # write today's numbers to the history table
    print('\n--- TOP LISTINGS ---')  # header for the best stuff
    for t, p, u, loc, sc, src in get_top_listings(conn):  # loop through the highest-scoring listings
        print(f'[{sc}] ${p:,.0f} - {t[:55]}')  # score, price, title
        print(f'    {src} | {u}')  # source and link


def report_mode(conn):
    """Generates a static HTML report for GitHub Pages hosting."""
    from report import generate_report  # import here so it only loads when needed
    path = generate_report(conn)  # build the HTML file
    print(f'Report generated: {path}')  # tell the user where the file is


def main():
    parser = argparse.ArgumentParser(description='Arizona Land Scraper')  # set up the argument parser
    group = parser.add_mutually_exclusive_group()  # only one mode at a time
    group.add_argument('--list', action='store_true', help='Browse all listings from terminal')  # list mode
    group.add_argument('--report', action='store_true', help='Generate HTML report for GitHub Pages')  # report mode
    args = parser.parse_args()  # parse the command-line arguments

    conn = init_db()  # create the database file and tables if they don't exist yet

    if args.list:  # user wants to browse listings from terminal
        list_mode(conn)  # print all listings sorted by price
    elif args.report:  # user wants to generate the HTML report
        report_mode(conn)  # build the static HTML file
    else:  # default: run the scrape
        scrape_mode(conn)  # scrape sites and send Discord alerts

    conn.close()  # close the database connection cleanly


if __name__ == '__main__':  # only run main() if I execute this file directly
    main()  # kick off the whole flow
