# Land Scraper — Site Status

Last updated: August 2026

---

## WORKING SOURCES (10 total)

| Source | Method | Listings | Price Range | Notes |
|--------|--------|----------|-------------|-------|
| **Craigslist** | Requests (HTML) | ~415 | $0 - $3.2M | Phoenix, Prescott, Flagstaff, Yuma, Tucson. Best for cheap private-seller deals. |
| **Cochise County** | PDF (pdfplumber) | ~335 | $265 - $15,300 | Tax deed parcels. PDF from county, updated per sale cycle. |
| **Landmodo** | Playwright | ~15 | $4,699 - $9,499 | Owner-financed land marketplace. Good for terms deals. |
| **Maricopa County** | Playwright | ~18 | TBD | Excess government land (flood control, highway). Prices often $0 (call for price). |
| **Yavapai County** | PDF + ArcGIS API | ~48 | $403 - $12,934 | Over-the-counter tax deed parcels near Prescott. Queries ArcGIS for subdivision/address details. |
| **GovAuctions** | Playwright | ~12 | $995 - $15,500 | Government surplus (HUD, federal, county tax deeds). |
| **Pinal County** | PDF (pdfplumber) | 4 | $7,300 - $17,250 | Over-the-counter state tax deed list. Updated monthly. |
| **Mohave County** | PDF (pdfplumber) | 3 | $1,027 - $5,751 | OTC tax deed parcels. Updated monthly. |
| **ADOT** | Requests (HTML) | 8 | $75,000 - $733,000 | State DOT surplus land. Clean HTML. |
| **Land Zero** | Playwright | 0 | — | Added to pipeline but all listings show "Out of Stock." Monitored for restocks. |

---

## ARIZONA COUNTY TAX DEED STATUS (All 15 Counties)

Tax deed properties are the cheapest way to buy land — you pay back taxes and own the property outright. Here's the status of every Arizona county:

### Counties With Automated Scrapers

| County | Source | Status | Price Range | How to Access |
|--------|--------|--------|-------------|---------------|
| **Cochise** | PDF scraper | ✅ WORKING | $265 - $15,300 | `cochise.az.gov/811/2026-Tax-Deed-Land-Sale` |
| **Mohave** | PDF scraper | ✅ WORKING | $1,027 - $5,751 | `mohave.gov/departments/clerk-of-the-board/over-the-counter-tax-deed-sales/` |
| **Pinal** | PDF scraper | ✅ WORKING | $7,300 - $17,250 | `treasurer.pinal.gov/special-districts.aspx` |
| **Yavapai** | PDF + GIS | ✅ WORKING | $403 - $12,934 | `yavapaiaz.gov/Mapping-and-Properties/Property-Taxes/Tax-Deed-Sales` |
| **Maricopa** | HTML scraper | ✅ WORKING | TBD | `maricopa.gov/5325/Available-for-Sale` |

### Counties That Cannot Be Automated (and Why)

| County | Website | Problem | Can It Be Fixed? |
|--------|---------|---------|------------------|
| **Apache** | `apache.az.gov` | DNS failure — site doesn't resolve. Domain may be down or restructured. | No — site is offline. Check back periodically. |
| **Coconino** | `coconino.az.gov` | Returns 403 Forbidden. Cloudflare bot protection blocks all automated requests. | Unlikely — Cloudflare blocks datacenter IPs. Would need residential proxy ($50/mo). |
| **Gila** | `gilacountyaz.gov` | Tax lien auction data is in Excel format (not deeds). No OTC deed list published online. | No — they don't publish OTC deed lists online. Only tax lien auction data. |
| **Graham** | `graham.az.gov` | Returns 403 Forbidden. Blocks automated access. | Unlikely — county uses basic bot protection. |
| **Greenlee** | `greenlee.az.gov` | Minimal website. Treasurer page exists but no tax deed list published. | No — they don't publish OTC deed lists online. |
| **La Paz** | `lapazcountyaz.gov` | DNS failure — site doesn't resolve. | No — site is offline. |
| **Navajo** | `navajo-az.gov` | DNS failure — site doesn't resolve. | No — site is offline. |
| **Pima** | `pima.gov` | Tax sale page loads but no OTC deed list published. They only do annual auctions. | No — they don't publish OTC deed lists online. |
| **Santa Cruz** | `santacruzcountyaz.gov` | Tax deed sale page requires login/registration. No public list. | No — requires account creation and manual access. |
| **Yuma** | `yumacountyaz.gov` | Has "Tax Deeded Property" page but content is blank/dynamic. No downloadable list. | Maybe — page loads but content doesn't render. Could try Playwright. |

### Why County Websites Are Hard to Scrape

1. **Cloudflare protection** — Most county sites use Cloudflare to block bots. Even Playwright with stealth patches gets blocked.
2. **DNS failures** — Several county domains (Apache, La Paz, Navajo) don't resolve at all. The domains may be expired or restructured.
3. **No OTC lists online** — Some counties (Gila, Greenlee, Pima, Santa Cruz) don't publish over-the-counter deed lists online. You have to call or visit in person.
4. **Dynamic content** — Yuma County's page loads but the content is JavaScript-rendered and doesn't appear in the HTML.
5. **Login required** — Santa Cruz County requires account access to view their deed list.

---

## arizonataxsale.com — Why It Can't Be Automated

**URL:** `https://www.arizonataxsale.com` (and county subdomains like `apache.arizonataxsale.com`)

**What it is:** The official Arizona tax lien auction platform, run by RealTaxLien/RealAuction. All 15 Arizona counties use this platform for their annual tax lien auctions.

**Why it can't be automated:**

1. **Auction-only platform** — This site is for annual tax lien auctions (held once per year, usually in February). It does NOT publish over-the-counter (OTC) tax deed lists. OTC lists are published separately by each county on their own websites.

2. **Login required** — To view any property data, you must create an account and register as a bidder. The site requires email verification and identity documentation.

3. **Session-based authentication** — Even with login, the site uses session tokens that expire quickly. Automated scraping would require maintaining valid sessions, which is unreliable.

4. **Rate limiting** — The site limits how many requests you can make per minute. Automated scraping would get IP-banned quickly.

5. **No public API** — There's no API endpoint to query properties. All data is behind the login wall.

6. **Legal restrictions** — The Terms of Service explicitly prohibit automated access and data scraping.

**Bottom line:** arizonataxsale.com is a bidding platform, not a property database. It's only active during the annual auction window (February). For year-round OTC properties, you need to check each county's own website — which is what our scraper does.

---

## OTHER BLOCKED SITES

### Akamai-Blocked (Premium real estate sites)

| Site | Block Type | Why Blocked |
|------|-----------|-------------|
| **LandWatch** | Akamai "Access Denied" | Largest land listing site. Blocks all bots. |
| **LandAndFarm** | Akamai | Sister site of LandWatch. Same protection. |
| **Homes.com** | Akamai | General real estate site. |
| **Land.com** | Akamai | Land listing aggregator. |
| **GovDeals** | Akamai | Government auction site. |

### CAPTCHA-Blocked

| Site | Block Type | Why Blocked |
|------|-----------|-------------|
| **Zillow** | CAPTCHA ("Press & Hold") | Largest real estate site. Aggressive bot detection. |
| **Trulia** | CAPTCHA | Same as Zillow (same parent company). |
| **Movoto** | CAPTCHA | Same system as Zillow. |

### Custom Bot Detection

| Site | Block Type | Why Blocked |
|------|-----------|-------------|
| **Realtor.com** | Returns empty page | Detects automation and serves blank page. |
| **Redfin** | "You might be a robot" | Custom detection system. |

### Cloudflare-Blocked

| Site | Block Type | Why Blocked |
|------|-----------|-------------|
| **Crexi** | Cloudflare JS challenge | Commercial real estate site. |
| **Coconino County** | Cloudflare JS challenge | County website. |

---

## HOW TO BYPASS ANTI-BOT SYSTEMS (If You Want to Spend Money)

### What They Check (In Order)

1. **IP Reputation** — Is this a datacenter IP or a real home IP? Datacenter = blocked immediately.
2. **TLS Fingerprint** — Does the SSL handshake match a real browser?
3. **Browser Fingerprint** — Is this a real browser or headless Chromium?
4. **Behavior Patterns** — Scroll speed, mouse movement, timing. Too fast = bot.
5. **JavaScript Environment** — Checks for automation markers.

### The Fix

| Layer | Solution | Cost |
|-------|----------|------|
| IP Reputation | Residential proxy (Bright Data, Oxylabs) | $50/mo |
| TLS Fingerprint | curl-cffi library | Free |
| Browser Fingerprint | Camoufox or playwright-stealth | Free |
| Behavior Patterns | Random delays between actions | Free |
| JavaScript Environment | Nodriver (no CDP markers) | Free |

**Total cost: ~$50/mo** to bypass Akamai, Cloudflare, and most custom detection.

### What This Would Unlock

- LandWatch, LandAndFarm, Homes.com, Land.com, GovDeals (Akamai)
- Crexi (Cloudflare)
- Coconino County (Cloudflare)

### What It Still Can't Bypass

- Zillow, Trulia, Movoto (CAPTCHA — needs human interaction)
- Realtor.com, Redfin (custom detection)
- County sites that don't publish OTC lists online

---

## THE HONEST MATH

| Approach | Cost | Sources | Listings | Worth It? |
|----------|------|---------|----------|-----------|
| **Current setup** | Free | 10 sources | ~855 listings | Yes — already finding cheapest deals |
| + Residential proxy | $50/mo | +3-5 sites | +100-200 listings | Maybe if you want LandWatch data |
| + Full bypass stack | $50/mo | +7-8 sites | +200-300 listings | Overkill for land scraping |
| Everything | $100-300/mo | All sites | All listings | Not worth it |

**The reality:** The blocked sites (LandWatch, Zillow, Realtor.com) tend to have higher-priced listings anyway. The cheapest land comes from tax deed sales, Craigslist, and government surplus — which we already scrape. You're already getting the best deals.

---

## NOT TESTED YET

| Site | URL | Notes |
|------|-----|-------|
| Yuma County Tax Deeded Property | `yumacountyaz.gov/government/treasurer/tax-deeded-property` | Page loads but content is blank. Could try Playwright to render JavaScript. |
