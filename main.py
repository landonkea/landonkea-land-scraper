"""
main.py - Entry point. Land scraper for Arizona.
"""

from datetime import datetime
from database import init_db, clear_old, get_top_listings, get_stats
from scraper import scrape_all


def main():
    conn = init_db()
    clear_old(conn)

    print(f'Starting land scrape at {datetime.now()}')
    print('Area: South of Flagstaff, North of Tucson')
    print('Focus: Cheapest land, water well + owner carry get bonus')

    saved = scrape_all(conn)
    print(f'\nTotal new listings: {saved}')

    total, good = get_stats(conn)
    print(f'Database: {total} total, {good} good (score >= 50)')

    print('\n--- TOP LISTINGS ---')
    for title, price, url, loc, score, source in get_top_listings(conn):
        print(f'[{score}] ${price:,.0f} - {title[:55]}')
        print(f'    {source} | {url}')

    conn.close()


if __name__ == '__main__':
    main()
