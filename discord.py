"""discord.py - Send alerts to Discord."""
# this file handles pushing land listing alerts into a Discord channel via webhook

import requests, time
# requests lets me make HTTP calls to the Discord API
# time is used to add small delays between messages so I don't get rate limited

from datetime import datetime
# datetime gives me access to the current time for the embed footer

from config import DISCORD_WEBHOOK
# pulls the webhook URL from my config file, keeps secrets out of the main code
from config import MAX_PRICE
# the price ceiling for Discord alerts, keeps expensive listings out of the channel


def send_alert(title, price, url, location, score, source):
    # this function builds a rich embed message and sends it to Discord
    # title is the listing name, price is the asking price, url is the listing link
    # location is where the property is, score is my match score, source is where I found it

    if not DISCORD_WEBHOOK:
        # if no webhook is configured I can't send anything, so I just print it locally
        print(f'  [NO WEBHOOK] [{score}] ${price:,.0f} - {title[:50]}')
        # this way the user still sees new listings in the terminal even without Discord
        return
        # bail out early, no point trying to post with a missing webhook URL

    if price > MAX_PRICE:
        # listings above the price ceiling don't get sent to Discord
        # they still get saved to the database, just not alerted on
        return

    color = 0x00ff00 if score >= 70 else 0xffff00 if score >= 50 else 0xff9900
    # the embed border color changes based on how good the match is
    # green for great scores, yellow for decent, orange for lower scores

    embed = {
        # building the Discord embed object that shows up as a rich message card
        'title': f'[{score}/100] ${price:,.0f} - {title[:75]}',
        # the title shows the score, price, and first 75 chars of the listing name
        'url': url, 'color': color,
        # clicking the title takes you straight to the original listing
        # color sets the left border color on the embed
        'fields': [
            # fields are the structured info blocks that show up in the embed
            {'name': 'Location', 'value': location or 'AZ', 'inline': True},
            # shows the property location, falls back to AZ if nothing is provided
            {'name': 'Source', 'value': source, 'inline': True},
            # shows where the listing was found, like Zillow or Redfin
        ],
        'footer': {'text': f'Found {datetime.now().strftime("%m/%d %I:%M %p")}'}
        # the footer stamps when this alert was sent so I know how fresh it is
    }

    try:
        # wrapping in try/except because Discord API calls can fail for all sorts of reasons
        resp = requests.post(DISCORD_WEBHOOK, json={'embeds': [embed]}, timeout=10)
        # sends the embed to the Discord webhook as JSON, gives up after 10 seconds
        if resp.status_code == 204:
            # 204 means Discord accepted the message with no issues
            print(f'  [{score}] ${price:,.0f} - {title[:50]}')
            # prints a quick summary to the terminal so I can see it was sent fine
        elif resp.status_code == 429:
            # 429 is Discord telling me I'm sending too many messages too fast
            time.sleep(resp.json().get('retry_after', 2) + 0.5)
            # waits the amount of time Discord asks for, plus a small buffer to be safe
            requests.post(DISCORD_WEBHOOK, json={'embeds': [embed]}, timeout=10)
            # retries sending the same embed after waiting

    except: pass
    # if anything else goes wrong, network timeout, JSON parse error, whatever, just move on
    # the listing isn't worth crashing the whole scraper over

    time.sleep(1.5)
    # always wait 1.5 seconds between messages to stay under Discord's rate limit
    # this keeps the bot running smoothly even with lots of listings
