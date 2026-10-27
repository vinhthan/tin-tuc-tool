import html
import re
import time
from datetime import datetime, timezone

import feedparser
import requests
from bs4 import BeautifulSoup

from translate import translate_title_and_summary

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

ENGLISH_SOURCES = {"Al Jazeera", "France24", "BBC World", "Sky News World"}

IMG_TAG_RE = re.compile(r'<img[^>]+src="([^"]+)"')

CONFLICT_KEYWORDS = [
    "war", "warfare", "attack", "attacked", "strike", "strikes", "airstrike",
    "air strike", "missile", "missiles", "rocket", "bomb", "bombing", "bombed",
    "explosion", "explode", "shell", "shelling", "kill", "killed", "killing",
    "dead", "death", "deaths", "casualt", "wounded", "injured", "troops",
    "military", "invasion", "invade", "offensive", "ceasefire", "truce",
    "conflict", "clash", "clashes", "shoot", "shooting", "shot", "gunfire",
    "assault", "terror", "terrorist", "hostage", "hostages", "nuclear",
    "coup", "uprising", "rebel", "rebels", "insurgent", "genocide", "massacre",
    "siege", "blockade", "drone strike", "artillery", "soldier", "soldiers",
    "warplane", "warship", "evacuate", "evacuation", "refugee", "refugees",
    "crisis", "sanctions", "nguy cơ", "escalation",
    "chiến tranh", "chiến sự", "tấn công", "tên lửa", "rốc két", "bom",
    "đánh bom", "nổ", "giết", "chết", "tử vong", "thương vong", "bị thương",
    "quân đội", "xung đột", "đụng độ", "nổ súng", "bạo loạn", "khủng bố",
    "con tin", "hạt nhân", "đảo chính", "nổi dậy", "phiến quân", "diệt chủng",
    "thảm sát", "bao vây", "pháo kích", "binh sĩ", "sơ tán", "tị nạn",
    "khủng hoảng", "trừng phạt", "leo thang", "ngừng bắn", "xâm lược",
]

_KEYWORD_PATTERNS = [
    (kw, re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE))
    for kw in CONFLICT_KEYWORDS
]


def compute_drama_score(title, summary):
    score = 0
    title_lower = title or ""
    summary_lower = summary or ""
    for _kw, pattern in _KEYWORD_PATTERNS:
        if pattern.search(title_lower):
            score += 3
        if pattern.search(summary_lower):
            score += 1
    return score


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

    is_english = feed["name"] in ENGLISH_SOURCES
    articles = []
    for entry in parsed.entries:
        published = _parse_published(entry)
        title = html.unescape(entry.get("title", "(không có tiêu đề)")).strip()
        summary = _clean_summary(entry)
        articles.append({
            "title": title,
            "summary": summary,
            "link": entry.get("link", ""),
            "image": _extract_image(entry),
            "source": feed["name"],
            "section": feed["section"],
            "published_at": published.isoformat(),
            "drama_score": compute_drama_score(title, summary),
            "needs_translation": is_english,
        })
    return articles, None


WORLD_LIMIT = 15
VIETNAM_LIMIT = 5


def _rank_key(article):
    return (article["drama_score"], article["published_at"])


def fetch_all():
    """Returns (articles, errors) where errors maps feed name -> error string."""
    articles = []
    errors = {}
    for feed in FEEDS:
        feed_articles, error = fetch_feed(feed)
        if error:
            errors[feed["name"]] = error
        articles.extend(feed_articles)

    world = sorted(
        (a for a in articles if a["section"] == "world"),
        key=_rank_key,
        reverse=True,
    )[:WORLD_LIMIT]
    vietnam = sorted(
        (a for a in articles if a["section"] == "vietnam"),
        key=_rank_key,
        reverse=True,
    )[:VIETNAM_LIMIT]

    selected = world + vietnam
    for article in selected:
        if article.pop("needs_translation", False):
            article["title"], article["summary"] = translate_title_and_summary(
                article["title"], article["summary"]
            )

    return selected, errors
