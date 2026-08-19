"""filters.py - Skip patterns and scoring for land listings."""
# This module handles filtering out bad listings and scoring the good ones.
# Skip patterns catch rentals, flood zones, and other deal-breakers.
# Scoring gives points for desirable features like wells and owner financing.

import re  # We need regular expressions to search through listing text quickly.

# Compiled regex to catch listings that aren't actually land for sale.
# Matches rental properties, parking spots, storage units, and vacation rentals.
SKIP = re.compile(r'for rent|for lease|room|roommate|parking|storage|mobile home park| rv |rv lot|camper|vacation rental|airbnb|vrbo|rent to own|rental|yearly rental|winter rental|rent this|monthly rent|per month|\/mo|/year|annaul rental|sale or rent|or rent|free rent|paying.*rent', re.I)

# Compiled regex to flag properties in flood-prone areas.
# Flood zones are a deal-breaker because of insurance costs and safety risks.
FLOOD = re.compile(r'flood zone|floodplain|flood plain|flood insurance|fema flood|100-year flood', re.I)

# Compiled regex to detect landlocked properties with no road access.
# If you can't reach the land legally, it's basically useless.
LOCKED = re.compile(r'landlocked|no road access|no easement|no legal access', re.I)

# Compiled regex to find properties with no HOA or restrictions.
# The \s* allows for optional spaces between "no" and "hoa" in listings.
# This catches phrases like "no HOA", "no restrictions", and "unrestricted".
NO_HOA = re.compile(r'no\s*hoa|no\s*homeowners\s*assoc|no\s*restrictions|unrestricted|no\s*cc&r|no\s*cc\s*and\s*r|no\s*dues', re.I)

# Compiled regex to detect properties with HOA fees or covenants.
# HOA fees add monthly costs and restrictions on what you can build.
HOA = re.compile(r'hoa\b|homeowners association|hoa fees|hoa dues|cc&r|cc and r', re.I)

# Compiled regex to catch lease-only properties.
# You don't own the land if it's a ground lease, you're just renting it.
LEASE = re.compile(r'lease only|for lease|leasing only|ground lease|sublease', re.I)

# Compiled regex to flag properties with liens or in foreclosure.
# Tax liens and foreclosures mean legal headaches and potential loss of property.
LIEN = re.compile(r'tax lien|government lien|irs lien|bank owned|reo|short sale|foreclosure|lis pendens', re.I)

# Compiled regex to identify properties with paved road access.
# Paved roads mean easier access and better resale value.
PAVED = re.compile(r'paved road|paved access|asphalt|highway frontage|state road', re.I)

# Compiled regex to detect available electric utilities.
# Electric power is essential for building or camping on the land.
ELECTRIC = re.compile(r'electric|power|electricity|pg&e|aps|srp|utility pole|grid power', re.I)

# Compiled regex to find properties that allow mobile homes.
# Mobile homes are an affordable way to live on cheap land.
MOBILE = re.compile(r'mobile home allowed|manufactured home|mobile permitted|manufactured ok|single wide|double wide|factory built', re.I)

# Compiled regex to spot RV-friendly properties.
# RV parking lets you use the land immediately while building or camping.
RV = re.compile(r'rv allowed|rv parking|rv ok|camper allowed|rv permitted|rv friendly|live in rv|camping allowed', re.I)

# Compiled regex to find land next to public areas like national forests.
# Adjacent public land gives you more space and privacy without buying more.
PUBLIC = re.compile(r'adjacent to public|bordering public|next to national forest|near blm|near forest|backs to public', re.I)

# Compiled regex to detect low-tax properties.
# Lower property taxes mean lower ongoing costs for owning the land.
TAX = re.compile(r'low tax|low property tax|minimal tax|no property tax', re.I)

# Compiled regex to check for cell service availability.
# Cell coverage is important for safety and communication in rural areas.
CELL = re.compile(r'cell service|cell coverage|cell signal|verizon|at&t|t-mobile', re.I)

# Compiled regex to catch all the good features in one pattern.
# This is the catch-all for desirable traits like road access, utilities, and views.
GOOD = re.compile(r'acreage|acres|utilities|road access|gated|fenced|mountain view|river|creek|spring|mineral rights|water rights|no hoa|no restrictions|unrestricted|well|septic|perc test|buildable|level lot|flat land|surveyed|corner lot', re.I)

# Compiled regex specifically for properties with an existing water well.
# A drilled well is the single most valuable feature for remote land.
HIGH = re.compile(r'water well|well on property|existing well|well drilled|well permit|well rights|well with pump', re.I)

# Compiled regex to find owner financing or seller carry options.
# Owner financing makes land affordable without needing a bank loan.
CARRY = re.compile(r'owner will carry|owner financing|seller financing|owner carry|seller will carry|terms available|flexible terms|low down|easy terms|owner financed|seller financed', re.I)


# This function pulls the lot size out of listing text.
# It looks for acreage first, then square footage as a fallback.
def parse_acres(text):
    """Extract lot size in acres."""
    # Search for acreage values like "5 acres" or "2.5 ac."
    # The regex captures numbers with commas or decimals, then the unit.
    m = re.search(r'([\d,.]+)\s*(?:acres?|ac\.?)\b', text.lower())
    if m:  # If we found an acreage match, try to convert it to a number.
        try: return float(m.group(1).replace(',', ''))  # Remove commas and convert to float.
        except ValueError: pass  # If conversion fails, keep looking.
    # No acreage found, so try square footage instead.
    # Many listings use square feet for smaller parcels.
    m = re.search(r'([\d,.]+)\s*(?:sq\.?\s*ft|sqft|square\s*feet)', text.lower())
    if m:  # Found a square footage match, now convert to acres.
        try: return float(m.group(1).replace(',', '')) / 43560  # There are 43,560 sq ft in an acre.
        except ValueError: pass  # If conversion fails, give up.
    return None  # Couldn't find or parse any size information.


# This function decides whether to skip a listing entirely.
# It catches the obvious bad ones before we waste time scoring them.
def should_skip(title, text=''):
    """Return True if listing should be skipped."""
    c = f'{title} {text}'  # Combine title and description for easier searching.
    # Check if any of our skip patterns match the listing text.
    # This catches rentals, flood zones, landlocked, lease-only, and liens.
    if any(p.search(c) for p in [SKIP, FLOOD, LOCKED, LEASE, LIEN]):
        return True  # Found a deal-breaker, skip this listing.
    # HOA is bad, but "no HOA" is good, so check for both.
    # Only skip if HOA is mentioned without the "no" qualifier.
    if HOA.search(c) and not NO_HOA.search(c):
        return True  # Has HOA fees, skip it.
    acres = parse_acres(c)  # Try to figure out how big the property is.
    if acres is not None and acres < 0.2:  # Less than a fifth of an acre is too small.
        return True  # Too small to be useful, skip it.
    return False  # No red flags found, this listing is worth scoring.


# This function gives a land listing a score from 0 to 100.
# Higher scores mean better deals with more desirable features.
def score_listing(title, text='', price=0):
    """Score a land listing 0-100."""
    c = f'{title} {text}'.lower()  # Combine and lowercase everything for consistent matching.
    s = 40  # Start at 40 points as a baseline for all listings.
    if HIGH.search(c): s += 35  # An existing well is the best feature, worth 35 points.
    if CARRY.search(c): s += 25  # Owner financing makes land accessible, worth 25 points.
    if NO_HOA.search(c): s += 10  # No HOA means no monthly fees or restrictions.
    if PAVED.search(c): s += 10  # Paved roads make access easy year-round.
    if ELECTRIC.search(c): s += 8  # Electric power saves thousands in utility costs.
    if MOBILE.search(c): s += 10  # Mobile home permission means affordable housing options.
    if RV.search(c): s += 8  # RV-friendly land lets you use it immediately.
    if PUBLIC.search(c): s += 10  # Bordering public land adds privacy and space.
    if TAX.search(c): s += 5  # Low taxes reduce your yearly ownership costs.
    if CELL.search(c): s += 5  # Cell service is important for safety and convenience.
    if GOOD.search(c): s += 10  # General good features get a bonus points.
    if price > 0:  # Only apply price bonuses if we have a price.
        if price < 5000: s += 15  # Under $5k is a steal, big bonus.
        elif price < 15000: s += 10  # Under $15k is still very affordable.
        elif price < 30000: s += 5  # Under $30k is reasonable for land.
    acres = parse_acres(c)  # Get the acreage for price-per-acre math.
    # Only calculate price-per-acre if we have both values and it's at least 0.2 acres.
    if acres and acres >= 0.2 and price > 0:
        ppa = price / acres  # Divide price by acres to get cost per acre.
        if ppa < 1000: s += 20  # Under $1k per acre is an amazing deal.
        elif ppa < 2500: s += 15  # Under $2.5k per acre is very good.
        elif ppa < 5000: s += 10  # Under $5k per acre is fair.
        elif ppa < 10000: s += 5  # Under $10k per acre is acceptable.
    # Give a small bonus for properties in popular Arizona areas.
    # These locations have proven demand and resale potential.
    if any(a in c for a in ['prescott', 'sedona', 'verde valley', 'cottle', 'camp verde', 'cottonwood', 'clarkdale', 'jerome', 'chino valley', 'williams']):
        s += 5  # Preferred location bonus.
    return max(0, min(100, s))  # Keep the score between 0 and 100, no negatives or over 100.
