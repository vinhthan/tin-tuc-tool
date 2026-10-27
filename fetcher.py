import re
import time
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

REQUEST_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (compatible; tin-tuc-tool/1.0; +https://github.com/vinhthan/tin-tuc-tool)"

FEEDS = [
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "section": "world"},
    {"name": "France24", "url": "https://www.france24.com/en/rss", "section": "world"},
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "section": "world"},
    {"name": "Sky News World", "url": "https://feeds.skynews.com/feeds/rss/world.xml", "section": "world"},
    {"name": "VnExpress Thế giới", "url": "https://vnexpress.net/rss/the-gioi.rss", "section": "world"},
    {"name": "VnExpress Thời sự", "url": "https://vnexpress.net/rss/thoi-su.rss", "section": "vietnam"},
    {"name": "Tuổi Trẻ", "url": "https://tuoitre.vn/rss/thoi-su.rss", "section": "vietnam"},
    {"name": "Thanh Niên", "url": "https://thanhnien.vn/rss/thoi-su.rss", "section": "vietnam"},
]

IMG_TAG_RE = re.compile(r'<img[^>]+src="([^"]+)"')


def _extract_image(entry):
    for key in ("media_content", "media_thumbnail"):
        media = entry.get(key)
        if media:
            url = media[0].get("url")
            if url:
                return url

    for link in entry.get("links", []):
        if str(link.get("type", "")).startswith("image/"):
            href = link.get("href")
            if href:
                return href

    for field in ("summary", "description"):
        html = entry.get(field)
        if html:
            match = IMG_TAG_RE.search(html)
            if match:
                return match.group(1)
            soup = BeautifulSoup(html, "html.parser")
            img = soup.find("img")
            if img and img.get("src"):
                return img["src"]

    return None


def _clean_summary(entry, max_len=220):
    html = entry.get("summary") or entry.get("description") or ""
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


def _parse_published(entry):
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            return datetime.fromtimestamp(time.mktime(value), tz=timezone.utc)
    return datetime.now(timezone.utc)


def fetch_feed(feed):
    try:
        resp = requests.get(
            feed["url"],
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            proxies={"http": None, "https": None},
        )
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
    except Exception as exc:
        return [], str(exc)

    articles = []
    for entry in parsed.entries:
        published = _parse_published(entry)
        articles.append({
            "title": entry.get("title", "(không có tiêu đề)").strip(),
            "link": entry.get("link", ""),
            "image": _extract_image(entry),
            "summary": _clean_summary(entry),
            "source": feed["name"],
            "section": feed["section"],
            "published_at": published.isoformat(),
        })
    return articles, None


def fetch_all():
    """Returns (articles, errors) where errors maps feed name -> error string."""
    articles = []
    errors = {}
    for feed in FEEDS:
        feed_articles, error = fetch_feed(feed)
        if error:
            errors[feed["name"]] = error
        articles.extend(feed_articles)

    articles.sort(key=lambda a: a["published_at"], reverse=True)
    return articles, errors
