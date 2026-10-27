import os
from datetime import datetime, timedelta, timezone

from flask import Flask, abort, render_template

import storage
from fetcher import fetch_all
from scheduler import start as start_scheduler

app = Flask(__name__)

REFRESH_INTERVAL = timedelta(hours=1)


def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def refresh_today_if_stale():
    date_str = today_str()
    existing = storage.load_day(date_str)
    if existing:
        fetched_at = datetime.fromisoformat(existing["fetched_at"])
        if datetime.now(timezone.utc) - fetched_at < REFRESH_INTERVAL:
            return existing
    articles, errors = fetch_all()
    return storage.save_day(date_str, articles, errors)


def split_sections(articles):
    world = [a for a in articles if a.get("section") == "world"]
    vietnam = [a for a in articles if a.get("section") == "vietnam"]
    return world, vietnam


@app.route("/")
def index():
    day_data = refresh_today_if_stale()
    world, vietnam = split_sections(day_data["articles"])
    dates = storage.list_available_dates()
    return render_template(
        "index.html",
        world=world,
        vietnam=vietnam,
        fetched_at=day_data["fetched_at"],
        errors=day_data.get("errors") or {},
        dates=dates,
        selected_date=today_str(),
    )


@app.route("/day/<date_str>")
def day_view(date_str):
    day_data = storage.load_day(date_str)
    if not day_data:
        abort(404)
    world, vietnam = split_sections(day_data["articles"])
    dates = storage.list_available_dates()
    return render_template(
        "index.html",
        world=world,
        vietnam=vietnam,
        fetched_at=day_data["fetched_at"],
        errors=day_data.get("errors") or {},
        dates=dates,
        selected_date=date_str,
    )


if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
    start_scheduler(refresh_today_if_stale)


if __name__ == "__main__":
    app.run(debug=True)
