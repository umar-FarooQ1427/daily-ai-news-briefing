
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

NEWS_FILE = Path("news.json")
OUTPUT_FILE = Path("ai_briefing.md")

API_URL = "https://openrouter.ai/api/v1/chat/completions"
API_KEY = os.getenv("OPENROUTER_API_KEY", "").strip()
MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

MAX_ARTICLES = 10


def load_articles():
    if not NEWS_FILE.exists():
        raise RuntimeError("news.json not found. Run news_collector.py first.")

    with NEWS_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        articles = data
    elif isinstance(data, dict):
        articles = data.get("articles", [])
        if isinstance(articles, dict):
            articles = [
                item
                for group in articles.values()
                if isinstance(group, list)
                for item in group
            ]
    else:
        raise RuntimeError("Unsupported news.json format.")

    if not isinstance(articles, list):
        raise RuntimeError("Invalid articles format in news.json.")

    return articles


def analyze_article(article):
    title = article.get("title", "Untitled")
    category = article.get("category", "Unknown")
    source = article.get("source", "Unknown")
    description = article.get("description") or article.get("summary") or ""

    prompt = f"""
Analyze this news article using only the supplied information.

Title: {title}
Category: {category}
Source: {source}
RSS description: {description}

Provide these sections:

Summary:
Write 2-3 clear sentences.

Why it matters:
Explain the significance for cybersecurity, AI, or computer science.

Importance:
Give a score from 1 to 5 with a brief explanation.

Confidence:
State High, Medium, or Low and explain why.

Important rules:
- Do not invent facts.
- If only a headline is available, acknowledge limited context.
- Do not claim to have read the full article.
- Keep the analysis concise.
"""

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/umar-FarooQ1427/daily-ai-news-briefing",
            "X-Title": "Daily AI News Briefing",
        },
        json={
            "model": MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a careful technology news analyst.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.3,
            "max_tokens": 550,
        },
        timeout=90,
    )

    if response.status_code != 200:
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text[:300]

        raise RuntimeError(
            f"OpenRouter HTTP {response.status_code}: {detail}"
        )

    data = response.json()
    choices = data.get("choices") or []

    if not choices:
        raise RuntimeError("OpenRouter returned no choices.")

    content = choices[0].get("message", {}).get("content", "")

    if isinstance(content, list):
        content = "\n".join(
            part.get("text", "")
            for part in content
            if isinstance(part, dict)
        )

    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("OpenRouter returned an empty analysis.")

    return content.strip()


def main():
    print("=" * 55)
    print("AI NEWS AGENT - OPENROUTER ANALYZER")
    print(f"Model: {MODEL}")
    print("=" * 55)

    if not API_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing from environment variables."
        )

    if MODEL != "openrouter/free" and not MODEL.endswith(":free"):
        raise RuntimeError(
            "Only openrouter/free or models ending in :free are allowed."
        )

    articles = load_articles()
    selected = articles[:MAX_ARTICLES]

    print(f"Loaded {len(articles)} articles.")
    print(f"Analyzing {len(selected)} articles.")

    if not selected:
        raise RuntimeError("No articles available for analysis.")

    report = [
        f"# AI Technology News Briefing - {datetime.now(timezone.utc):%Y-%m-%d}",
        "",
        f"AI engine: OpenRouter ({MODEL})",
        "",
        f"AI analyzed {len(selected)} of {len(articles)} collected articles.",
        "",
    ]

    for index, article in enumerate(selected, start=1):
        title = article.get("title", "Untitled")
        category = article.get("category", "Unknown")
        source = article.get("source", "Unknown")
        link = article.get("link") or article.get("url", "")

        print(f"Analyzing {index}/{len(selected)}: {title}", flush=True)

        analysis = analyze_article(article)

        report.extend([
            f"## {index}. {title}",
            "",
            f"- **Category:** {category}",
            f"- **Source:** {source}",
            "",
            analysis,
            "",
        ])

        if link.startswith(("https://", "http://")):
            report.extend([
                f"[Read original article]({link})",
                "",
            ])

        report.extend(["---", ""])

        if index < len(selected):
            time.sleep(2)

    OUTPUT_FILE.write_text(
        "\n".join(report),
        encoding="utf-8",
    )

    print(f"Saved {OUTPUT_FILE} successfully.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, requests.RequestException, ValueError) as error:
        print(f"[ERROR] {error}", file=sys.stderr)
        sys.exit(1)
