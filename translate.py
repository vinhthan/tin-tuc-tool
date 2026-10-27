import sys
import time

from deep_translator import MyMemoryTranslator
from deep_translator.exceptions import TooManyRequests

_translator = MyMemoryTranslator(source="en-US", target="vi-VN", email="vinhtm1@fpt.com")

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1
MIN_CALL_INTERVAL_SECONDS = 1.1
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 300

_last_call_at = 0.0
_circuit_open_until = 0.0


def _throttle():
    global _last_call_at
    elapsed = time.monotonic() - _last_call_at
    wait = MIN_CALL_INTERVAL_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_call_at = time.monotonic()


def translate_to_vietnamese(text):
    global _circuit_open_until
    if not text:
        return text
    if time.monotonic() < _circuit_open_until:
        return text
    for attempt in range(MAX_RETRIES):
        _throttle()
        try:
            return _translator.translate(text)
        except TooManyRequests:
            if attempt == MAX_RETRIES - 1:
                _circuit_open_until = time.monotonic() + CIRCUIT_BREAKER_COOLDOWN_SECONDS
                print(
                    f"[translate] rate limited, pausing translation for {CIRCUIT_BREAKER_COOLDOWN_SECONDS}s",
                    file=sys.stderr, flush=True,
                )
                return text
            time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))
        except Exception as exc:
            print(f"[translate] failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            return text
    return text


SEPARATOR = "\n<<<SEP>>>\n"


def translate_title_and_summary(title, summary):
    """Translate both fields in a single API call to cut request count in half."""
    if not title and not summary:
        return title, summary
    combined = translate_to_vietnamese(f"{title}{SEPARATOR}{summary}")
    if SEPARATOR not in combined:
        return translate_to_vietnamese(title), translate_to_vietnamese(summary)
    new_title, new_summary = combined.split(SEPARATOR, 1)
    return new_title.strip(), new_summary.strip()
