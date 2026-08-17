"""
filters.py - Skip patterns and scoring logic for land listings.
"""

import re

# Skip patterns - listings that aren't actual land for sale
SKIP_PATTERN = re.compile(
    r'for rent|for lease|room|roommate|parking|storage|mobile home park| rv |rv lot|camper|vacation rental|airbnb|vrbo',
    re.IGNORECASE
)

# Bad listing filters - skip these entirely
FLOOD_ZONE = re.compile(
    r'flood zone|floodplain|flood plain|flood insurance|fema flood|100-year flood|500-year flood',
    re.IGNORECASE
)

LANDLOCKED = re.compile(
    r'landlocked|no road access|no easement|no legal access|land locked',
    re.IGNORECASE
)

HOA_RESTRICTIONS = re.compile(
    r'hoa\b|homeowners association|monthly hoa|hoa fees|hoa dues|community association|cc&r|cc and r|ccr restrictions',
    re.IGNORECASE
)

LEASE_ONLY = re.compile(
    r'lease only|for lease|for rent|leasing only|long-term lease|ground lease|sublease',
    re.IGNORECASE
)

LIEN = re.compile(
    r'tax lien|government lien|irs lien|federal lien|tax deed|tax sale|auction|bank owned|reo|short sale|foreclosure|lis pendens',
    re.IGNORECASE
)

# Bonus scoring keywords
PAVED_ROAD = re.compile(
    r'paved road|paved access|asphalt road|asphalt access|highway frontage|state road|county road paved',
    re.IGNORECASE
)

ELECTRIC = re.compile(
    r'electric|power|electricity|electric on site|power on site|pg&e|aps|srp|electric available|power available|grid power|utility pole',
    re.IGNORECASE
)

MOBILE_HOME = re.compile(
    r'mobile home allowed|manufactured home|mobile permitted|manufactured permitted|mobile ok|manufactured ok|single wide|double wide|mobile home permitted|factory built home',
    re.IGNORECASE
)

RV_ALLOWED = re.compile(
    r'rv allowed|rv parking|rv ok|camper allowed|rv permitted|rv friendly|live in rv|rv use|camping allowed|rv friendly',
    re.IGNORECASE
)

PUBLIC_LAND = re.compile(
    r'adjacent to public|bordering public|next to national forest|near blm|near national forest|adjacent to state land|bordering state|near forest|backs to public|backs to national|shares border with',
    re.IGNORECASE
)

LOW_TAX = re.compile(
    r'low tax|low property tax|low taxes|minimal tax|affordable tax|low yearly tax|low annual tax|no property tax',
    re.IGNORECASE
)

CELL_COVERAGE = re.compile(
    r'cell service|cell coverage|cell signal|cell reception|strong signal|good reception|mobile coverage|verizon|at&t|t-mobile coverage',
    re.IGNORECASE
)

# Good keywords - moderate boost
GOOD_WORDS = re.compile(
    r'acreage|acres|utilities|road access|gated|fenced|mountain view|city view|river|creek|spring|mineral rights|water rights|no hoa|no restrictions|unrestricted|well|septic|perc test|percolation|buildable|usable|gentle terrain|level lot|flat land|surveyed|corner lot|cul-de-sac',
    re.IGNORECASE
)

# High value keywords - big bonus
HIGH_VALUE = re.compile(
    r'water well|well on property|has a well|existing well|well drilled|well permit|well rights|water well on|well with pump|well producing',
    re.IGNORECASE
)

OWNER_CARRY = re.compile(
    r'owner will carry|owner financing|seller financing|owner carry|will carry|seller will carry|terms available|flexible terms|owner terms|low down|small down|easy terms|affordable terms|payments|monthly payment|no credit check|bad credit ok|owner financed|seller carries|seller financed',
    re.IGNORECASE
)


def parse_lot_size(text):
    """Extract lot size in acres from text. Returns float or None."""
    text = text.lower()

    # Match "X acres" or "X acre" or "X ac"
    acre_match = re.search(r'([\d,.]+)\s*(?:acres?|ac\.?)\b', text)
    if acre_match:
        try:
            return float(acre_match.group(1).replace(',', ''))
        except ValueError:
            pass

    # Match "X sq ft" and convert to acres (1 acre = 43560 sq ft)
    sqft_match = re.search(r'([\d,.]+)\s*(?:sq\.?\s*ft|sqft|square\s*feet)', text)
    if sqft_match:
        try:
            sqft = float(sqft_match.group(1).replace(',', ''))
            return sqft / 43560
        except ValueError:
            pass

    # Match "lot size X" patterns
    lot_match = re.search(r'lot\s*size[:\s]*([\d,.]+)', text)
    if lot_match:
        try:
            return float(lot_match.group(1).replace(',', ''))
        except ValueError:
            pass

    return None


def should_skip(title, text=''):
    """Return True if listing should be skipped."""
    combined = f'{title} {text}'

    # Basic skip patterns
    if SKIP_PATTERN.search(combined):
        return True

    # Flood zone
    if FLOOD_ZONE.search(combined):
        return True

    # Landlocked
    if LANDLOCKED.search(combined):
        return True

    # HOA restrictions
    if HOA_RESTRICTIONS.search(combined):
        return True

    # Lease only
    if LEASE_ONLY.search(combined):
        return True

    # Government/tax liens
    if LIEN.search(combined):
        return True

    # Check lot size minimum
    lot_size = parse_lot_size(combined)
    if lot_size is not None and lot_size < 0.2:
        return True

    return False


def score_listing(title, text='', price=0):
    """Score a land listing 0-100. Higher = better."""
    combined = f'{title} {text}'
    score = 40

    # Water well = huge bonus
    if HIGH_VALUE.search(combined):
        score += 35

    # Owner will carry = big bonus
    if OWNER_CARRY.search(combined):
        score += 25

    # Paved road access
    if PAVED_ROAD.search(combined):
        score += 10

    # Electric/power on site
    if ELECTRIC.search(combined):
        score += 8

    # Mobile home allowed
    if MOBILE_HOME.search(combined):
        score += 10

    # RV parking allowed
    if RV_ALLOWED.search(combined):
        score += 8

    # Adjacent to public land / national forest
    if PUBLIC_LAND.search(combined):
        score += 10

    # Low property tax
    if LOW_TAX.search(combined):
        score += 5

    # Cell coverage
    if CELL_COVERAGE.search(combined):
        score += 5

    # Good features (generic)
    if GOOD_WORDS.search(combined):
        score += 10

    # Price scoring (raw price)
    if price > 0:
        if price < 5000:
            score += 15
        elif price < 15000:
            score += 10
        elif price < 30000:
            score += 5

    # Price per acre bonus (if we can determine lot size)
    lot_size = parse_lot_size(combined)
    if lot_size is not None and lot_size >= 0.2:
        price_per_acre = price / lot_size if lot_size > 0 else 0
        if price_per_acre > 0:
            if price_per_acre < 1000:
                score += 20  # Under $1,000/acre = amazing deal
            elif price_per_acre < 2500:
                score += 15  # Under $2,500/acre = good deal
            elif price_per_acre < 5000:
                score += 10  # Under $5,000/acre = decent
            elif price_per_acre < 10000:
                score += 5   # Under $10,000/acre = okay

    # Prescott/Sedona area bonus
    area_text = combined.lower()
    if any(area in area_text for area in ['prescott', 'sedona', 'verde valley', 'cottle', 'camp verde', 'cottonwood', 'clarkdale', 'jerome', 'cordes lakes', 'spring valley', 'mayer', 'dewey', 'humboldt', 'chino valley', 'ash fork', 'williams']):
        score += 5

    return max(0, min(100, score))
