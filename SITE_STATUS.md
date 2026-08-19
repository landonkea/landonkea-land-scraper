# Land Scraper — Site Status

## Working Sources

| Site | Method | Listings | Notes |
|------|--------|----------|-------|
| **Craigslist** | Requests (HTML) | ~438 | Phoenix, Prescott, Flagstaff, Yuma. Best for cheap private-seller deals. |
| **Landmodo** | Playwright | ~25 | Owner-financed land marketplace. Good for terms deals ($100-200/mo). |
| **GovAuctions** | Playwright | ~12 | Government surplus (HUD, federal, county tax deeds). Some as low as $995. |

## Blocked Sites

| Site | Block Type | Would Cost to Bypass |
|------|-----------|---------------------|
| Zillow | CAPTCHA (Press & Hold) | Residential proxy + CAPTCHA solver |
| Trulia | CAPTCHA (same as Zillow) | Same as Zillow |
| Movoto | CAPTCHA (same as Zillow) | Same as Zillow |
| Realtor.com | Bot detection (empty page) | Residential proxy |
| LandWatch | Akamai | Residential proxy ($50+/mo) |
| LandAndFarm | Akamai (sister site) | Same as LandWatch |
| Homes.com | Akamai | Same as LandWatch |
| Land.com | Akamai | Same as LandWatch |
| Crexi | Cloudflare | Cloudflare bypass service |
| Redfin | Custom bot detection | Residential proxy |
| GovDeals | Akamai | Same as LandWatch |
| LandZero | JS doesn't render | Would need full browser with JS execution |

## Why They're Blocked

All major real estate sites use enterprise anti-bot systems (Akamai, Cloudflare, custom) that detect headless browsers. These systems check:
- Browser fingerprint (headless vs real)
- IP reputation (datacenter vs residential)
- Behavior patterns (scroll speed, mouse movement)
- JavaScript environment (navigator properties)

Bypassing requires either:
- Residential proxies ($50-200/month) — rotate through real residential IPs
- CAPTCHA solving services ($1-3 per 1000 CAPTCHAs)
- Both combined

**Not worth it for a free scraper** — Craigslist + Landmodo + GovAuctions cover the market well.
