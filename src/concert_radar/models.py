from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class Country(StrEnum):
    PORTUGAL = "PT"
    SPAIN = "ES"


class Source(StrEnum):
    BOL = "BOL"
    TICKETLINE = "Ticketline"
    LA_GANZUA = "La Ganzúa"
    BANDSINTOWN = "Bandsintown"


class Listing(BaseModel):
    """One event as a ticketing or listings site publishes it."""

    source: Source
    title: str
    performers: list[str] = Field(
        description="Performer names when the site lists them separately; empty when the artist is only in the title."
    )
    starts_on: date
    venue: str
    city: str
    country: Country
    url: str


class RadarState(BaseModel):
    """What one run remembers for the next."""

    first_seen: dict[str, date] = Field(
        description="Show key -> the day the show first appeared."
    )
    last_worked: dict[Source, date] = Field(
        description="The last day each source returned events."
    )


class Show(BaseModel):
    """A playlist artist playing on a given day, merged across every site that lists it."""

    artist: str
    starts_on: date
    venue: str
    city: str
    country: Country
    links: dict[Source, str]
    first_seen: date
