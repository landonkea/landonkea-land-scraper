# Land Scraper — Site Status

## Working Sources

| Site | Method | Listings | Notes |
|------|--------|----------|-------|
| **Craigslist** | Requests (HTML) | ~438 | Phoenix, Prescott, Flagstaff, Yuma. Best for cheap private-seller deals. |
| **Landmodo** | Playwright | ~25 | Owner-financed land marketplace. Good for terms deals ($100-200/mo). |
| **GovAuctions** | Playwright | ~12 | Government surplus (HUD, federal, county tax deeds). Some as low as $995. |

---

## Blocked Sites

### Akamai-Blocked

| Site | Block Type |
|------|-----------|
| **LandWatch** | Akamai "Access Denied" |
| **LandAndFarm** | Akamai (sister site of LandWatch) |
| **Homes.com** | Akamai |
| **Land.com** | Akamai |
| **GovDeals** | Akamai |

### CAPTCHA-Blocked

| Site | Block Type |
|------|-----------|
| **Zillow** | CAPTCHA ("Press & Hold to confirm you are human") |
| **Trulia** | CAPTCHA (same as Zillow — same parent company) |
| **Movoto** | CAPTCHA (same system as Zillow) |

### Custom Bot Detection

| Site | Block Type |
|------|-----------|
| **Realtor.com** | Custom detection (returns empty page) |
| **Redfin** | Custom detection ("You might be a robot") |

### Cloudflare-Blocked

| Site | Block Type |
|------|-----------|
| **Crexi** | Cloudflare JS challenge |
| **LandZero** | Cloudflare + JS doesn't render |

---

## How Anti-Bot Systems Work

### What They Check (In Order)

1. **IP Reputation** — Is this a datacenter IP or a real home IP? Datacenter = blocked immediately.
2. **TLS Fingerprint** — Does the SSL handshake match a real browser? Python's `requests` library has a unique fingerprint that screams "bot."
3. **Browser Fingerprint** — Is this a real browser or headless Chromium? Checks `navigator.webdriver`, plugins, canvas rendering, etc.
4. **Behavior Patterns** — Scroll speed, mouse movement, timing. Too fast = bot.
5. **JavaScript Environment** — Checks for Selenium, Puppeteer, Playwright automation markers.

**The key insight:** If you fail check #1 (IP reputation), nothing else matters. You're blocked before the other checks even run.

---

## How To Bypass Each Layer

### Layer 1: IP Reputation (The Big One)

**The problem:** GitHub Actions, your Mac, and VPS servers all use datacenter IPs. Akamai, Cloudflare, and custom anti-bot systems flag these immediately.

**The solution: Residential proxies.**

A residential proxy routes your traffic through a real person's home internet connection. The anti-bot system sees a normal home IP instead of a server farm.

**Think of it like this:**
- Datacenter IP = showing up to a store in a delivery truck with a clipboard (suspicious)
- Residential IP = showing up in a regular car in regular clothes (normal)

**Providers:**
| Provider | Cost | Notes |
|----------|------|-------|
| **Bright Data** | $50/mo for 1GB | Largest provider, most reliable |
| **Oxylabs** | $49/mo | Enterprise-grade |
| **NodeMaven** | $30/mo | Newer, cheaper |
| **Scrapfly** | $30/mo | Includes anti-bot bypass |

### Layer 2: TLS Fingerprint

**The problem:** Python's `requests` library produces a TLS handshake that doesn't match any real browser. Akamai detects this.

**The solution: curl-cffi or scrapy-impersonate.**

These libraries use curl's TLS stack to impersonate specific browser versions. Your requests look like they come from real Chrome.

```python
# Instead of:
import requests
r = requests.get(url)  # ← Fingerprint says "bot"

# Use:
from curl_cffi import requests
r = requests.get(url, impersonate="chrome")  # ← Fingerprint says "Chrome 120"
```

### Layer 3: Browser Fingerprint

**The problem:** Headless Chromium (Playwright, Selenium) has detectable properties — `navigator.webdriver` is true, missing plugins, wrong canvas rendering.

**The solutions:**

| Tool | How It Works | Cost |
|------|-------------|------|
| **playwright-stealth** | Patches Playwright's JavaScript environment | Free (already using this) |
| **Camoufox** | Modified Firefox, spoofs fingerprints at C++ level | Free |
| **Nodriver** | Chrome without CDP automation markers | Free |
| **undetected-chromedriver** | Patched Selenium ChromeDriver | Free |

**Camoufox** is the most effective in 2026 — it operates at the C++ level rather than through detectable JavaScript patches.

### Layer 4: Behavior Patterns

**The problem:** Bots scroll and click too fast. Real humans are slow and inconsistent.

**The solution:** Random delays between actions.

```python
import time, random
time.sleep(random.uniform(2, 5))  # Wait 2-5 seconds between actions
```

### Layer 5: JavaScript Environment

**The problem:** Selenium/Puppeteer/Playwright leave markers in the browser's JavaScript environment.

**The solution:** Use Nodriver (no CDP) or Camoufox (Firefox-based).

---

## Complete Bypass Stack (If You Want to Spend Money)

To reliably bypass all anti-bot systems, you need:

1. **Residential proxy** ($50/mo) — Fixes IP reputation
2. **curl-cffi** (free) — Fixes TLS fingerprint
3. **Camoufox or playwright-stealth** (free) — Fixes browser fingerprint
4. **Random delays** (free) — Fixes behavior patterns

**Total cost: ~$50/mo** to bypass Akamai, Cloudflare, and most custom detection.

**What this would unlock:**
- LandWatch, LandAndFarm, Homes.com, Land.com, GovDeals (Akamai)
- Crexi (Cloudflare)

**What it still can't reliably bypass:**
- Zillow, Trulia, Movoto (CAPTCHA — needs human interaction or CAPTCHA solver)
- Realtor.com, Redfin (custom detection — needs site-specific reverse engineering)

---

## FlareSolverr — Cloudflare Only

### What It Is
Open-source proxy server (free, self-hosted) that bypasses Cloudflare specifically. GitHub: [FlareSolverr/FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) (15k+ stars, MIT license).

### How It Works
1. You send FlareSolverr a URL via HTTP request
2. It launches a real Chrome browser with undetected-chromedriver
3. Opens the URL and waits for the Cloudflare challenge to clear
4. Returns the final HTML + session cookies
5. You reuse those cookies with normal HTTP requests

### What It Could Unlock
- **Crexi** — Cloudflare-protected
- **LandZero** — Partially (Cloudflare passes, but JS rendering is separate issue)

### What It Can't Touch
- **Akamai sites** — LandWatch, LandAndFarm, Homes.com, Land.com, GovDeals
- **CAPTCHA sites** — Zillow, Trulia, Movoto
- **Custom detection** — Realtor.com, Redfin

### Limitations
- Only works on **Cloudflare**, not Akamai or custom detection
- Breaks periodically when Cloudflare updates
- Resource-heavy (launches Chrome per request)
- If the site shows a CAPTCHA, it fails

### Bottom Line
FlareSolverr would add maybe 1-2 sites. Not worth the setup complexity for a free scraper.

---

## The Honest Math

| Approach | Cost | Sites Unlocked | Worth It? |
|----------|------|----------------|-----------|
| Current setup (Craigslist + Landmodo + GovAuctions) | Free | 3 sources, ~475 listings | Yes — already finding cheapest deals |
| FlareSolverr | Free (self-hosted) | +1-2 sites (Crexi) | Marginal |
| Residential proxy only | $50/mo | +5 Akamai sites | Maybe if you want more sources |
| Full stack (proxy + tools) | $50/mo | +7-8 sites | Overkill for land scraping |
| Everything (proxy + CAPTCHA solver) | $100-300/mo | All sites | Not worth it |

**The reality:** The blocked sites (LandWatch, Zillow, Realtor, etc.) tend to have higher-priced listings anyway. Craigslist, Landmodo, and GovAuctions are where the cheapest land actually is. You're already scraping the best sources for free.

---

## Sites Not Tested

| Site | URL | Notes |
|------|-----|-------|
| ParcelFair | parcelfair.com | Tax lien/deed aggregator, paid service |
| TaxSaleAtlas | taxsaleatlas.com | Free tax sale calendar, no direct listings |
| ADOT Surplus | azdot.gov | State surplus land, small inventory |
| Maricopa County | maricopa.gov | Tax-deeded land, as-needed basis |
| Yavapai County | yavapaiaz.gov | Tax deed sales, over-the-counter list |
