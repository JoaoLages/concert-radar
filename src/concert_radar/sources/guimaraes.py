"""Multiusos de Guimarães (multiusosdeguimaraes.pt). Its agenda is drawn in the browser, so events
are found through the site's events sitemap and dated from each event page's start timestamp."""

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup, Tag

from concert_radar.models import Country, Listing, Source

_SITEMAP = "https://multiusosdeguimaraes.pt/ajde_events-sitemap.xml"
_EVENT_PAGE = re.compile(r"<loc>(https://multiusosdeguimaraes\.pt/events/[^<]+/)</loc>")
_LISBON = ZoneInfo("Europe/Lisbon")


def _listing(client: httpx.Client, url: str) -> Listing:
    response = client.get(url)
    response.raise_for_status()
    page = BeautifulSoup(response.text, "html.parser")
    title = page.select_one('meta[property="og:title"]')
    when = page.select_one("[data-time]")  # "<start>-<end>", Unix seconds
    if not isinstance(title, Tag) or not isinstance(when, Tag):
        raise TypeError(
            f"Multiusos de Guimarães event without a title or start time: {url}"
        )
    return Listing(
        source=Source.GUIMARAES,
        title=str(title["content"]).split(" | ")[0],  # "<name> | Multiusos Guimarães"
        performers=[],
        starts_on=datetime.fromtimestamp(
            int(str(when["data-time"]).split("-")[0]), _LISBON
        ).date(),
        venue="Multiusos de Guimarães",
        city="Guimarães",
        country=Country.PORTUGAL,
        url=url,
    )


def listings(client: httpx.Client) -> list[Listing]:
    response = client.get(_SITEMAP)
    response.raise_for_status()
    return [_listing(client, url) for url in _EVENT_PAGE.findall(response.text)]
