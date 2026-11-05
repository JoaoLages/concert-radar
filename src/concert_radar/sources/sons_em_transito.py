"""Sons em Trânsito (sonsemtransito.com), a booking agency: its agenda lists its artists' tour dates
everywhere, with the artist as a separate field. Dates carry no year; the agenda runs a few months
ahead, so each is the next such day from today."""

from datetime import date

import httpx
from bs4 import BeautifulSoup, Tag

from concert_radar.models import Country, Listing, Source
from concert_radar.sources.dates import next_portuguese_day

_AGENDA = "https://www.sonsemtransito.com/pt/agenda/atual/todos"
_COUNTRIES = {"POR": Country.PORTUGAL, "ES": Country.SPAIN, "ESP": Country.SPAIN}


def listings(client: httpx.Client, today: date) -> list[Listing]:
    response = client.get(_AGENDA)
    response.raise_for_status()
    found: list[Listing] = []
    for show in BeautifulSoup(response.text, "html.parser").select(".schedule-show"):
        when, info = (
            show.select_one(".schedule-show-date"),
            show.select_one(".schedule-show-info"),
        )
        artist = info.select_one("span") if isinstance(info, Tag) else None
        if (
            not isinstance(when, Tag)
            or not isinstance(info, Tag)
            or not isinstance(artist, Tag)
        ):
            raise TypeError(
                f"Sons em Trânsito show without a date, artist or place: {show}"
            )
        name = artist.get_text(" ", strip=True)
        artist.extract()
        *place, country_code = info.get_text(
            " ", strip=True
        ).split()  # "Vila Real, Teatro Vila Real POR"
        if country_code not in _COUNTRIES:
            continue
        city, _, venue = (part.strip() for part in " ".join(place).partition(","))
        tickets = show.select_one(".schedule-show-tickets a[href]")
        found.append(
            Listing(
                source=Source.SONS_EM_TRANSITO,
                title=name,
                performers=[name],
                starts_on=next_portuguese_day(
                    when.get_text(" ", strip=True).replace(".", " "), today
                ),
                venue=venue or city,
                city=city,
                country=_COUNTRIES[country_code],
                url=str(tickets["href"]) if isinstance(tickets, Tag) else _AGENDA,
            )
        )
    return found
