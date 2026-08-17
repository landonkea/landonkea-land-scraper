"""config.py - Settings for land scraper."""

import os, pathlib
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = pathlib.Path(__file__).parent
DB_PATH = str(ROOT_DIR / 'data' / 'lands.db')
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK_URL_LAND')
MIN_SCORE = 40

CRAIGSLIST_REGIONS = ['phoenix', 'prescott', 'flagstaff', 'yuma']
CL_LAND_PATH = '/rea'

PLAYWRIGHT_SITES = [
    {'name': 'zillow', 'domain': 'zillow.com', 'url': 'https://www.zillow.com/phoenix-az/land/'},
    {'name': 'realtor', 'domain': 'realtor.com', 'url': 'https://www.realtor.com/realestateandhomes-search/Phoenix_AZ/land'},
    {'name': 'landwatch', 'domain': 'landwatch.com', 'url': 'https://www.landwatch.com/arizona-land-for-sale'},
    {'name': 'landandfarm', 'domain': 'landandfarm.com', 'url': 'https://www.landandfarm.com/Arizona-land-for-sale'},
    {'name': 'crexi', 'domain': 'crexi.com', 'url': 'https://www.crexi.com/properties?type=land&sort=price_asc&state=Arizona'},
]

GEO_BOUNDS = {'min_lat': 33.5, 'max_lat': 35.1}
PREFERRED_AREAS = ['prescott', 'sedona', 'verde valley', 'cottle', 'camp verde', 'cottonwood', 'clarkdale', 'jerome', 'cordes lakes', 'spring valley', 'mayer', 'dewey', 'chino valley', 'williams', 'big park']
