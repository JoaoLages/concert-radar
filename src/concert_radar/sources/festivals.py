"""Festival lineups. Big festivals are sold as one ticket named after the festival, so the acts
playing them only show up on the festival's own lineup pages. Each act becomes its own listing."""

import re
from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from concert_radar.models import Country, Listing, Source
from concert_radar.sources.dates import next_portuguese_day

_NOS_ALIVE = "https://nosalive.com"
_SONAR = "https://sonar.es"
# "17.18.19 June 2027": the festival's days, then the month and year.
_SONAR_DAYS = re.compile(r"\b(\d{1,2})(?:\.\d{1,2})*\s+June\s+(\d{4})\b")


def nos_alive(client: httpx.Client, today: date) -> list[Listing]:
    """One page per festival day; each act's card gives its name and day ("08 JUL")."""
    found: list[Listing] = []
    for day_page in ("primeiro-dia", "segundo-dia", "terceiro-dia"):
        response = client.get(f"{_NOS_ALIVE}/{day_page}/")
        response.raise_for_status()
        for card in BeautifulSoup(response.text, "html.parser").select(
            "div.portfolio-item"
        ):
            name, when, link = (
                card.select_one(s)
                for s in (".port-captions h4", ".port-captions .description", "a[href]")
            )
            if (
                not isinstance(name, Tag)
                or not isinstance(when, Tag)
                or not isinstance(link, Tag)
            ):
                raise TypeError(f"NOS Alive act without a name, day or link: {card}")
            artist = name.get_text(" ", strip=True)
            found.append(
                Listing(
                    source=Source.NOS_ALIVE,
                    title=f"NOS Alive: {artist}",
                    performers=[artist],
                    starts_on=next_portuguese_day(
                        when.get_text(" ", strip=True), today
                    ),
                    venue="NOS Alive, Passeio Marítimo de Algés",
                    city="Oeiras",
                    country=Country.PORTUGAL,
                    url=str(link["href"]),
                )
            )
    return found


def sonar(client: httpx.Client) -> list[Listing]:
    """The lineup page doesn't date each act, so every act is listed on the festival's first day."""
    response = client.get(f"{_SONAR}/en/programme/line-up")
    response.raise_for_status()
    page = BeautifulSoup(response.text, "html.parser")
    days = _SONAR_DAYS.search(page.get_text(" ", strip=True))
    if not days:
        raise ValueError("Sónar's festival dates weren't found on its lineup page")
    first_day = date(int(days[2]), 6, int(days[1]))
    return [
        Listing(
            source=Source.SONAR,
            title=f"Sónar: {act.get_text(' ', strip=True)}",
            performers=[act.get_text(" ", strip=True)],
            starts_on=first_day,
            venue="Sónar",
            city="Barcelona",
            country=Country.SPAIN,
            url=_SONAR + str(act["href"]),
        )
        for act in page.select('a[href^="/en/activity/"]')
    ]
