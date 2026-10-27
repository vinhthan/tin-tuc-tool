from apscheduler.schedulers.background import BackgroundScheduler

_scheduler = None


def start(refresh_func):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(refresh_func, "interval", hours=1, id="refresh_news", next_run_time=None)
    _scheduler.start()
    return _scheduler
