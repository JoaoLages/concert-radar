"""Reads schema.org events embedded as JSON-LD in a listings page."""

import json
from datetime import date

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field


class _Schema(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Address(_Schema):
    locality: str = Field(alias="addressLocality")


class Place(_Schema):
    name: str
    address: Address


class Performer(_Schema):
    name: str


class Event(_Schema):
    name: str
    url: str
    start: str = Field(
        alias="startDate",
        description="ISO datetime; some sites add 7 fractional digits.",
    )
    location: Place
    performer: Performer | list[Performer] | None = None

    @property
    def starts_on(self) -> date:
        return date.fromisoformat(self.start[:10])

    @property
    def performer_names(self) -> list[str]:
        performers = (
            self.performer
            if isinstance(self.performer, list)
            else [self.performer]
            if self.performer
            else []
        )
        return [p.name for p in performers]


def events_in(page: str) -> list[Event]:
    """Every schema.org Event or MusicEvent on the page; other JSON-LD blocks are skipped."""
    events: list[Event] = []
    for script in BeautifulSoup(page, "html.parser").find_all(
        "script", type="application/ld+json"
    ):
        items = json.loads(script.get_text())
        for item in items if isinstance(items, list) else [items]:
            if isinstance(item, dict) and item.get("@type") in ("Event", "MusicEvent"):
                events.append(Event.model_validate(item))
    return events
