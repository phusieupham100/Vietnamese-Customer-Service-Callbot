"""Text normalization helpers for vehicle model matching."""

from __future__ import annotations

import re
import unicodedata


_PUNCTUATION_RE = re.compile(r"[^0-9a-zA-ZÀ-ỹ]+")
_SPACE_RE = re.compile(r"\s+")


def strip_vietnamese_accents(text: str) -> str:
    """Return text without Vietnamese diacritics for accent-insensitive matching."""
    normalized = unicodedata.normalize("NFD", text)
    without_marks = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return without_marks.replace("đ", "d").replace("Đ", "D")


def normalize_vehicle_text(text: str) -> str:
    """Normalize text for vehicle matching while preserving meaningful digits."""
    lowered = text.strip().lower()
    lowered = lowered.replace("–", "-").replace("—", "-")
    lowered = strip_vietnamese_accents(lowered)
    lowered = _PUNCTUATION_RE.sub(" ", lowered)
    lowered = _SPACE_RE.sub(" ", lowered).strip()
    return lowered


def compact_vehicle_text(text: str) -> str:
    """Return normalized text with spaces removed for variants like VF8/VF 8."""
    return normalize_vehicle_text(text).replace(" ", "")

