"""BOL (bol.pt): one search page lists every upcoming music event in Portugal."""

import httpx

from concert_radar.models import Country, Listing, Source
from concert_radar.sources.jsonld import events_in

_MUSIC_URL = "https://www.bol.pt/Comprar/pesquisa/2-0-0-0-0-0/musica_e_concertos"


def listings(client: httpx.Client) -> list[Listing]:
    response = client.get(_MUSIC_URL)
    response.raise_for_status()
    return [
        Listing(
            source=Source.BOL,
            title=event.name,
            performers=[],
            starts_on=event.starts_on,
            venue=event.location.name,
            city=event.location.address.locality,
            country=Country.PORTUGAL,
            url=event.url,
        )
        for event in events_in(response.text)
    ]
