"""scraper.py - Scraping logic for land listings."""

import re, time, requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from filters import should_skip, score_listing
from config import CRAIGSLIST_REGIONS, CL_LAND_PATH

LANDMODO_JS = """() => {
    const r = [];
    document.querySelectorAll('.search_result').forEach(el => {
        const text = (el.innerText || '').substring(0, 600);
        const link = el.querySelector('a[href*="/properties/"]');
        const href = link ? link.href : el.querySelector('a') ? el.querySelector('a').href : '';
        if (text.length > 20) r.push({href, text});
    });
    return r;
}"""

GOVAUCTIONS_JS = """() => {
    const r = [];
    document.querySelectorAll('a.card-surface, a.group').forEach(a => {
        const text = (a.innerText || '').substring(0, 600);
        const href = a.href || '';
        if (text.includes('$') && text.length > 20) r.push({href, text});
    });
    return r;
}"""

LANDZERO_JS = """() => {
    const r = [];
    document.querySelectorAll('.elementor-post, .e-loop-item, [class*="product"], article').forEach(el => {
        const text = (el.innerText || '').substring(0, 600);
        const link = el.querySelector('a');
        const href = link ? link.href : '';
        if (text.length > 20 && text.includes('$')) r.push({href, text});
    });
    return r;
}"""


def scrape_all(conn):
    from database import save_listing
    from discord import send_alert
    saved = 0
    saved += _cl(conn, save_listing, send_alert)
    saved += _landmodo(conn, save_listing, send_alert)
    saved += _govauctions(conn, save_listing, send_alert)
    return saved


def _cl(conn, save, alert):
    saved = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    for region in CRAIGSLIST_REGIONS:
        try:
            r = requests.get(f'https://{region}.craigslist.org/search{CL_LAND_PATH}', headers=headers, timeout=15)
            for row in BeautifulSoup(r.text, 'html.parser').find_all('li', class_='cl-static-search-result'):
                link = row.find('a', href=True)
                if not link: continue
                href = link['href'] if link['href'].startswith('http') else f'https://{region}.craigslist.org' + link['href']
                title = (row.find('div', class_='title') or type('', (), {'text': ''})()).text.strip()
                pt = (row.find('div', class_='price') or type('', (), {'text': ''})()).text.strip()
                pm = re.search(r'\$([\d,]+)', pt)
                price = float(pm.group(1).replace(',', '')) if pm else 0
                loc = (row.find('div', class_='location') or type('', (), {'text': region})()).text.strip()
                if should_skip(title): continue
                sc = score_listing(title, '', price)
                if save(conn, 'craigslist', href, title, price, href, loc, '', sc):
                    saved += 1
                    if sc >= 40: alert(title, price, href, loc, sc, 'craigslist')
        except: pass
    return saved


def _pw_scrape(conn, save, alert, name, url, js):
    """Generic Playwright scraper with custom JS selector."""
    saved = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        Stealth().apply_stealth_sync(ctx)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(5)
            for _ in range(5):
                page.evaluate('window.scrollBy(0, 1000)')
                time.sleep(0.5)
            data = page.evaluate(js)
        except:
            browser.close()
            return 0
        for item in data:
            href, text = item.get('href', ''), item.get('text', '')
            pm = re.search(r'\$([\d,]+)', text)
            if not pm: continue
            price = float(pm.group(1).replace(',', ''))
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            title = next((l for l in lines if len(l) > 10 and '$' not in l and 'Posted' not in l), lines[0] if lines else 'Land listing')
            if should_skip(title, text): continue
            sc = score_listing(title, text, price)
            if save(conn, name, href, title, price, href, '', text[:500], sc):
                saved += 1
                if sc >= 40: alert(title, price, href, '', sc, name)
        browser.close()
    print(f'  {name}: +{saved}')
    return saved


def _landmodo(conn, save, alert):
    return _pw_scrape(conn, save, alert, 'landmodo',
        'https://www.landmodo.com/arizona-land-for-sale/cheap-land', LANDMODO_JS)


def _govauctions(conn, save, alert):
    return _pw_scrape(conn, save, alert, 'govauctions',
        'https://govauctions.app/auctions/real-estate/arizona', GOVAUCTIONS_JS)
