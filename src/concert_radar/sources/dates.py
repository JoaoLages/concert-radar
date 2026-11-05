"""Reads the Portuguese date lines venue sites print on their event cards."""

import re
from datetime import date

from concert_radar.matching import normalize

_MONTHS = [
    "jan",
    "fev",
    "mar",
    "abr",
    "mai",
    "jun",
    "jul",
    "ago",
    "set",
    "out",
    "nov",
    "dez",
]
_TIME = re.compile(r"\b\d{1,2}[:h]\d{2}\b")
# A day, optionally followed by its month (abbreviated or in full) and year.
_DAY = re.compile(
    rf"\b(\d{{1,2}})(?:\s+({'|'.join(_MONTHS)})[a-z]*)?(?:\s+(\d{{4}}))?\b"
)


def portuguese_dates(text: str) -> list[date]:
    """Every day mentioned, e.g. "20 E 21 NOV 2026", "19 dezembro 2026 a 20 dezembro 2026" or
    "04 junho 2027 | 11:00 - 06 junho 2027 | 20:00". A day without its own month or year takes
    the next one given; times are ignored."""
    days = [list(m.groups()) for m in _DAY.finditer(_TIME.sub(" ", normalize(text)))]
    month, year = None, None
    for day in reversed(days):
        month = day[1] = day[1] or month
        year = day[2] = day[2] or year
    if not days or not all(month and year for _, month, year in days):
        raise ValueError(f"Date not understood: {text!r}")
    return [
        date(int(year), _MONTHS.index(month) + 1, int(day)) for day, month, year in days
    ]


def next_portuguese_day(text: str, today: date) -> date:
    """A day and abbreviated month with no year, e.g. "08 JUL", as its next date from today."""
    match = re.search(rf"\b(\d{{1,2}})\s+({'|'.join(_MONTHS)})", normalize(text))
    if not match:
        raise ValueError(f"Date not understood: {text!r}")
    day = date(today.year, _MONTHS.index(match[2]) + 1, int(match[1]))
    return day if day >= today else day.replace(year=today.year + 1)
