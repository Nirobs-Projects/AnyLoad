# -*- coding: utf-8 -*-
import os
import re
import unicodedata

INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def normalize_text(text):
    if text is None:
        return ""
    if isinstance(text, bytes):
        text = text.decode("utf-8", errors="ignore")
    text = str(text)
    text = unicodedata.normalize("NFC", text)
    return text


def sanitize_filename(value):
    value = normalize_text(value)
    value = INVALID_FILENAME_CHARS.sub("_", value)
    value = value.strip().strip('.')
    return value[:255]
