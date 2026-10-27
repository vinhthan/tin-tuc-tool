import sys
import time

from deep_translator import MyMemoryTranslator
from deep_translator.exceptions import TooManyRequests

_translator = MyMemoryTranslator(source="en-US", target="vi-VN")

MAX_RETRIES = 4
RETRY_DELAY_SECONDS = 2
MIN_CALL_INTERVAL_SECONDS = 1.1

_last_call_at = 0.0


def _throttle():
    global _last_call_at
    elapsed = time.monotonic() - _last_call_at
    wait = MIN_CALL_INTERVAL_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def translate_to_vietnamese(text):
    if not text:
        return text
    for attempt in range(MAX_RETRIES):
        _throttle()
        try:
            return _translator.translate(text)
        except TooManyRequests:
            if attempt == MAX_RETRIES - 1:
                print("[translate] gave up after rate limiting", file=sys.stderr, flush=True)
                return text
            time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
        except Exception as exc:
            print(f"[translate] failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            return text
    return text
