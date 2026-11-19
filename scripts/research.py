"""Finds a fresh angle to write about: tries recent AWS news first, falls
back to the static evergreen topic pool in config.yaml."""
import random
import xml.etree.ElementTree as ET

import requests

AWS_WHATS_NEW_FEED = "https://aws.amazon.com/about-aws/whats-new/recent/feed/"


def fetch_aws_news(limit=15):
    """Fetch recent items from AWS's official 'What's New' RSS feed."""
    resp = requests.get(
        AWS_WHATS_NEW_FEED,
        timeout=30,
        headers={"User-Agent": "reddit-aws-bot/1.0"},
    )
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for item in root.findall(".//item")[:limit]:
        title = (item.findtext("title") or "").strip()
        description = (item.findtext("description") or "").strip()
        if title:
            items.append({"title": title, "description": description})
    return items


def pick_angle(config, recent):
    """Returns (topic_label, extra_context_or_None). `recent` is a list of
    topic labels to avoid repeating."""
    recent_labels = set(recent)

    try:
        news_items = fetch_aws_news()
    except Exception as exc:  # noqa: BLE001 - fall back silently, network/feed issues happen
        print(f"Trending fetch failed, falling back to evergreen topics: {exc}")
        news_items = []

    fresh_news = [n for n in news_items if n["title"] not in recent_labels]
    if fresh_news:
        chosen = random.choice(fresh_news[:5])
        return chosen["title"], chosen["description"]

    available = [t for t in config["topics"] if t not in recent_labels]
    if not available:
        available = config["topics"]
    return random.choice(available), None
