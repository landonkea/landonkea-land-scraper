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
    saved += _maricopa(conn, save_listing, send_alert)
    saved += _adot(conn, save_listing, send_alert)
    saved += _cochise(conn, save_listing, send_alert)
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


def _maricopa(conn, save, alert):
    """Scrape Maricopa County excess land listings."""
    saved = 0
    url = 'https://www.maricopa.gov/5325/Available-for-Sale'
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        Stealth().apply_stealth_sync(ctx)
        page = ctx.new_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
            time.sleep(5)
            for _ in range(10):
                page.evaluate('window.scrollBy(0, 800)')
                time.sleep(0.3)
            text = page.evaluate('() => document.body.innerText')
        except:
            browser.close()
            return 0
        browser.close()

    # Parse listings from page text
    # Each listing has: Assessor's Parcel Number, Location, Size, Minimum Bid
    parcels = re.split(r'Assessor\'s Parcel Number:', text)
    for chunk in parcels[1:]:  # Skip first chunk (header)
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        if len(lines) < 3:
            continue

        parcel = lines[0].strip()
        location = ''
        size = ''
        min_bid = ''

        for i, line in enumerate(lines):
            if line.startswith('Location:'):
                location = lines[i+1] if i+1 < len(lines) else ''
            elif line.startswith('Size:'):
                size = lines[i+1] if i+1 < len(lines) else ''
            elif 'Minimum Bid:' in line:
                min_bid = lines[i+1] if i+1 < len(lines) else ''

        # Extract price from min_bid
        price = 0
        if min_bid:
            pm = re.search(r'\$([\d,]+)', min_bid)
            if pm:
                price = float(pm.group(1).replace(',', ''))

        title = f'Maricopa County excess land - {size} - {location}'
        href = url

        if should_skip(title):
            continue

        sc = score_listing(title, f'{size} {location} {min_bid}', price)
        if save(conn, 'maricopa_county', parcel, title, price, href, location, f'Size: {size}. Min bid: {min_bid}', sc):
            saved += 1
            if sc >= 40:
                alert(title, price, href, location, sc, 'maricopa_county')

    print(f'  maricopa_county: +{saved}')
    return saved


def _adot(conn, save, alert):
    """Scrape ADOT (AZ Dept of Transportation) vacant land listings."""
    saved = 0
    url = 'https://azdot.gov/business/right-way-properties/vacant-land-and-commercial-properties-sale'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(r.text, 'html.parser')
        text = soup.get_text('\n')
    except:
        return 0

    # Split by "Excess Land No." on its own line
    parcels = re.split(r'\nExcess Land No\.\n', text)
    for chunk in parcels[1:]:
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]
        if len(lines) < 3:
            continue

        land_id = lines[0].strip()
        location = ''
        size = ''
        min_bid = ''
        status = ''

        for i, line in enumerate(lines):
            if line == 'Location' and i+1 < len(lines):
                location = lines[i+1]
            elif re.search(r'\d[\d,]*\s*sq\s*ft', line):
                size = line
            elif line.startswith('Zoning:'):
                pass  # skip
            elif 'Minimum Bid:' in line:
                pm = re.search(r'\$([\d,]+)', line)
                if pm:
                    min_bid = pm.group(0)
                    price = float(pm.group(1).replace(',', ''))
            elif line in ('IN ESCROW', 'OFFER TENDERED', 'PRICE REDUCED'):
                status = line

        if not min_bid:
            continue

        title = f'ADOT excess land {land_id} - {size} - {location}'
        if status:
            title += f' [{status}]'

        if should_skip(title):
            continue

        sc = score_listing(title, f'{size} {location} {min_bid}', price)
        if save(conn, 'adot', land_id, title, price, url, location, f'Size: {size}. Min bid: {min_bid}. {status}', sc):
            saved += 1
            if sc >= 40:
                alert(title, price, url, location, sc, 'adot')

    print(f'  adot: +{saved}')
    return saved


def _cochise(conn, save, alert):
    """Scrape Cochise County tax deed land sale from PDF."""
    saved = 0
    import io
    try:
        import pdfplumber
    except ImportError:
        print('  cochise_county: skipped (pdfplumber not installed)')
        return 0

    pdf_url = 'https://www.cochise.az.gov/DocumentCenter/View/26715/Spring-2026-Tax-Deed-Land-Sale-Parcel-Listing-PDF'
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    try:
        r = requests.get(pdf_url, headers=headers, timeout=30)
        if r.status_code != 200:
            print(f'  cochise_county: PDF fetch failed ({r.status_code})')
            return 0
    except:
        return 0

    try:
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or not row[1]:
                            continue
                        # Columns: Row#, Unit ID, Zoning, Acreage, Legal Desc, Owner, FCV, Taxes, Min Bid
                        unit_id = str(row[1]).strip()
                        if not re.match(r'\d{6,8}', unit_id):
                            continue
                        zoning = str(row[2] or '').strip()
                        try:
                            acreage = float(row[3])
                        except:
                            continue
                        legal_desc = str(row[4] or '').strip()
                        owner = str(row[5] or '').strip()
                        fcv_str = str(row[6] or '').replace('$', '').replace(',', '').replace(' ', '').strip()
                        min_bid_str = str(row[8] or '').replace('$', '').replace(',', '').replace(' ', '').strip()

                        try:
                            fcv = float(fcv_str)
                        except:
                            fcv = 0
                        try:
                            price = float(min_bid_str) if min_bid_str else fcv
                        except:
                            price = fcv

                        if price <= 0:
                            continue

                        # Extract location from legal description
                        loc_match = re.match(r'(.+?)(?:LOT|BLOCK|BLK|TR)', legal_desc, re.I)
                        location = loc_match.group(1).strip().rstrip(',') if loc_match else legal_desc[:60]

                        title = f'Cochise County tax deed - {acreage} acres - {location}'
                        if should_skip(title):
                            continue

                        sc = score_listing(title, f'{acreage} acres {zoning} {location}', price)
                        if save(conn, 'cochise_county', unit_id, title, price, 'https://www.cochise.az.gov/811/2026-Tax-Deed-Land-Sale', location, f'Zoning: {zoning}. {acreage}ac. Min bid: ${price:,.0f}', sc):
                            saved += 1
                            if sc >= 40:
                                alert(title, price, 'https://www.cochise.az.gov/811/2026-Tax-Deed-Land-Sale', location, sc, 'cochise_county')
    except:
        return 0

    print(f'  cochise_county: +{saved}')
    return saved

    print(f'  cochise_county: +{saved}')
    return saved
