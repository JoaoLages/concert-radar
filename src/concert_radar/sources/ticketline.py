"""Ticketline (ticketline.pt): music and festival searches, one month at a time."""

from datetime import date
from enum import IntEnum

import httpx
from bs4 import BeautifulSoup, Tag

from concert_radar.models import Country, Listing, Source

_BASE_URL = "https://www.ticketline.pt"
# The search shows an event with several dates or venues once, under its first date.
_MULTIPLE_DATES_CLASS = "has_multiple_sessions"


class _Category(IntEnum):
    MUSIC = 104
    FESTIVALS = 121


def _prop(item: Tag, prop: str) -> str:
    """An item's schema.org property, given either as an attribute or as text."""
    found = item.select_one(f'[itemprop="{prop}"]')
    if not isinstance(found, Tag):
        raise TypeError(f"Ticketline event without {prop}: {item}")
    if prop == "location":
        # A session gives its venue as a nested schema.org Place with its own name.
        place_name = found.select_one('[itemprop="name"]')
        found = place_name if isinstance(place_name, Tag) else found
    return str(found.get("content") or found.get_text(" ", strip=True))


def _listing(item: Tag, event: Listing | None = None) -> Listing:
    """A search result, or one date of `event` (titled and, if it has no link of its own, linked like it)."""
    link = item.select_one('a[itemprop="url"]')
    if not isinstance(link, Tag):
        raise TypeError(f"Ticketline event without a link: {item}")
    href = link.get("href")  # sessions that can't be bought (e.g. sold out) have none
    if href:
        url = _BASE_URL + str(href)
    elif event:
        url = event.url
    else:
        raise TypeError(f"Ticketline event without a link: {item}")
    return Listing(
        source=Source.TICKETLINE,
        title=event.title if event else _prop(item, "name"),
        performers=[],
        starts_on=date.fromisoformat(_prop(item, "startDate")[:10]),
        venue=_prop(item, "location"),
        city="",
        country=Country.PORTUGAL,
        url=url,
    )


def _dates_of(client: httpx.Client, event: Listing, today: date) -> list[Listing]:
    """One listing per date and venue on the event's own page, under the event's title.
    The page lists either separate events per city or sessions at one venue."""
    response = client.get(event.url)
    response.raise_for_status()
    sessions = BeautifulSoup(response.text, "html.parser").select(
        '#sessoes li[itemtype="http://schema.org/Event"]'
    )
    found = [_listing(session, event) for session in sessions]
    return [listing for listing in found if listing.starts_on >= today] or [event]


def listings(client: httpx.Client, today: date, months: int) -> list[Listing]:
    """Events starting in the next `months` months, one per date and venue."""
    by_url: dict[str, Listing] = {}
    several_dates: set[str] = set()
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
                    listing = by_url.setdefault(listing.url, listing)
                    if _MULTIPLE_DATES_CLASS in item.get_attribute_list("class"):
                        several_dates.add(listing.url)
                page += 1
    found: list[Listing] = []
    for url, listing in by_url.items():
        found += (
            _dates_of(client, listing, today) if url in several_dates else [listing]
        )
    return found
