import requests
from bs4 import BeautifulSoup
import time
import os

# ── Configuration ────────────────────────────────────────────────
LETTERBOXD_USERNAME = "kaveh333"
WATCHMODE_API_KEY   = os.environ.get("WATCHMODE_API_KEY", "YOUR_API_KEY_HERE")

PLATFORMS = {
    "netflix":     "Netflix",
    "hulu":        "Hulu",
    "prime":       "Amazon Prime Video",
    "peacock":     "Peacock",
    "paramount":   "Paramount+",
    "disney":      "Disney+",
    "hbo":         "Max (HBO)",
    "apple":       "Apple TV+",
}

# ── Step 1: Scrape Letterboxd watchlist ──────────────────────────
def get_watchlist(username):
    movies = []
    page = 1
    print(f"Scraping Letterboxd watchlist for '{username}'...")

    while True:
        url = f"https://letterboxd.com/{username}/watchlist/page/{page}/"
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})

        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "lxml")
        items = soup.select("div.film-poster")

        if not items:
            break

        for item in items:
            img   = item.select_one("img")
            title = img.get("alt", "Unknown") if img else "Unknown"
            year  = ""
            movies.append({"title": title, "year": year})

        print(f"  Page {page}: found {len(items)} movies")
        page += 1
        time.sleep(1)  # be polite — don't hammer their server

    print(f"Total movies found: {len(movies)}\n")
    return movies

# ── Step 2: Search Watchmode for a movie's ID ────────────────────
def search_watchmode(title, year, api_key):
    url = "https://api.watchmode.com/v1/search/"
    params = {
        "apiKey":       api_key,
        "search_field": "name",
        "search_value": title,
        "types":        "movie",
    }
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return None

    results = response.json().get("title_results", [])
    for r in results:
        if year and str(r.get("year", "")) == str(year):
            return r["id"]
    if results:
        return results[0]["id"]
    return None

# ── Step 3: Get streaming sources for a Watchmode title ID ───────
def get_streaming_sources(watchmode_id, api_key):
    url = f"https://api.watchmode.com/v1/title/{watchmode_id}/sources/"
    params = {"apiKey": api_key, "regions": "US"}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        return []
    return response.json()

# ── Step 4: Match sources to our platform list ───────────────────
def match_platforms(sources):
    matched = set()
    for source in sources:
        if source.get("type") != "sub":   # "sub" = subscription (not rent/buy)
            continue
        name = source.get("name", "").lower()
        for key, label in PLATFORMS.items():
            if key in name:
                matched.add(label)
    return matched

# ── Step 5: Put it all together and print results ────────────────
def main():
    movies  = get_watchlist(LETTERBOXD_USERNAME)
    results = {label: [] for label in PLATFORMS.values()}
    results["Not Found on Major Platforms"] = []

    total = len(movies)
    for i, movie in enumerate(movies, 1):
        title, year = movie["title"], movie["year"]
        print(f"[{i}/{total}] Checking: {title} ({year})")

        watchmode_id = search_watchmode(title, year, WATCHMODE_API_KEY)
        if not watchmode_id:
            results["Not Found on Major Platforms"].append(f"{title} ({year})")
            time.sleep(0.5)
            continue

        sources  = get_streaming_sources(watchmode_id, WATCHMODE_API_KEY)
        platforms = match_platforms(sources)

        if platforms:
            for p in platforms:
                results[p].append(f"{title} ({year})")
        else:
            results["Not Found on Major Platforms"].append(f"{title} ({year})")

        time.sleep(0.5)  # stay within API rate limits

    # ── Print final report ───────────────────────────────────────
    print("\n" + "═"*50)
    print("  STREAMING AVAILABILITY REPORT")
    print("═"*50)
    for platform, movie_list in results.items():
        if movie_list:
            print(f"\n{platform} ({len(movie_list)} movies):")
            for m in sorted(movie_list):
                print(f"  • {m}")

    not_found = results["Not Found on Major Platforms"]
    print(f"\n{'═'*50}")
    print(f"Checked {total} movies total.")
    print(f"{total - len(not_found)} available on at least one platform.")
    print(f"{len(not_found)} not found on any of the 8 platforms.")

if __name__ == "__main__":
    main()