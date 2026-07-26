"""
Booking.com Room Price Scraper — Lisbon & Algarve
----------------------------------------------------
Two-stage scraper:
  1. Search booking.com (sorted by popularity = "most booked") for a
     destination, collect the top N hotel detail-page links.
  2. Visit each hotel page and extract every room type + price from
     the room rate table.

Built from selectors confirmed against a LIVE session (not guessed):
  - Search results sorted via sr_order=popularity
  - Room rows identified via tr[id^="room_type_id_"]
  - Price text contains "Rp" (IDR) — adjust CURRENCY_REGEX if your
    session shows a different currency (e.g. EUR, USD).

IMPORTANT:
  - Run this on your local machine with full internet access.
  - The "aid" affiliate id is kept from your working session — if the
    site blocks requests again, try re-capturing a fresh aid/label via
    codegen (Kayak referral links tend to work better than direct
    booking.com search).
  - Selectors CAN still shift over time. If something breaks, re-run
    `playwright codegen <url>` on the specific page that fails and
    update the relevant selector below.
"""

import csv
import random
import re
import time
from datetime import date, timedelta
from playwright.sync_api import sync_playwright

CITIES = {
    "Lisbon": "Lisbon, Portugal",
    "Algarve": "Algarve, Portugal",
}

HOTELS_PER_CITY = 30
AFFILIATE_ID = "842265"  # change if it stops working

today = date.today()
checkin = today + timedelta(days=14)
checkout = checkin + timedelta(days=1)  # 1-night search
CHECKIN_STR = checkin.strftime("%Y-%m-%d")
CHECKOUT_STR = checkout.strftime("%Y-%m-%d")

ADULTS = 2
OUTPUT_CSV = "hotel_room_prices.csv"

SEARCH_URL_TEMPLATE = (
    "https://www.booking.com/searchresults.html"
    "?ss={destination}"
    "&checkin={checkin}&checkout={checkout}"
    "&group_adults={adults}&no_rooms=1&group_children=0"
    "&sb=1&src_elem=sb&src=searchresults"
    "&sr_order=popularity" 
    "&lang=en-us&aid={aid}"
)

CURRENCY_REGEX = re.compile(r"(?:Rp|€|\$|EUR|USD)[\s.,\d]+") 


def polite_wait(a=2.0, b=4.5):
    time.sleep(random.uniform(a, b))


def parse_price(text):
    """Extract numeric price from strings like 'Rp 3,166,772'."""
    if not text:
        return None
    match = CURRENCY_REGEX.search(text)
    if not match:
        return None
    digits = re.sub(r"[^\d]", "", match.group())
    return float(digits) if digits else None


def dismiss_popups(page):
    """Close cookie banner and sign-in nag if they appear. Safe to call
    even if neither is present."""
    try:
        page.click("#onetrust-accept-btn-handler", timeout=4000)
    except Exception:
        pass

    for selector in [
        "button[aria-label='Dismiss sign-in info.']",
        "button[aria-label*='Dismiss']",
        "[data-testid='header-signin-modal'] button[aria-label*='close' i]",
    ]:
        try:
            page.click(selector, timeout=4000)
            break
        except Exception:
            continue



# STAGE 1: Get top N hotel links from search results
def get_top_hotel_links(page, city_label, destination, limit=HOTELS_PER_CITY):
    url = SEARCH_URL_TEMPLATE.format(
        destination=destination.replace(" ", "+"),
        checkin=CHECKIN_STR,
        checkout=CHECKOUT_STR,
        adults=ADULTS,
        aid=AFFILIATE_ID,
    )
    print(f"[{city_label}] Navigating to search results...")
    page.goto(url, timeout=60000)
    page.wait_for_timeout(3000)
    dismiss_popups(page)
    page.wait_for_timeout(1000)

    # Scroll a few times to trigger lazy-loaded cards
    for _ in range(4):
        page.mouse.wheel(0, 2000)
        page.wait_for_timeout(800)

    # Match any link to a hotel detail page
    anchors = page.query_selector_all("a[href*='/hotel/pt/']")

    seen = set()
    links = []
    for a in anchors:
        href = a.get_attribute("href")
        if not href:
            continue
        # strip tracking fragment duplicates by keeping full href
        base_key = href.split("?")[0]
        if base_key in seen:
            continue
        seen.add(base_key)
        links.append(href if href.startswith("http") else f"https://www.booking.com{href}")
        if len(links) >= limit:
            break

    print(f"[{city_label}] Found {len(links)} unique hotel links.")

    if len(links) == 0:
        try:
            page.screenshot(path=f"debug_search_{city_label}.png", full_page=True)
            with open(f"debug_search_{city_label}.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print(f"  Saved debug_search_{city_label}.png and .html for inspection")
        except Exception as debug_err:
            print(f"  Could not save debug artifacts: {debug_err}")

    return links


# STAGE 2: Visit a hotel page and extract room types + prices
def get_hotel_name(page):
    try:
        title = page.title()
        return title.split(" - ")[0].strip()
    except Exception:
        return "Unknown"


def get_room_prices(page, hotel_url):
    rooms = []
    hotel_name = "Unknown"
    try:
        page.goto(hotel_url, timeout=60000)
        page.wait_for_timeout(2500)
        dismiss_popups(page)
        hotel_name = get_hotel_name(page)

        # Scroll down to trigger any lazy-loaded room table before waiting
        for _ in range(4):
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(600)

        # Check for sold-out / no-availability state first — this is a
        # different failure mode than "selector broke" and common for
        # small guesthouses/apartments on popular dates.
        page_text = page.inner_text("body")
        if re.search(r"sold out|no rooms available|not available for these dates", page_text, re.I):
            print("  INFO: property appears sold out for these dates — skipping.")
            return hotel_name, rooms

        # Confirmed from live HTML inspection: room name lives in
        # a.hprt-roomtype-link, price lives in td.hprt-table-cell-price
        # (both are stable literal classes, unlike the ARIA role attrs
        # which are computed by the browser and don't exist in raw HTML).
        try:
            page.wait_for_selector("a.hprt-roomtype-link", timeout=15000)
        except Exception:
            print("  WARNING: room table not found — selector may need updating.")
            safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", hotel_name)[:40]
            try:
                page.screenshot(path=f"debug_{safe_name}.png", full_page=True)
                with open(f"debug_{safe_name}.html", "w", encoding="utf-8") as f:
                    f.write(page.content())
                print(f"  Saved debug_{safe_name}.png and .html for inspection")
            except Exception as debug_err:
                print(f"  Could not save debug artifacts: {debug_err}")
            return hotel_name, rooms

        room_links = page.query_selector_all("a.hprt-roomtype-link")

        for link in room_links:
            room_type = link.inner_text().strip()

            row = link.evaluate_handle("el => el.closest('tr')")
            row_el = row.as_element()
            if row_el is None:
                continue

            price_el = row_el.query_selector(".hprt-table-cell-price .bui-price-display__value")
            if price_el is None:
                # fallback: any price-looking text within the price cell
                price_cell = row_el.query_selector(".hprt-table-cell-price")
                price_text = price_cell.inner_text() if price_cell else ""
            else:
                price_text = price_el.inner_text()

            price = parse_price(price_text)

            if room_type and price:
                rooms.append({"room_type_name": room_type, "price": price})

        return hotel_name, rooms

    except Exception as e:
        print(f"  ERROR scraping hotel page: {e}")
        return hotel_name, rooms


def main():
    all_rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for city_label, destination in CITIES.items():
            links = get_top_hotel_links(page, city_label, destination)

            for i, link in enumerate(links, 1):
                print(f"  [{city_label}] ({i}/{len(links)}) Scraping: {link[:80]}...")
                hotel_name, rooms = get_room_prices(page, link)

                if not rooms:
                    all_rows.append({
                        "city": city_label,
                        "hotel_name": hotel_name,
                        "room_type_name": None,
                        "price": None,
                        "checkin": CHECKIN_STR,
                        "checkout": CHECKOUT_STR,
                        "url": link,
                    })
                else:
                    for r in rooms:
                        all_rows.append({
                            "city": city_label,
                            "hotel_name": hotel_name,
                            "room_type_name": r["room_type_name"],
                            "price": r["price"],
                            "checkin": CHECKIN_STR,
                            "checkout": CHECKOUT_STR,
                            "url": link,
                        })

                polite_wait(2.5, 5)

        browser.close()

    fieldnames = ["city", "hotel_name", "room_type_name", "price", "checkin", "checkout", "url"]
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nDone. Saved {len(all_rows)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()