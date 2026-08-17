"""
scraper.py - All scraping logic for land listings.
"""

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
import time
import re
from filters import should_skip, score_listing
from config import CRAIGSLIST_REGIONS, PLAYWRIGHT_SITES, CL_LAND_PATH, GEO_BOUNDS


GENERIC_JS = """() => {
    const results = [];
    const seen = new Set();
    document.querySelectorAll('a').forEach(link => {
        const href = link.href;
        if (!href.includes('DOMAIN') || seen.has(href)) return;
        seen.add(href);
        const container = link.closest('li') || link.closest('article') || link.closest('div') || link;
        const text = (container.innerText || '').substring(0, 500);
        if (text.length > 20) {
            results.push({href, text});
        }
    });
    return results;
}"""


def scrape_all(conn):
    """Scrape Craigslist + all Playwright sites. Returns total saved."""
    from database import save_listing
    from discord import send_alert

    saved = 0
    saved += scrape_craigslist(conn, save_listing, send_alert)
    saved += scrape_playwright_sites(conn, save_listing, send_alert)
    return saved


def scrape_craigslist(conn, save_listing, send_alert):
    """Scrape Craigslist land listings."""
    saved = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

    for region in CRAIGSLIST_REGIONS:
        try:
            url = f'https://{region}.craigslist.org/search{CL_LAND_PATH}'
            r = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')

            for row in soup.find_all('li', class_='cl-static-search-result'):
                listing = parse_cl_row(row, region)
                if not listing:
                    continue

                title, price, href, location = listing

                if should_skip(title):
                    continue

                score = score_listing(title, '', price)

                if save_listing(conn, 'craigslist', href, title, price, href, location, '', score):
                    saved += 1
                    if score >= 40:
                        send_alert(title, price, href, location, score, 'craigslist')
        except:
            pass

    return saved


def scrape_playwright_sites(conn, save_listing, send_alert):
    """Scrape all Playwright-based sites. One browser per site."""
    saved = 0

    for site in PLAYWRIGHT_SITES:
        try:
            saved += scrape_one_site(conn, site, save_listing, send_alert)
        except Exception as e:
            print(f'  {site["name"]}: error - {e}')

    return saved


def scrape_one_site(conn, site, save_listing, send_alert):
    """Scrape one site with its own browser."""
    saved = 0
    name = site['name']
    domain = site['domain']
    url = site['url']
    js = GENERIC_JS.replace('DOMAIN', domain)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        Stealth().apply_stealth_sync(context)
        page = context.new_page()

        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            time.sleep(3)

            for _ in range(5):
                page.evaluate('window.scrollBy(0, 1000)')
                time.sleep(0.3)
        except:
            browser.close()
            return 0

        try:
            data = page.evaluate(js)
        except:
            browser.close()
            return 0

        for item in data:
            href = item.get('href', '')
            text = item.get('text', '')

            price_match = re.search(r'\$([\d,]+)', text)
            if not price_match:
                continue
            price = float(price_match.group(1).replace(',', ''))

            lines = [l.strip() for l in text.split('\n') if l.strip()]
            title = ''
            for line in lines:
                if len(line) > 10 and '$' not in line:
                    title = line
                    break
            if not title:
                title = lines[0] if lines else 'Land listing'

            if should_skip(title, text):
                continue

            score = score_listing(title, text, price)

            if save_listing(conn, name, href, title, price, href, '', text[:500], score):
                saved += 1
                if score >= 40:
                    send_alert(title, price, href, '', score, name)

        browser.close()

    print(f'  {name}: +{saved}')
    return saved


def parse_cl_row(row, region):
    """Parse a Craigslist search result row."""
    link = row.find('a', href=True)
    if not link:
        return None

    href = link['href']
    if not href.startswith('http'):
        href = f'https://{region}.craigslist.org' + href

    title_el = row.find('div', class_='title')
    title = title_el.text.strip() if title_el else ''

    price_el = row.find('div', class_='price')
    price_text = price_el.text.strip() if price_el else ''
    price_match = re.search(r'\$([\d,]+)', price_text)
    price = float(price_match.group(1).replace(',', '')) if price_match else 0

    loc_el = row.find('div', class_='location')
    location = loc_el.text.strip() if loc_el else region

    return title, price, href, location
