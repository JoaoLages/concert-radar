"""La Ganzúa (laganzua.net): paginated yearly lists of concerts in Spain."""

from datetime import date

import httpx

from concert_radar.models import Country, Listing, Source
from concert_radar.sources.jsonld import events_in


def listings(client: httpx.Client, today: date) -> list[Listing]:
    """This year's and next year's concerts, from today on."""
    found: list[Listing] = []
    for year in (today.year, today.year + 1):
        page = 1
        while True:
            suffix = f"/pagina-{page}" if page > 1 else ""
            response = client.get(
                f"https://www.laganzua.net/conciertos/espana/{year}{suffix}"
            )
            if response.status_code == httpx.codes.NOT_FOUND:
                break
            response.raise_for_status()
            found += [
                Listing(
                    source=Source.LA_GANZUA,
                    title=event.name,
                    performers=event.performer_names,
                    starts_on=event.starts_on,
                    venue=event.location.name,
                    city=event.location.address.locality,
                    country=Country.SPAIN,
                    url=event.url,
                )
                for event in events_in(response.text)
                if event.starts_on >= today
            ]
            page += 1
    return found
