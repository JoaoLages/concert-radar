"""Venues whose WordPress site runs The Events Calendar plugin, read through its public REST API."""

import html
from datetime import date

import httpx
from pydantic import BaseModel, ConfigDict, Field

from concert_radar.models import Country, Listing, Source


class Venue(BaseModel):
    source: Source
    site: str = Field(
        description="The venue's website, e.g. https://www.superbockarena.pt"
    )
    name: str
    city: str


VENUES = [
    Venue(
        source=Source.SUPER_BOCK_ARENA,
        site="https://www.superbockarena.pt",
        name="Super Bock Arena",
        city="Porto",
    ),
    Venue(
        source=Source.LAV,
        site="https://lisboaaovivo.com",
        name="LAV - Lisboa ao Vivo",
        city="Lisboa",
    ),
]


class _Event(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(description="May contain HTML entities, e.g. '&#8211;'.")
    start_date: str = Field(description="Local time, 'YYYY-MM-DD HH:MM:SS'.")
    url: str


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore")

    events: list[_Event]
    next_rest_url: str | None = None  # absent on the last page


def listings(client: httpx.Client, venue: Venue) -> list[Listing]:
    """Upcoming events: by default the API returns today through two years ahead."""
    found: list[Listing] = []
    url: str | None = f"{venue.site}/wp-json/tribe/events/v1/events?per_page=50"
    while url:
        response = client.get(url)
        response.raise_for_status()
        page = _Page.model_validate_json(response.text)
        found += [
            Listing(
                source=venue.source,
                title=html.unescape(event.title),
                performers=[],
                starts_on=date.fromisoformat(event.start_date[:10]),
                venue=venue.name,
                city=venue.city,
                country=Country.PORTUGAL,
                url=event.url,
            )
            for event in page.events
        ]
        url = page.next_rest_url
    return found
