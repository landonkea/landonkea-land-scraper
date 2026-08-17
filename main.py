"""main.py - Entry point."""

from datetime import datetime
from database import init_db, clear_old, get_top_listings, get_stats
from scraper import scrape_all


def main():
    conn = init_db()
    clear_old(conn)
    print(f'Land scrape {datetime.now()} — south Flagstaff, north Tucson')
    saved = scrape_all(conn)
    total, good = get_stats(conn)
    print(f'\nNew: {saved} | DB: {total} total, {good} good (>=50)')
    print('\n--- TOP LISTINGS ---')
    for t, p, u, loc, sc, src in get_top_listings(conn):
        print(f'[{sc}] ${p:,.0f} - {t[:55]}')
        print(f'    {src} | {u}')
    conn.close()


if __name__ == '__main__':
    main()
