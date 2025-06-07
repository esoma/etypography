from __future__ import annotations

__all__ = ["character_is_normally_rendered"]

from unicodedata import category as unicode_category


def character_is_normally_rendered(character: str) -> bool:
    # http://www.unicode.org/reports/tr44/#GC_Values_Table
    return unicode_category(character)[0] not in "CZ"
