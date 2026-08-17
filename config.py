"""
config.py - All settings in one place.
Land scraper for Arizona (south of Flagstaff, north of Tucson).
"""

import pathlib
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = pathlib.Path(__file__).parent
DB_PATH = str(ROOT_DIR / 'data' / 'lands.db')
DISCORD_WEBHOOK = __import__('os').environ.get('DISCORD_WEBHOOK_URL_LAND')

# Price range (no max - we want cheapest first, sorted by price)
MIN_PRICE = 0
MAX_PRICE = 999999

# Minimum score to send to Discord (0-100)
MIN_SCORE = 40

# Craigslist regions in our area
CRAIGSLIST_REGIONS = [
    'phoenix',    # Phoenix metro, south of Flagstaff
    'prescott',   # Prescott area
    'flagstaff',  # Northern edge (Flagstaff itself is borderline)
]

# Playwright sites to scrape
PLAYWRIGHT_SITES = [
    {'name': 'zillow', 'domain': 'zillow.com', 'url': 'https://www.zillow.com/phoenix-az/land/?searchQueryState=%7B%22pagination%22%3A%7B%7D%2C%22isMapVisible%22%3Afalse%2C%22filterState%22%3A%7B%22sort%22%3A%7B%22value%22%3A%22pricea%22%7D%2C%22ah%22%3A%7B%22value%22%3Atrue%7D%2C%22land%22%3A%7B%22value%22%3Atrue%7D%7D%7D'},
    {'name': 'realtor', 'domain': 'realtor.com', 'url': 'https://www.realtor.com/realestateandhomes-search/Phoenix_AZ/land'},
    {'name': 'landwatch', 'domain': 'landwatch.com', 'url': 'https://www.landwatch.com/arizona-land-for-sale'},
    {'name': 'landandfarm', 'domain': 'landandfarm.com', 'url': 'https://www.landandfarm.com/Arizona-land-for-sale'},
    {'name': 'crexi', 'domain': 'crexi.com', 'url': 'https://www.crexi.com/properties?type=land&sort=price_asc&state=Arizona'},
]

# Craigslist search paths for land
CL_LAND_PATH = '/rea'  # real estate for sale (appended to /search)

# Geographic bounds (south of Flagstaff, north of Scottsdale/Cave Creek)
# Latitude: Flagstaff ~35.2, Scottsdale ~33.5
# Sweet spot: Prescott/Sedona area ~34.2-34.8
GEO_BOUNDS = {
    'min_lat': 33.5,   # North of Scottsdale/Cave Creek
    'max_lat': 35.1,   # South of Flagstaff
}

# Preferred area: Prescott/Sedona region (lower weight, but nice to have)
PREFERRED_AREAS = [
    'prescott', 'prescott valley', 'sedona', 'cottle', 'camp verde',
    'cottonwood', 'clarkdale', 'jerome', 'cordes lakes', 'spring valley',
    'mayer', 'dewey', 'humboldt', 'chino valley', 'ash fork', 'williams',
    'verde valley', 'big park', 'west Sedona', 'Lake Montezuma',
    'Beaver Creek', 'Cornville', 'Page Springs', 'Yarnell', 'Peeples Valley',
    ' Skull Valley', 'Paulden', 'Chino Valley', 'Kirkland',
]

# Craigslist regions in our area
CRAIGSLIST_REGIONS = [
    'phoenix',    # Phoenix metro, north of Scottsdale
    'prescott',   # Prescott area - our sweet spot
    'flagstaff',  # Northern edge (Flagstaff itself is borderline)
    'yuma',       # Yuma - some desert land
]
