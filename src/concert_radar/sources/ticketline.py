"""Ticketline (ticketline.pt): music and festival searches, one month at a time."""

from datetime import date
from enum import IntEnum

import httpx
from bs4 import BeautifulSoup, Tag

from concert_radar.models import Country, Listing, Source

_BASE_URL = "https://www.ticketline.pt"


class _Category(IntEnum):
    MUSIC = 104
    FESTIVALS = 121


def _text(item: Tag, prop: str) -> str:
    found = item.select_one(f'[itemprop="{prop}"]')
    if not isinstance(found, Tag):
        raise TypeError(f"Ticketline event without {prop}: {item}")
    return found.get_text(" ", strip=True)


def _listing(item: Tag) -> Listing:
    link = item.select_one('a[itemprop="url"]')
    start = item.select_one('[itemprop="startDate"]')
    if not isinstance(link, Tag) or not isinstance(start, Tag):
        raise TypeError(f"Ticketline event without a link or date: {item}")
    return Listing(
        source=Source.TICKETLINE,
        title=_text(item, "name"),
        performers=[],
        starts_on=date.fromisoformat(str(start["content"])),
        venue=_text(item, "location"),
        city="",
        country=Country.PORTUGAL,
        url=_BASE_URL + str(link["href"]),
    )


def listings(client: httpx.Client, today: date, months: int) -> list[Listing]:
    """Events starting in the next `months` months; an event with several dates is listed once."""
    by_url: dict[str, Listing] = {}
    for category in _Category:
        for offset in range(months):
            year, month_index = divmod(today.year * 12 + today.month - 1 + offset, 12)
            month = month_index + 1
            page = 1
            while True:
                response = client.get(
                    f"{_BASE_URL}/pesquisa/",
                    params={
                        "category": category,
                        "month": month,
                        "year": year,
                        "page": page,
                    },
                )
                response.raise_for_status()
                items = BeautifulSoup(response.text, "html.parser").find_all(
                    "li", attrs={"itemtype": "http://schema.org/Event"}
                )
                if not items:
                    break
                for item in items:
                    listing = _listing(item)
                    by_url.setdefault(listing.url, listing)
                page += 1
    return list(by_url.values())
