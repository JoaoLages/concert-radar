"""MEO Arena (arena.meo.pt): the venue's full agenda. Most of its shows sell through Blueticket,
which can't be read directly, so the venue's own page is how they get in."""

import re
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from concert_radar.models import Country, Listing, Source

_BASE_URL = "https://arena.meo.pt"
_MONTHS = [
    "JAN",
    "FEV",
    "MAR",
    "ABR",
    "MAI",
    "JUN",
    "JUL",
    "AGO",
    "SET",
    "OUT",
    "NOV",
    "DEZ",
]
# A day, optionally followed by its month and year: "20 E 21 NOV 2026" or "30 NOV E 01 DEZ 2026".
_DAY = re.compile(rf"\b(\d{{1,2}})(?:\s+({'|'.join(_MONTHS)}))?(?:\s+(\d{{4}}))?\b")


def _dates(text: str) -> list[date]:
    """Every day in a card's date line; a day without its own month or year takes the next one given."""
    days = [list(m.groups()) for m in _DAY.finditer(text.upper())]
    month, year = None, None
    for day in reversed(days):
        month = day[1] = day[1] or month
        year = day[2] = day[2] or year
    if not days or not all(month and year for _, month, year in days):
        raise ValueError(f"MEO Arena date not understood: {text!r}")
    return [
        date(int(year), _MONTHS.index(month) + 1, int(day)) for day, month, year in days
    ]


def listings(client: httpx.Client) -> list[Listing]:
    response = client.get(f"{_BASE_URL}/agenda-completa")
    response.raise_for_status()
    found: list[Listing] = []
    for card in BeautifulSoup(response.text, "html.parser").select(
        ".agendaDestaquesUn"
    ):
        link = card.select_one("a.destaquesNome")
        when = card.select_one(".destaquesData")
        if not isinstance(link, Tag) or not isinstance(when, Tag):
            raise TypeError(f"MEO Arena event without a name or date: {card}")
        found += [
            Listing(
                source=Source.MEO_ARENA,
                title=link.get_text(" ", strip=True),
                performers=[],
                starts_on=day,
                venue="MEO Arena",
                city="Lisboa",
                country=Country.PORTUGAL,
                url=_BASE_URL + str(link["href"]),
            )
            for day in _dates(when.get_text(" ", strip=True))
        ]
    return found
