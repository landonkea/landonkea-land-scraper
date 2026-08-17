"""scraper.py - Scraping logic for land listings."""

import re, time, requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from filters import should_skip, score_listing
from config import CRAIGSLIST_REGIONS, PLAYWRIGHT_SITES, CL_LAND_PATH

GENERIC_JS = """() => {
    const r = [], s = new Set();
    document.querySelectorAll('a').forEach(l => {
        if (!l.href.includes('DOMAIN') || s.has(l.href)) return;
        s.add(l.href);
        const c = l.closest('li') || l.closest('article') || l.closest('div') || l;
        const t = (c.innerText || '').substring(0, 500);
        if (t.length > 20) r.push({href: l.href, text: t});
    });
    return r;
}"""


def scrape_all(conn):
    from database import save_listing
    from discord import send_alert
    saved = 0
    saved += _cl(conn, save_listing, send_alert)
    saved += _pw_sites(conn, save_listing, send_alert)
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


def _pw_sites(conn, save, alert):
    saved = 0
    for site in PLAYWRIGHT_SITES:
        try: saved += _pw_one(conn, site, save, alert)
        except Exception as e: print(f'  {site["name"]}: {e}')
    return saved


def _pw_one(conn, site, save, alert):
    saved = 0
    name, domain, url = site['name'], site['domain'], site['url']
    js = GENERIC_JS.replace('DOMAIN', domain)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        Stealth().apply_stealth_sync(ctx)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=15000)
            time.sleep(3)
            for _ in range(5):
                page.evaluate('window.scrollBy(0, 1000)')
                time.sleep(0.3)
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
            title = next((l for l in lines if len(l) > 10 and '$' not in l), lines[0] if lines else 'Land listing')
            if should_skip(title, text): continue
            sc = score_listing(title, text, price)
            if save(conn, name, href, title, price, href, '', text[:500], sc):
                saved += 1
                if sc >= 40: alert(title, price, href, '', sc, name)
        browser.close()
    print(f'  {name}: +{saved}')
    return saved
