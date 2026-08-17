"""filters.py - Skip patterns and scoring for land listings."""

import re

SKIP = re.compile(r'for rent|for lease|room|roommate|parking|storage|mobile home park| rv |rv lot|camper|vacation rental|airbnb|vrbo', re.I)
FLOOD = re.compile(r'flood zone|floodplain|flood plain|flood insurance|fema flood|100-year flood', re.I)
LOCKED = re.compile(r'landlocked|no road access|no easement|no legal access', re.I)
HOA = re.compile(r'hoa\b|homeowners association|hoa fees|hoa dues|cc&r|cc and r', re.I)
LEASE = re.compile(r'lease only|for lease|leasing only|ground lease|sublease', re.I)
LIEN = re.compile(r'tax lien|government lien|irs lien|tax deed|tax sale|auction|bank owned|reo|short sale|foreclosure|lis pendens', re.I)
PAVED = re.compile(r'paved road|paved access|asphalt|highway frontage|state road', re.I)
ELECTRIC = re.compile(r'electric|power|electricity|pg&e|aps|srp|utility pole|grid power', re.I)
MOBILE = re.compile(r'mobile home allowed|manufactured home|mobile permitted|manufactured ok|single wide|double wide|factory built', re.I)
RV = re.compile(r'rv allowed|rv parking|rv ok|camper allowed|rv permitted|rv friendly|live in rv|camping allowed', re.I)
PUBLIC = re.compile(r'adjacent to public|bordering public|next to national forest|near blm|near forest|backs to public', re.I)
TAX = re.compile(r'low tax|low property tax|minimal tax|no property tax', re.I)
CELL = re.compile(r'cell service|cell coverage|cell signal|verizon|at&t|t-mobile', re.I)
GOOD = re.compile(r'acreage|acres|utilities|road access|gated|fenced|mountain view|river|creek|spring|mineral rights|water rights|no hoa|no restrictions|unrestricted|well|septic|perc test|buildable|level lot|flat land|surveyed|corner lot', re.I)
HIGH = re.compile(r'water well|well on property|existing well|well drilled|well permit|well rights|well with pump', re.I)
CARRY = re.compile(r'owner will carry|owner financing|seller financing|owner carry|seller will carry|terms available|flexible terms|low down|easy terms|owner financed|seller financed', re.I)


def parse_acres(text):
    """Extract lot size in acres."""
    m = re.search(r'([\d,.]+)\s*(?:acres?|ac\.?)\b', text.lower())
    if m:
        try: return float(m.group(1).replace(',', ''))
        except ValueError: pass
    m = re.search(r'([\d,.]+)\s*(?:sq\.?\s*ft|sqft|square\s*feet)', text.lower())
    if m:
        try: return float(m.group(1).replace(',', '')) / 43560
        except ValueError: pass
    return None


def should_skip(title, text=''):
    """Return True if listing should be skipped."""
    c = f'{title} {text}'
    if any(p.search(c) for p in [SKIP, FLOOD, LOCKED, HOA, LEASE, LIEN]):
        return True
    acres = parse_acres(c)
    if acres is not None and acres < 0.2:
        return True
    return False


def score_listing(title, text='', price=0):
    """Score a land listing 0-100."""
    c = f'{title} {text}'.lower()
    s = 40
    if HIGH.search(c): s += 35
    if CARRY.search(c): s += 25
    if PAVED.search(c): s += 10
    if ELECTRIC.search(c): s += 8
    if MOBILE.search(c): s += 10
    if RV.search(c): s += 8
    if PUBLIC.search(c): s += 10
    if TAX.search(c): s += 5
    if CELL.search(c): s += 5
    if GOOD.search(c): s += 10
    if price > 0:
        if price < 5000: s += 15
        elif price < 15000: s += 10
        elif price < 30000: s += 5
    acres = parse_acres(c)
    if acres and acres >= 0.2 and price > 0:
        ppa = price / acres
        if ppa < 1000: s += 20
        elif ppa < 2500: s += 15
        elif ppa < 5000: s += 10
        elif ppa < 10000: s += 5
    if any(a in c for a in ['prescott', 'sedona', 'verde valley', 'cottle', 'camp verde', 'cottonwood', 'clarkdale', 'jerome', 'chino valley', 'williams']):
        s += 5
    return max(0, min(100, s))
