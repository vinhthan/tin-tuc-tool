import base64
import json
import os
from datetime import datetime, timezone

import requests

GITHUB_API = "https://api.github.com"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # "owner/repo"
DATA_DIR = "data"
LOCAL_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

USE_GITHUB = bool(GITHUB_TOKEN and GITHUB_REPO)


def _headers():
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def _github_path(date_str):
    return f"{DATA_DIR}/{date_str}.json"


def _github_get_file(date_str):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{_github_path(date_str)}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    if resp.status_code == 404:
        return None, None
    resp.raise_for_status()
    body = resp.json()
    content = base64.b64decode(body["content"]).decode("utf-8")
    return json.loads(content), body["sha"]


def _github_put_file(date_str, payload, sha):
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{_github_path(date_str)}"
    data = {
        "message": f"update {date_str} news data",
        "content": base64.b64encode(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")).decode("ascii"),
    }
    if sha:
        data["sha"] = sha
    resp = requests.put(url, headers=_headers(), json=data, timeout=10)
    resp.raise_for_status()


def _github_list_dates():
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{DATA_DIR}"
    resp = requests.get(url, headers=_headers(), timeout=10)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    names = [item["name"] for item in resp.json() if item["name"].endswith(".json")]
    return sorted(name[:-5] for name in names)


def _local_file(date_str):
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    return os.path.join(LOCAL_DATA_DIR, f"{date_str}.json")


def _local_get_file(date_str):
    path = _local_file(date_str)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _local_put_file(date_str, payload):
    path = _local_file(date_str)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _local_list_dates():
    os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
    names = [n for n in os.listdir(LOCAL_DATA_DIR) if n.endswith(".json")]
    return sorted(name[:-5] for name in names)


def load_day(date_str):
    """Returns dict {fetched_at, articles, errors} or None if not found."""
    if USE_GITHUB:
        data, _sha = _github_get_file(date_str)
        return data
    return _local_get_file(date_str)


def save_day(date_str, articles, errors):
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
        "errors": errors,
    }
    if USE_GITHUB:
        _existing, sha = _github_get_file(date_str)
        _github_put_file(date_str, payload, sha)
    else:
        _local_put_file(date_str, payload)
    return payload


def list_available_dates():
    dates = _github_list_dates() if USE_GITHUB else _local_list_dates()
    return sorted(dates, reverse=True)
