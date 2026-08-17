"""
filters.py - Skip patterns and scoring logic for land listings.
"""

import re

# Skip patterns - listings that aren't actual land for sale
SKIP_PATTERN = re.compile(
    r'for rent|for lease|room|roommate|parking|storage|mobile home park| rv |rv lot|camper|vacation rental',
    re.IGNORECASE
)

# High value keywords - boost score significantly
HIGH_VALUE = re.compile(
    r'water well|well on property|has a well|existing well|well drilled|well permit|well rights',
    re.IGNORECASE
)

# Owner financing keywords - boost score
OWNER_CARRY = re.compile(
    r'owner will carry|owner financing|seller financing|owner carry|will carry|seller will carry|terms available|flexible terms|owner terms',
    re.IGNORECASE
)

# Good keywords - moderate boost
GOOD_WORDS = re.compile(
    r'acreage|acres|utilities|electric|power|road access|paved road|county road|gated|fenced|mountain view|city view|river|creek|spring|mineral rights|water rights|no hoa|no restrictions|unrestricted',
    re.IGNORECASE
)

# Bad keywords - lower score or skip
BAD_WORDS = re.compile(
    r'leash|lien|tax deed|auction|bank owned|reo|short sale|contingent|pending|under contract|sold',
    re.IGNORECASE
)


def should_skip(title, text=''):
    """Return True if listing should be skipped."""
    combined = f'{title} {text}'
    if SKIP_PATTERN.search(combined):
        return True
    if BAD_WORDS.search(combined):
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

    # Good features = moderate bonus
    if GOOD_WORDS.search(combined):
        score += 10

    # Price incentives
    if price > 0:
        if price < 5000:
            score += 15
        elif price < 15000:
            score += 10
        elif price < 30000:
            score += 5

    return max(0, min(100, score))
