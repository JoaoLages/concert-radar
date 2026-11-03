"""Venues' own agenda pages: a static list of event cards, each with a title, a Portuguese date line
and a link. Many of these shows sell through Blueticket, which can't be read directly, so the
venues' pages are how they get in."""

import httpx
from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field

from concert_radar.models import Country, Listing, Source
from concert_radar.sources.dates import portuguese_dates


class VenuePage(BaseModel):
    source: Source
    site: str = Field(description="The venue's website; card links are relative to it.")
    agenda_path: str
    card: str = Field(description="CSS selector of one event card.")
    title: str = Field(description="CSS selector of the event name, within a card.")
    when: str = Field(description="CSS selector of the date line, within a card.")
    link: str = Field(
        description="CSS selector of the link to the event's page, within a card."
    )
    name: str
    city: str


VENUES = [
    VenuePage(
        source=Source.MEO_ARENA,
        site="https://arena.meo.pt",
        agenda_path="/agenda-completa",
        card=".agendaDestaquesUn",
        title="a.destaquesNome",
        when=".destaquesData",
        link="a.destaquesNome",
        name="MEO Arena",
        city="Lisboa",
    ),
    VenuePage(
        source=Source.CAMPO_PEQUENO,
        site="https://sagrescampopequeno.pt",
        agenda_path="/pt/agenda",
        card="div.event",
        title="h3.card-title",
        when=".date",
        link='a[href^="/pt/agenda/"]',
        name="Sagres Campo Pequeno",
        city="Lisboa",
    ),
    VenuePage(
        source=Source.FORUM_BRAGA,
        site="https://www.forumbraga.com",
        agenda_path="/Events",
        card="article.u-block-hover",
        title="h6",
        when="h4.dateinfo",
        link='a[href^="/Detail/"]',
        name="Altice Forum Braga",
        city="Braga",
    ),
]


def listings(client: httpx.Client, venue: VenuePage) -> list[Listing]:
    """One listing per day a card mentions; a multi-day card gives each day it names."""
    response = client.get(venue.site + venue.agenda_path)
    response.raise_for_status()
    found: list[Listing] = []
    for card in BeautifulSoup(response.text, "html.parser").select(venue.card):
        title, when, link = (
            card.select_one(s) for s in (venue.title, venue.when, venue.link)
        )
        if (
            not isinstance(title, Tag)
            or not isinstance(when, Tag)
            or not isinstance(link, Tag)
        ):
            raise TypeError(f"{venue.name} event without a title, date or link: {card}")
        found += [
            Listing(
                source=venue.source,
                title=title.get_text(" ", strip=True),
                performers=[],
                starts_on=day,
                venue=venue.name,
                city=venue.city,
                country=Country.PORTUGAL,
                url=venue.site + str(link["href"]),
            )
            for day in portuguese_dates(when.get_text(" ", strip=True))
        ]
    return found
