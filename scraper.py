"""scraper.py - Scraping logic for land listings."""  # This module handles pulling land listings from various county and public websites.

import re, time, requests, io  # re handles regex patterns for price parsing; time adds delays between page loads; requests fetches raw HTML; io handles in-memory file streams for PDFs.
import pdfplumber  # pdfplumber extracts text from PDF files like county tax sale lists.
from bs4 import BeautifulSoup  # BeautifulSoup parses HTML into a tree we can search for specific tags and classes.
from playwright.sync_api import sync_playwright  # Playwright launches a real browser to scrape JavaScript-heavy sites that requests can't handle.
from playwright_stealth import Stealth  # Stealth patches Playwright so it doesn't look like a bot to sites that block headless browsers.
from filters import should_skip, score_listing  # should_skip filters out junk listings; score_listing rates how promising each parcel is.
from config import CRAIGSLIST_REGIONS, CL_LAND_PATH  # CRAIGSLIST_REGIONS is a list of Craigslist subdomains to hit; CL_LAND_PATH is the URL path for the land category.

LANDMODO_JS = """() => {  // This entire JavaScript block runs inside the browser to extract listing data from Landmodo's search results page.
    const r = [];  // r is the results array that will hold every listing we find on the page.
    document.querySelectorAll('.search_result').forEach(el => {  // This loops through every DOM element with the search_result class.
        const text = (el.innerText || '').substring(0, 600);  // Pulls the visible text from the listing card and cuts it to 600 chars to keep data small.
        const link = el.querySelector('a[href*="/properties/"]');  // Looks for a link pointing to a specific property page, which has /properties/ in the URL.
        const href = link ? link.href : el.querySelector('a') ? el.querySelector('a').href : '';  // Falls back to any link if no property link exists, or empty string if nothing is there.
        if (text.length > 20) r.push({href, text});  // Only keeps listings with real content, skipping empty or near-empty cards.
    });
    return r;  // Sends the array of {href, text} objects back to Python so it can process them.
}"""  # End of the Landmodo JavaScript function.

GOVAUCTIONS_JS = """() => {  // This JavaScript extracts auction listings from GoV Auctions using two different card selector patterns.
    const r = [];  // Results array, same pattern as the other scrapers.
    document.querySelectorAll('a.card-surface, a.group').forEach(a => {  // GoV Auctions uses either a.card-surface or a.group as the clickable card wrapper.
        const text = (a.innerText || '').substring(0, 600);  // Gets the text inside the card and caps it at 600 characters.
        const href = a.href || '';  // The href is directly on the card anchor element itself.
        if (text.includes('$') && text.length > 20) r.push({href, text});  // Only keeps cards that show a dollar amount and have real text, filtering out empty placeholders.
    });
    return r;  // Returns the filtered listing data to Python.
}"""  # End of the GoV Auctions JavaScript function.

LANDZERO_JS = """() => {  // This JavaScript scrapes Land Zero, which uses Elementor and WordPress, so the selectors target those specific class names.
    const r = [];  // Results array for Land Zero listings.
    document.querySelectorAll('.elementor-post, .e-loop-item, [class*="product"], article').forEach(el => {  // Catches Elementor posts, loop items, anything with product in the class, and generic article tags.
        const text = (el.innerText || '').substring(0, 600);  // Extracts visible text from the listing element.
        const link = el.querySelector('a');  // Finds the first anchor tag inside the listing, which should be the property link.
        const href = link ? link.href : '';  // Uses the link href or falls back to empty string.
        if (text.length > 20 && text.includes('$')) r.push({href, text});  // Keeps listings that have a price and enough text to be a real listing.
    });
    return r;  // Sends the data back to Python.
}"""  # End of the Land Zero JavaScript function.


def scrape_all(conn):  # This is the main entry point that runs every scraper and returns the total number of new listings saved.
    from database import save_listing  # save_listing writes a new listing to the SQLite database if it hasn't been seen before.
    from discord import send_alert  # send_alert posts a Discord notification when a high-scoring listing is found.
    saved = 0  # Counter tracks how many new listings were saved across all scrapers.
    alerts = []  # Collect all alerts first so we can sort them before sending.

    def collect_alert(title, price, url, location, score, source):
        # Instead of sending immediately, stash the alert for later sorting.
        alerts.append((price, title, url, location, score, source))

    saved += _cl(conn, save_listing, collect_alert)  # Craigslist scraper runs first since it's the fastest (just HTTP requests, no browser).
    saved += _landmodo(conn, save_listing, collect_alert)  # Landmodo uses Playwright to load JavaScript-rendered content.
    saved += _govauctions(conn, save_listing, collect_alert)  # GoV Auctions also needs Playwright for its dynamic page.
    saved += _landzero(conn, save_listing, collect_alert)  # Land Zero uses Elementor/WordPress, needs Playwright to render.
    saved += _maricopa(conn, save_listing, collect_alert)  # Maricopa County has their own site that loads listings dynamically.
    saved += _adot(conn, save_listing, collect_alert)  # ADOT posts a static page with their land parcels, simple requests call.
    saved += _cochise(conn, save_listing, collect_alert)  # Cochise County publishes a PDF that we have to parse.
    saved += _mohave(conn, save_listing, collect_alert)  # Mohave County also uses a PDF, but with a different table layout.
    saved += _yavapai(conn, save_listing, collect_alert)  # Yavapai County publishes an over-the-counter tax deed PDF.

    # Sort alerts cheapest first, then send them to Discord.
    alerts.sort(key=lambda a: a[0])  # Sort by price ascending.
    for price, title, url, location, score, source in alerts:
        send_alert(title, price, url, location, score, source)  # Now send each alert in order.

    return saved  # Total count goes back to the caller so it can log or display it.


def _cl(conn, save, alert):  # Craigslist scraper. Uses plain requests because Craigslist doesn't require JavaScript.
    saved = 0  # Running count of new listings saved from Craigslist.
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}  # Sets a fake browser User-Agent so Craigslist doesn't reject the request as a bot.
    for region in CRAIGSLIST_REGIONS:  # Loops through each Craigslist region (like "phoenix", "tucson", etc.).
        try:  # Wraps everything in try/except so one bad region doesn't crash the whole scraper.
            r = requests.get(f'https://{region}.craigslist.org/search{CL_LAND_PATH}', headers=headers, timeout=15)  # Fetches the land listings page for this region with a 15-second timeout.
            for row in BeautifulSoup(r.text, 'html.parser').find_all('li', class_='cl-static-search-result'):  # Parses the HTML and finds every listing item by its class name.
                link = row.find('a', href=True)  # Grabs the first anchor tag that has an href, which is the link to the actual listing.
                if not link: continue  # Skips the row entirely if there's no clickable link.
                href = link['href'] if link['href'].startswith('http') else f'https://{region}.craigslist.org' + link['href']  # Builds a full URL, prepending the region domain if the href is just a relative path.
                title = (row.find('div', class_='title') or type('', (), {'text': ''})()).text.strip()  # Extracts the listing title, using a dummy object if the div doesn't exist so we don't crash.
                pt = (row.find('div', class_='price') or type('', (), {'text': ''})()).text.strip()  # Extracts the price text the same safe way.
                pm = re.search(r'\$([\d,]+)', pt)  # Regex looks for a dollar sign followed by digits and commas, like "$12,500".
                price = float(pm.group(1).replace(',', '')) if pm else 0  # Converts the matched number to a float, stripping commas. Defaults to 0 if no price found.
                loc = (row.find('div', class_='location') or type('', (), {'text': region})()).text.strip()  # Gets the location text, falling back to the region name if nothing is shown.
                if should_skip(title): continue  # Filters out titles that match exclusion keywords like "wanted" or "services".
                sc = score_listing(title, '', price)  # Rates the listing from 0-100 based on title keywords and price. Empty string for body because Craigslist doesn't show it in search results.
                if save(conn, 'craigslist', href, title, price, href, loc, '', sc):  # Saves to database, returns True if it's a new listing we haven't seen before.
                    saved += 1  # Counts the newly saved listing.
                    if sc >= 40: alert(title, price, href, loc, sc, 'craigslist')  # Sends a Discord alert only if the listing scores 40 or above, which means it looks promising.
        except: pass  # Swallows any exception silently so the scraper keeps running even if one region fails.
    return saved  # Returns the total new listings saved across all Craigslist regions.


def _pw_scrape(conn, save, alert, name, url, js):  # Generic Playwright scraper that takes a name, URL, and custom JavaScript to run in the browser.
    """Generic Playwright scraper with custom JS selector."""  # Docstring explains this is a reusable function for any site that needs browser-based scraping.
    saved = 0  # Counter for new listings saved by this scraper.
    with sync_playwright() as p:  # Opens a Playwright context that manages the browser lifecycle and cleans up when done.
        browser = p.chromium.launch(headless=True)  # Starts a Chromium browser in headless mode so there's no visible window popping up.
        ctx = browser.new_context()  # Creates a fresh browser context, which is like an isolated session with its own cookies and settings.
        Stealth().apply_stealth_sync(ctx)  # Patches the context to avoid bot detection, like making navigator.webdriver return false.
        page = ctx.new_page()  # Opens a new tab in the browser context.
        try:  # Try block so we can close the browser gracefully if anything goes wrong.
            page.goto(url, wait_until='domcontentloaded', timeout=20000)  # Navigates to the target URL and waits for the HTML to be parsed, with a 20-second timeout.
            time.sleep(5)  # Waits 5 seconds after page load to let any lazy-loaded content or ads finish rendering.
            for _ in range(5):  # Scrolls down 5 times to trigger infinite scroll or lazy loading on the page.
                page.evaluate('window.scrollBy(0, 1000)')  # Runs JavaScript in the browser to scroll the window down by 1000 pixels.
                time.sleep(0.5)  # Brief pause between scrolls so the page has time to load new content.
            data = page.evaluate(js)  # Runs the custom JavaScript function (passed in as the js parameter) and captures its return value.
        except:  # Catches any error from the navigation, scrolling, or JS evaluation.
            browser.close()  # Closes the browser before returning so we don't leak memory.
            return 0  # Returns 0 listings saved when something goes wrong.
        for item in data:  # Iterates through the array of {href, text} objects that the JavaScript returned.
            href, text = item.get('href', ''), item.get('text', '')  # Unpacks the href and text from each item, defaulting to empty strings.
            pm = re.search(r'\$([\d,]+)', text)  # Looks for a dollar amount in the listing text using the same price regex pattern.
            if not pm: continue  # Skips listings that don't show a price, since we can't evaluate them.
            price = float(pm.group(1).replace(',', ''))  # Converts the matched price string to a float number.
            lines = [l.strip() for l in text.split('\n') if l.strip()]  # Splits the text into non-empty lines, stripping whitespace from each.
            title = next((l for l in lines if len(l) > 10 and '$' not in l and 'Posted' not in l), lines[0] if lines else 'Land listing')  # Picks the first decent-looking line as the title, skipping price-only lines and posted dates.
            if should_skip(title, text): continue  # Filters out listings that match exclusion rules, checking both title and full text this time.
            sc = score_listing(title, text, price)  # Scores the listing with the full text available, which gives better results than Craigslist.
            if save(conn, name, href, title, price, href, '', text[:500], sc):  # Saves to database, truncating the body text to 500 characters to keep storage reasonable.
                saved += 1  # Counts the new listing.
                if sc >= 40: alert(title, price, href, '', sc, name)  # Sends a Discord alert if the listing is promising enough.
        browser.close()  # Closes the browser after processing all items, freeing system resources.
    print(f'  {name}: +{saved}')  # Prints how many new listings were found from this source, with the source name.
    return saved  # Returns the count for the caller to add to its running total.


def _landmodo(conn, save, alert):  # Landmodo scraper, a thin wrapper that calls the generic Playwright scraper with Landmodo-specific settings.
    return _pw_scrape(conn, save, alert, 'landmodo',  # Passes 'landmodo' as the source name for the database.
        'https://www.landmodo.com/arizona-land-for-sale/cheap-land', LANDMODO_JS)  # Points to the cheap Arizona land page and uses the Landmodo JavaScript selector we defined earlier.


def _govauctions(conn, save, alert):  # GoV Auctions scraper, another thin wrapper around the generic Playwright function.
    return _pw_scrape(conn, save, alert, 'govauctions',  # Passes 'govauctions' as the source name.
        'https://govauctions.app/auctions/real-estate/arizona', GOVAUCTIONS_JS)  # Targets the Arizona real estate auctions page and uses the GoV Auctions JavaScript.


def _landzero(conn, save, alert):  # Land Zero scraper, uses Playwright to load their Elementor/WordPress site.
    return _pw_scrape(conn, save, alert, 'landzero',  # Passes 'landzero' as the source name.
        'https://landzero.com/cheap-land/arizona/', LANDZERO_JS)  # Points to the Arizona cheap land page and uses the Land Zero JavaScript selector.


def _maricopa(conn, save, alert):  # Maricopa County scraper, handles their specific site layout where parcels are labeled with "Assessor's Parcel Number:".
    """Scrape Maricopa County excess land listings."""  # Docstring tells you this targets Maricopa County specifically.
    saved = 0  # Counter for new listings saved from Maricopa.
    url = 'https://www.maricopa.gov/5325/Available-for-Sale'  # The direct URL to Maricopa County's land-for-sale page.
    with sync_playwright() as p:  # Opens the Playwright browser context.
        browser = p.chromium.launch(headless=True)  # Headless Chromium so nothing pops up on screen.
        ctx = browser.new_context()  # Isolated browser context.
        Stealth().apply_stealth_sync(ctx)  # Applies anti-bot-detection patches.
        page = ctx.new_page()  # Opens a fresh tab.
        try:  # Try block for error handling during page load and scrolling.
            page.goto(url, wait_until='domcontentloaded', timeout=20000)  # Loads the Maricopa page and waits for the HTML structure to be ready.
            time.sleep(5)  # Lets any JavaScript finish running after the initial load.
            for _ in range(10):  # Scrolls 10 times, more than other scrapers because this page is longer.
                page.evaluate('window.scrollBy(0, 800)')  # Scrolls down 800 pixels each time.
                time.sleep(0.3)  # Short pause between scrolls, faster than other scrapers because this page is simpler.
            text = page.evaluate('() => document.body.innerText')  # Grabs all visible text from the page body as a single string.
        except:  # Catches navigation or scrolling errors.
            browser.close()  # Cleans up the browser.
            return 0  # Returns zero if we couldn't load the page.
        browser.close()  # Closes the browser once we have the text we need.

    # Parse listings from page text  # Everything below processes the raw page text into structured listing data.
    # Each listing has: Assessor's Parcel Number, Location, Size, Minimum Bid  # Describes the fields we expect to find in each listing block.
    parcels = re.split(r'Assessor\'s Parcel Number:', text)  # Splits the entire page text at each "Assessor's Parcel Number:" marker, giving us one chunk per listing.
    for chunk in parcels[1:]:  # Skips the first chunk because it's everything before the first parcel, usually just the page header.
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]  # Splits each parcel chunk into non-empty lines.
        if len(lines) < 3:  # A valid listing needs at least a few lines of data.
            continue  # Skips chunks that are too short to be real listings.

        parcel = lines[0].strip()  # The first line after the split is the parcel number itself.
        location = ''  # Will hold the property location once we find it.
        size = ''  # Will hold the parcel size in acres or square feet.
        min_bid = ''  # Will hold the minimum bid amount as a string.

        for i, line in enumerate(lines):  # Loops through every line with its index so we can look at the next line too.
            if line.startswith('Location:'):  # When we find the Location label...
                location = lines[i+1] if i+1 < len(lines) else ''  # ...the actual location is on the next line.
            elif line.startswith('Size:'):  # When we find the Size label...
                size = lines[i+1] if i+1 < len(lines) else ''  # ...the size value is on the next line.
            elif 'Minimum Bid:' in line:  # When we find the Minimum Bid label somewhere in a line...
                min_bid = lines[i+1] if i+1 < len(lines) else ''  # ...the bid amount is on the next line.

        # Extract price from min_bid  # Now we need to pull a number out of the minimum bid string.
        price = 0  # Default price of zero in case parsing fails.
        if min_bid:  # Only tries to parse if we actually found a minimum bid value.
            pm = re.search(r'\$([\d,]+)', min_bid)  # Looks for $12,345 style amounts in the bid text.
            if pm:  # If the regex matched something...
                price = float(pm.group(1).replace(',', ''))  # ...converts it to a float for database storage.

        title = f'Maricopa County excess land - {size} - {location}'  # Builds a human-readable title that combines the county name, size, and location.
        href = url  # Uses the main URL as the link since each parcel doesn't have its own dedicated page.

        if should_skip(title):  # Checks if this listing matches any exclusion keywords.
            continue  # Moves on to the next parcel if it does.

        sc = score_listing(title, f'{size} {location} {min_bid}', price)  # Scores the listing using all the text data we extracted.
        if save(conn, 'maricopa_county', parcel, title, price, href, location, f'Size: {size}. Min bid: {min_bid}', sc):  # Saves to database with the parcel number as the unique ID.
            saved += 1  # Counts the new listing.
            if sc >= 40:  # Only alerts on listings that look good enough to act on.
                alert(title, price, href, location, sc, 'maricopa_county')  # Sends the Discord notification.

    print(f'  maricopa_county: +{saved}')  # Reports how many new Maricopa listings were found.
    return saved  # Returns the count for the running total.


def _adot(conn, save, alert):  # ADOT scraper for Arizona Department of Transportation vacant land. Their site is simpler so we can use requests instead of Playwright.
    """Scrape ADOT (AZ Dept of Transportation) vacant land listings."""  # Docstring identifies this as the ADOT-specific scraper.
    saved = 0  # Counter for new ADOT listings saved.
    url = 'https://azdot.gov/business/right-way-properties/vacant-land-and-commercial-properties-sale'  # The page where ADOT lists their available land parcels.
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}  # Fake browser user agent to avoid getting blocked.
    try:  # Wraps the HTTP request in a try block.
        r = requests.get(url, headers=headers, timeout=20)  # Fetches the ADOT page with a 20-second timeout.
        soup = BeautifulSoup(r.text, 'html.parser')  # Parses the raw HTML into a searchable tree.
        text = soup.get_text('\n')  # Extracts all visible text from the page, joined by newlines to preserve structure.
    except:  # Catches network errors or timeouts.
        return 0  # Returns zero if we couldn't fetch the page.

    # Split by "Excess Land No." on its own line  # ADOT labels each parcel with "Excess Land No." on its own line, so we split on that pattern.
    parcels = re.split(r'\nExcess Land No\.\n', text)  # Splits the text at each "Excess Land No." marker to isolate individual parcels.
    for chunk in parcels[1:]:  # Skips the first chunk, which is everything before the first parcel listing.
        lines = [l.strip() for l in chunk.split('\n') if l.strip()]  # Breaks the chunk into clean non-empty lines.
        if len(lines) < 3:  # Needs at least a few lines to be a valid listing.
            continue  # Skips incomplete chunks.

        land_id = lines[0].strip()  # First line after the split is the land ID number.
        location = ''  # Property location, filled in later.
        size = ''  # Parcel size, usually in square feet.
        min_bid = ''  # Minimum bid amount as a string.
        status = ''  # Status like "IN ESCROW" or "PRICE REDUCED".

        for i, line in enumerate(lines):  # Loops through lines with index to peek at the next one when needed.
            if line == 'Location' and i+1 < len(lines):  # When we hit the "Location" label on its own line...
                location = lines[i+1]  # ...the address is on the next line.
            elif re.search(r'\d[\d,]*\s*sq\s*ft', line):  # Matches patterns like "12,500 sq ft" or "1250 sq ft" to identify the size line.
                size = line  # The whole line is the size description.
            elif line.startswith('Zoning:'):  # ADOT includes zoning info but we don't need it for scoring.
                pass  # Skips the zoning line entirely.
            elif 'Minimum Bid:' in line:  # When we find the bid amount embedded in a line...
                pm = re.search(r'\$([\d,]+)', line)  # ...pulls out the dollar amount.
                if pm:  # If the regex found a price...
                    min_bid = pm.group(0)  # Stores the full matched string like "$5,000".
                    price = float(pm.group(1).replace(',', ''))  # Also converts it to a float for the database.
            elif line in ('IN ESCROW', 'OFFER TENDERED', 'PRICE REDUCED'):  # These three status values are worth tracking.
                status = line  # Stores the status so we can append it to the title.

        if not min_bid:  # If we never found a minimum bid...
            continue  # ...this listing is incomplete or already sold, so skip it.

        title = f'ADOT excess land {land_id} - {size} - {location}'  # Builds a descriptive title from the parsed fields.
        if status:  # If there's a status like "IN ESCROW"...
            title += f' [{status}]'  # ...appends it in brackets so we know the deal status at a glance.

        if should_skip(title):  # Checks the title against exclusion rules.
            continue  # Skips it if it matches any filters.

        sc = score_listing(title, f'{size} {location} {min_bid}', price)  # Scores the listing using all extracted text.
        if save(conn, 'adot', land_id, title, price, url, location, f'Size: {size}. Min bid: {min_bid}. {status}', sc):  # Saves to database using the land ID as the unique key.
            saved += 1  # Counts the new listing.
            if sc >= 40:  # Only alerts on the good ones.
                alert(title, price, url, location, sc, 'adot')  # Sends the Discord notification.

    print(f'  adot: +{saved}')  # Reports how many new ADOT parcels were found.
    return saved  # Returns the count for the total.


def _cochise(conn, save, alert):  # Cochise County scraper. Their listings come as a PDF, so we need pdfplumber to extract tables.
    """Scrape Cochise County tax deed land sale from PDF."""  # Docstring makes it clear this one deals with PDF data.
    saved = 0  # Counter for new Cochise listings saved.
    import io  # io.BytesIO lets us treat raw PDF bytes as a file-like object without writing to disk.
    try:  # Tries to import pdfplumber in case it's not installed.
        import pdfplumber  # pdfplumber reads tables out of PDFs, which is exactly what Cochise County publishes.
    except ImportError:  # If pdfplumber isn't installed...
        print('  cochise_county: skipped (pdfplumber not installed)')  # ...tells the user why we're skipping this source.
        return 0  # Returns zero so the rest of the scraper keeps running.

    pdf_url = 'https://www.cochise.az.gov/DocumentCenter/View/26715/Spring-2026-Tax-Deed-Land-Sale-Parcel-Listing-PDF'  # Direct link to the current tax deed sale PDF on Cochise County's site.
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}  # Fake browser user agent for the PDF download.
    try:  # Wraps the PDF download in error handling.
        r = requests.get(pdf_url, headers=headers, timeout=30)  # Downloads the PDF with a longer 30-second timeout since it can be a large file.
        if r.status_code != 200:  # Checks if the download actually succeeded.
            print(f'  cochise_county: PDF fetch failed ({r.status_code})')  # Reports the HTTP error code if something went wrong.
            return 0  # Can't parse what we didn't download.
    except:  # Catches network errors or timeouts.
        return 0  # Returns zero on failure.

    try:  # Wraps the PDF parsing in error handling.
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:  # Opens the PDF from memory without saving it to a file, using a context manager for cleanup.
            for page in pdf.pages:  # Loops through every page of the PDF.
                tables = page.extract_tables()  # Extracts all tables from the current page as lists of rows.
                for table in tables:  # Loops through each table on the page.
                    for row in table:  # Loops through each row in the table.
                        if not row or not row[1]:  # Skips empty rows or rows missing the unit ID column.
                            continue  # Moves to the next row.
                        # Columns: Row#, Unit ID, Zoning, Acreage, Legal Desc, Owner, FCV, Taxes, Min Bid  # Documents the column layout so you know which index is which field.
                        unit_id = str(row[1]).strip()  # Grabs the unit ID from column 1 and converts it to a clean string.
                        if not re.match(r'\d{6,8}', unit_id):  # Unit IDs are 6 to 8 digits long, so anything else is a header or garbage.
                            continue  # Skips non-parcel rows.
                        zoning = str(row[2] or '').strip()  # Column 2 is zoning info, used for scoring.
                        try:  # Tries to convert acreage to a number.
                            acreage = float(row[3])  # Column 3 is the acreage, stored as a float for calculations.
                        except:  # If the conversion fails...
                            continue  # ...the row is probably corrupted, so skip it.
                        legal_desc = str(row[4] or '').strip()  # Column 4 is the legal description, which contains location info we'll extract later.
                        owner = str(row[5] or '').strip()  # Column 5 is the current owner name.
                        fcv_str = str(row[6] or '').replace('$', '').replace(',', '').replace(' ', '').strip()  # Column 6 is the full cash value, cleaned of formatting characters.
                        min_bid_str = str(row[8] or '').replace('$', '').replace(',', '').replace(' ', '').strip()  # Column 8 is the minimum bid, cleaned the same way.

                        try:  # Tries to convert the full cash value to a number.
                            fcv = float(fcv_str)  # Full cash value is the county's assessed value for the property.
                        except:  # Falls back to zero if parsing fails.
                            fcv = 0
                        try:  # Tries to convert the minimum bid to a number.
                            price = float(min_bid_str) if min_bid_str else fcv  # Uses the min bid if available, otherwise falls back to the full cash value.
                        except:  # Falls back to the full cash value if the min bid string is garbled.
                            price = fcv

                        if price <= 0:  # Listings with no price aren't useful for buying.
                            continue  # Skips free or zero-price parcels.

                        # Extract location from legal description  # Legal descriptions follow a pattern like "APN 123-45-678, LOT 1, BLOCK 2..."
                        loc_match = re.match(r'(.+?)(?:LOT|BLOCK|BLK|TR)', legal_desc, re.I)  # Captures everything up to LOT/BLOCK/BLK/TR, which marks the start of the subdivision details.
                        location = loc_match.group(1).strip().rstrip(',') if loc_match else legal_desc[:60]  # Uses the matched location or falls back to the first 60 chars of the legal description.

                        title = f'Cochise County tax deed - {acreage} acres - {location}'  # Builds a title with the county, acreage, and location.
                        if should_skip(title):  # Checks the title against exclusion rules.
                            continue  # Skips it if it matches.

                        sc = score_listing(title, f'{acreage} acres {zoning} {location}', price)  # Scores the listing with all available info.
                        if save(conn, 'cochise_county', unit_id, title, price, 'https://www.cochise.az.gov/811/2026-Tax-Deed-Land-Sale', location, f'Zoning: {zoning}. {acreage}ac. Min bid: ${price:,.0f}', sc):  # Saves with the unit ID as the unique key and links to the county's sale page.
                            saved += 1  # Counts the new listing.
                            if sc >= 40:  # Only alerts on the promising ones.
                                alert(title, price, 'https://www.cochise.az.gov/811/2026-Tax-Deed-Land-Sale', location, sc, 'cochise_county')  # Sends the Discord notification.
    except:  # Catches any error during PDF parsing.
        return 0  # Returns zero so the rest of the scraper doesn't crash.

    print(f'  cochise_county: +{saved}')  # Reports how many new Cochise listings were found.
    return saved  # Returns the count for the total.


def _mohave(conn, save, alert):  # Mohave County scraper, also PDF-based but with a different table layout than Cochise.
    """Scrape Mohave County OTC tax deed parcels from PDF."""  # Docstring says this is for Mohave's over-the-counter tax deed parcels.
    saved = 0  # Counter for new Mohave listings saved.
    import io  # Needed to wrap the PDF bytes in a file-like object.
    try:  # Tries to import pdfplumber.
        import pdfplumber  # The library that reads PDF tables.
    except ImportError:  # If it's not installed...
        print('  mohave_county: skipped (pdfplumber not installed)')  # ...explains why we're skipping this source.
        return 0  # Returns zero so other scrapers continue.

    pdf_url = 'https://www.mohave.gov/media/2yjev04g/otc_td_list-0625.pdf'  # Direct link to Mohave County's current tax deed PDF.
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}  # Fake browser user agent for the PDF request.
    try:  # Wraps the download in error handling.
        r = requests.get(pdf_url, headers=headers, timeout=30)  # Downloads the PDF with a 30-second timeout.
        if r.status_code != 200:  # Checks if the server responded successfully.
            print(f'  mohave_county: PDF fetch failed ({r.status_code})')  # Reports the HTTP error if the download failed.
            return 0  # Can't parse without the PDF.
    except:  # Catches network errors.
        return 0  # Returns zero on failure.

    try:  # Wraps the parsing logic in error handling.
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:  # Opens the PDF from the downloaded bytes.
            for page in pdf.pages:  # Loops through each page of the PDF.
                tables = page.extract_tables()  # Pulls out all tables from the current page.
                for table in tables:  # Loops through each table.
                    for row in table:  # Loops through each row in the table.
                        if not row or not row[1]:  # Skips empty rows or rows missing the parcel number.
                            continue  # Moves to the next row.
                        parcel = str(row[1]).strip()  # Grabs the parcel number from column 1.
                        if not re.match(r'\d{6,8}', parcel):  # Validates that it's a 6-8 digit number like a real parcel ID.
                            continue  # Skips headers or malformed rows.
                        owner = str(row[2] or '').strip()  # Column 2 is the property owner name.
                        desc = str(row[3] or '').strip()  # Column 3 is the property description.
                        location = str(row[4] or '').strip()  # Column 4 is the property location.
                        fcv_str = str(row[5] or '').replace('$', '').replace(',', '').replace(' ', '').strip()  # Column 5 is the full cash value, cleaned of formatting.
                        owed_str = str(row[6] or '').replace('$', '').replace(',', '').replace(' ', '').strip()  # Column 6 is the amount owed (taxes), also cleaned.
                        min_bid_str = str(row[7] or '').replace('$', '').replace(',', '').replace(' ', '').strip()  # Column 7 is the minimum bid amount.

                        try:  # Tries to convert full cash value to a float.
                            fcv = float(fcv_str)  # The county's assessed value.
                        except:  # Falls back to zero.
                            fcv = 0
                        try:  # Tries to convert the owed amount to a float.
                            owed = float(owed_str)  # Total taxes owed on the property.
                        except:  # Falls back to zero.
                            owed = 0
                        try:  # Tries to convert the minimum bid to a float.
                            price = float(min_bid_str) if min_bid_str else min(fcv, owed) if fcv and owed else fcv or owed  # Uses min bid if available; otherwise picks the lower of FCV and taxes owed; or whichever one is available.
                        except:  # Falls back to zero if everything fails.
                            price = 0

                        if price <= 0:  # Zero or negative prices aren't useful for buying.
                            continue  # Skips this listing.

                        title = f'Mohave County tax deed - {desc[:50]} - {location}'  # Builds a title, truncating the description to 50 characters to keep it readable.
                        if should_skip(title):  # Checks against exclusion filters.
                            continue  # Skips it if it matches.

                        sc = score_listing(title, f'{desc} {location} {owner}', price)  # Scores the listing using description, location, and owner name.
                        if save(conn, 'mohave_county', parcel, title, price, 'https://www.mohave.gov/departments/clerk-of-the-board/over-the-counter-tax-deed-sales/', location, f'Owner: {owner}. Desc: {desc}. Min bid: ${price:,.0f}', sc):  # Saves to database with the parcel number as the unique ID, linking to Mohave's OTC sales page.
                            saved += 1  # Counts the new listing.
                            if sc >= 40:  # Only alerts on the good ones.
                                alert(title, price, 'https://www.mohave.gov/departments/clerk-of-the-board/over-the-counter-tax-deed-sales/', location, sc, 'mohave_county')  # Sends the Discord notification.
    except:  # Catches any error during PDF parsing.
        return 0  # Returns zero so other scrapers keep running.

    print(f'  mohave_county: +{saved}')  # Reports how many new Mohave listings were found.
    return saved  # Returns the count for the running total.


def _yavapai(conn, save, alert):  # Yavapai County scraper, parses their over-the-counter tax deed PDF.
    """Scrape Yavapai County OTC tax deed parcels from PDF."""  # Docstring says this targets Yavapai County's available tax deed properties.
    saved = 0  # Counter for new Yavapai listings saved.
    pdf_url = 'https://www.yavapaiaz.gov/files/sharedassets/public/v/1/mapping-and-properties/parcelsforsaleundertaxdeedsale-04022025-2.pdf'  # Direct link to Yavapai County's over-the-counter tax deed list.
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}  # Fake browser user agent for the PDF request.
    try:  # Wraps the download in error handling.
        r = requests.get(pdf_url, headers=headers, timeout=30)  # Downloads the PDF with a 30-second timeout.
        if r.status_code != 200:  # Checks if the server responded successfully.
            print(f'  yavapai_county: PDF fetch failed ({r.status_code})')  # Reports the HTTP error if the download failed.
            return 0  # Can't parse without the PDF.
    except:  # Catches network errors.
        return 0  # Returns zero on failure.

    try:  # Wraps the parsing logic in error handling.
        with pdfplumber.open(io.BytesIO(r.content)) as pdf:  # Opens the PDF from the downloaded bytes.
            full_text = ''  # Accumulates text from all pages.
            for page in pdf.pages:  # Loops through each page of the PDF.
                text = page.extract_text()  # Extracts raw text from the current page.
                if text:  # Only adds non-empty pages.
                    full_text += text + '\n'  # Appends the page text with a newline separator.

        # Parse the PDF text into individual parcels.
        # The format is: "Former Owner - NAME\nParcel Number - XXX-XX-XXX\nPartial Description: ...\nRedemption Amount - $X,XXX"
        parcel_blocks = re.split(r'(?=Former Owner\s*[-–])', full_text)  # Splits the text at each "Former Owner" header to get individual parcels.

        for block in parcel_blocks:  # Loops through each parcel block.
            if not block.strip():  # Skips empty blocks.
                continue  # Moves to the next one.

            owner_match = re.search(r'Former Owner\s*[-–]\s*(.+)', block)  # Extracts the former owner name.
            parcel_match = re.search(r'Parcel Number\s*[-–]\s*(\S+)', block)  # Extracts the parcel number.
            desc_match = re.search(r'Partial Description:\s*(.+?)(?:\n|Redemption|Amount)', block, re.S)  # Extracts the property description.
            amount_match = re.search(r'(?:Redemption Amount|Amount)\s*[-–]\s*\$?([\d,]+\.?\d*)', block)  # Extracts the redemption/minimum bid amount.

            if not parcel_match:  # If we can't find a parcel number, skip this block.
                continue  # Can't identify the property without it.

            parcel = parcel_match.group(1).strip()  # Gets the parcel number string.
            owner = owner_match.group(1).strip() if owner_match else 'Unknown'  # Gets the owner name or defaults to Unknown.
            desc = desc_match.group(1).strip() if desc_match else ''  # Gets the property description or empty string.

            try:  # Tries to convert the redemption amount to a float.
                price = float(amount_match.group(1).replace(',', ''))  # Removes commas and converts to float.
            except:  # Falls back to zero if parsing fails.
                price = 0  # Can't determine the price.

            if price <= 0:  # Zero or negative prices aren't useful for buying.
                continue  # Skips this listing.

            title = f'Yavapai County tax deed - {desc[:50]}'  # Builds a title, truncating the description to 50 characters.
            if should_skip(title):  # Checks against exclusion filters.
                continue  # Skips it if it matches.

            url = 'https://www.yavapaiaz.gov/Mapping-and-Properties/Property-Taxes/Tax-Deed-Sales'  # Links to Yavapai County's tax deed sales page.
            sc = score_listing(title, f'{desc} {owner}', price)  # Scores the listing using description and owner name.
            if save(conn, 'yavapai_county', parcel, title, price, url, 'Yavapai County', f'Owner: {owner}. Desc: {desc}. Redemption: ${price:,.0f}', sc):  # Saves to database with the parcel number as the unique ID.
                saved += 1  # Counts the new listing.
                if sc >= 40:  # Only alerts on the good ones.
                    alert(title, price, url, 'Yavapai County', sc, 'yavapai_county')  # Sends the Discord notification.
    except:  # Catches any error during PDF parsing.
        return 0  # Returns zero so other scrapers keep running.

    print(f'  yavapai_county: +{saved}')  # Reports how many new Yavapai listings were found.
    return saved  # Returns the count for the running total.