"""config.py - Settings for land scraper."""  # this file holds all the configurable values so nothing important lives buried in the main logic
                                         # docstrings are triple-quoted and sit at the top of a module to describe its purpose

import os, pathlib                        # os lets me reach into environment variables, pathlib handles file paths across any OS
from dotenv import load_dotenv            # pulls secrets and settings out of a .env file so I don't have to hardcode them

load_dotenv()                            # this actually loads the .env file into the environment so os.environ can find the values

ROOT_DIR = pathlib.Path(__file__).parent  # __file__ points to this config.py, .parent walks up one folder to the project root
DB_PATH = str(ROOT_DIR / 'data' / 'lands.db')  # builds the full path to the SQLite database and converts it to a string so sqlite3 accepts it
DISCORD_WEBHOOK = os.environ.get('DISCORD_WEBHOOK_URL_LAND')  # grabs the Discord webhook URL from the environment; returns None if it's missing
MIN_SCORE = 40                           # parcels scoring below this threshold get skipped during filtering
MAX_PRICE = 100000                       # listings above this price won't get sent to Discord

CRAIGSLIST_REGIONS = ['phoenix', 'prescott', 'flagstaff', 'yuma']  # these are the Craigslist subdomains I want to scrape for land listings
CL_LAND_PATH = '/rea'                    # Craigslist appends this path to the region URL to land on the real estate section

PLAYWRIGHT_SITES = [                     # sites that need a full browser engine to render JavaScript before I can scrape them
    {'name': 'landmodo', 'url': 'https://www.landmodo.com/arizona-land-for-sale/cheap-land'},  # landmodo serves listings via JS so a simple HTTP request won't work
]                                        # closing bracket ends the list

GEO_BOUNDS = {'min_lat': 33.5, 'max_lat': 35.1}  # anything outside these latitude limits gets tossed out during geocoding checks
PREFERRED_AREAS = ['prescott', 'sedona', 'verde valley', 'cottle', 'camp verde', 'cottonwood', 'clarkdale', 'jerome', 'cordes lakes', 'spring valley', 'mayer', 'dewey', 'chino valley', 'williams', 'big park']  # parcels in these towns get a boost because they match what I actually want to buy
