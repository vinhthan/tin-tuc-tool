import sys

from deep_translator import MyMemoryTranslator

_translator = MyMemoryTranslator(source="en-US", target="vi-VN")


def translate_to_vietnamese(text):
    if not text:
        return text
    try:
        return _translator.translate(text)
    except Exception as exc:
        print(f"[translate] failed: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        return text
