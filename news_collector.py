
import json
import calendar
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser


# ==========================================
# 1. NEWS SOURCES
# ==========================================

FEEDS = {
    "Cybersecurity": [
        "https://www.bleepingcomputer.com/feed/",
        "https://www.cisa.gov/cybersecurity-advisories/all.xml",
    ],
    "Artificial Intelligence": [
        "https://openai.com/news/rss.xml",
        "https://deepmind.google/blog/rss.xml",
    ],
    "Computer Science": [
        "https://research.google/blog/rss/",
    ],
}

# Collect articles published within the last 7 days.
LOOKBACK_DAYS = 7


# ==========================================
# 2. CONVERT PUBLICATION DATE TO UTC
# ==========================================

def get_published_date(entry):
    """Return an article's publication date in UTC."""

    parsed_date = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
    )

    if parsed_date is None:
        return None

    timestamp = calendar.timegm(parsed_date)

    return datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc
    )


# ==========================================
# 3. FETCH NEWS FROM RSS FEEDS
# ==========================================

def fetch_news():
    """Fetch recent articles from all configured feeds."""

    articles = []
    seen_links = set()

    cutoff = datetime.now(timezone.utc) - timedelta(
        days=LOOKBACK_DAYS
    )

    for category, urls in FEEDS.items():

        for url in urls:
            print(f"\nReading {category}: {url}")

            try:
                feed = feedparser.parse(url)

                # Show the actual error if the feed fails.
                if feed.bozo and not feed.entries:
                    print(
                        "  Feed could not be read: "
                        f"{feed.bozo_exception}"
                    )
                    continue

                if not feed.entries:
                    print("  No articles found in this feed.")
                    continue

                source = feed.feed.get("title", url)

                for entry in feed.entries:

                    title = entry.get("title", "").strip()
                    link = entry.get("link", "").strip()

                    # Skip entries without a title or link.
                    if not title or not link:
                        continue

                    # Avoid collecting the same article twice.
                    if link in seen_links:
                        continue

                    published = get_published_date(entry)

                    # Skip articles without a usable date.
                    if published is None:
                        continue

                    # Keep only articles from the selected period.
                    if published < cutoff:
                        continue

                    seen_links.add(link)

                    article = {
                        "category": category,
                        "title": title,
                        "source": source,
                        "published": published.isoformat(),
                        "link": link,
                    }

                    articles.append(article)

                print(
                    f"  Feed processed. "
                    f"Total collected so far: {len(articles)}"
                )

            except Exception as error:
                print(f"  Error reading feed: {error}")

    # Sort newest articles first.
    articles.sort(
        key=lambda article: article["published"],
        reverse=True
    )

    return articles


# ==========================================
# 4. SAVE NEWS AS JSON
# ==========================================

def save_json(articles):
    """Save structured article data to news.json."""

    output_file = Path("news.json")

    with output_file.open("w", encoding="utf-8") as file:
        json.dump(
            articles,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(f"\nSaved structured data to {output_file.resolve()}")


# ==========================================
# 5. GENERATE A MARKDOWN NEWS BRIEFING
# ==========================================

def save_report(articles):
    """Generate a readable report containing article links."""

    today = datetime.now().strftime("%Y-%m-%d")
    output_file = Path("daily_briefing.md")

    with output_file.open("w", encoding="utf-8") as file:

        file.write(f"# Technology News Briefing — {today}\n\n")

        file.write(
            f"Collected {len(articles)} articles from "
            f"the last {LOOKBACK_DAYS} days.\n\n"
        )

        for category in FEEDS:

            file.write(f"## {category}\n\n")

            selected = [
                article
                for article in articles
                if article["category"] == category
            ]

            if not selected:
                file.write(
                    "No recent articles found, "
                    "or the configured feeds were unavailable.\n\n"
                )
                continue

            for article in selected:

                file.write(f"### {article['title']}\n\n")
                file.write(f"- Source: {article['source']}\n")
                file.write(f"- Published: {article['published']}\n")
                file.write(f"- Read article: {article['link']}\n\n")

    print(f"Saved briefing to {output_file.resolve()}")


# ==========================================
# 6. MAIN PROGRAM
# ==========================================

def main():
    print("=" * 55)
    print("       AI NEWS AGENT - NEWS COLLECTOR")
    print("=" * 55)

    print(f"\nLooking for news from the last {LOOKBACK_DAYS} days.")

    articles = fetch_news()

    save_json(articles)
    save_report(articles)

    print("\n" + "=" * 55)
    print(f"Finished! Collected {len(articles)} articles.")
    print("Output files:")
    print("  1. news.json")
    print("  2. daily_briefing.md")
    print("=" * 55)


if __name__ == "__main__":
    main()
