"""Coliseu Porto Ageas (coliseu.pt). The site builds its agenda in the browser from a GraphQL
endpoint; this sends the same query the site's own code sends, so a site rebuild can break it."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
from pydantic import BaseModel, ConfigDict, Field

from concert_radar.models import Country, Listing, Source

_ENDPOINT = "https://nest.coliseu.pt/graph/"
_QUERY = """query events($filter: EventFilter, $paging: OffsetPaging, $sorting: [EventSort!]) {
  events(filter: $filter, paging: $paging, sorting: $sorting) { nodes { name startDate slug state } }
}"""
# As the site asks: visible, not archived, and not category 28, which it keeps off its agenda.
_VARIABLES = {
    "paging": {"limit": 9999},
    "sorting": [{"field": "startDate", "direction": "ASC"}],
    "filter": {
        "isArchived": {"is": False},
        "isVisible": {"is": True},
        "category": {"id": {"notIn": ["28"]}},
    },
}
_LISBON = ZoneInfo("Europe/Lisbon")


class _Event(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    start: datetime = Field(alias="startDate", description="UTC.")
    slug: str
    state: str = Field(description="'ACTIVE' for shows going ahead.")


class _Events(BaseModel):
    nodes: list[_Event]


class _Data(BaseModel):
    events: _Events


class _Response(BaseModel):
    data: _Data


def listings(client: httpx.Client, today: date) -> list[Listing]:
    response = client.post(
        _ENDPOINT,
        json={"operationName": "events", "query": _QUERY, "variables": _VARIABLES},
    )
    response.raise_for_status()
    events = _Response.model_validate_json(response.text).data.events.nodes
    return [
        Listing(
            source=Source.COLISEU_PORTO,
            title=event.name,
            performers=[],
            starts_on=starts_on,
            venue="Coliseu Porto Ageas",
            city="Porto",
            country=Country.PORTUGAL,
            url=f"https://coliseu.pt/evento/{event.slug}",
        )
        for event in events
        if event.state == "ACTIVE"
        and (starts_on := event.start.astimezone(_LISBON).date()) >= today
    ]
