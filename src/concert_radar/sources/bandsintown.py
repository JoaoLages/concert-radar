"""Bandsintown: the upcoming-events feed its website shows around a location."""

from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict, Field

from concert_radar.models import Country, Listing, Source

_FIRST_PAGE_URL = "https://www.bandsintown.com/all-dates/fetch-next/upcomingEvents"
# The feed is centred on a point, so search around each big city to cover both countries.
_SEARCH_CENTRES = {
    "Lisbon": (38.7223, -9.1393),
    "Porto": (41.1579, -8.6291),
    "Madrid": (40.4168, -3.7038),
    "Barcelona": (41.3874, 2.1686),
}
_COUNTRY_NAMES = {"Portugal": Country.PORTUGAL, "Spain": Country.SPAIN}


class _Event(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: int
    artist_name: str = Field(alias="artistName")
    venue_name: str = Field(alias="venueName")
    location_text: str = Field(
        alias="locationText", description="'City, Country', e.g. 'Madrid, Spain'."
    )
    starts_at: datetime = Field(alias="startsAt")
    event_url: str = Field(alias="eventUrl")


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore")

    events: list[_Event]
    next_page_url: str | None = Field(alias="urlForNextPageOfEvents")


def listings(client: httpx.Client) -> list[Listing]:
    by_id: dict[int, Listing] = {}
    for latitude, longitude in _SEARCH_CENTRES.values():
        url: str | None = str(
            httpx.URL(
                _FIRST_PAGE_URL,
                params={"page": 1, "latitude": latitude, "longitude": longitude},
            )
        )
        while url:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            page = _Page.model_validate_json(response.text)
            for event in page.events:
                city, _, country_name = event.location_text.rpartition(", ")
                if event.id in by_id or country_name not in _COUNTRY_NAMES:
                    continue
                by_id[event.id] = Listing(
                    source=Source.BANDSINTOWN,
                    title=event.artist_name,
                    performers=[event.artist_name],
                    starts_on=event.starts_at.date(),
                    venue=event.venue_name,
                    city=city,
                    country=_COUNTRY_NAMES[country_name],
                    url=event.event_url,
                )
            url = page.next_page_url if page.events else None
    return list(by_id.values())
