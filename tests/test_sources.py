from datetime import date
from pathlib import Path

import httpx

from concert_radar.models import Country, Listing, Source
from concert_radar.sources import bandsintown, bol, laganzua, ticketline

FIXTURES = Path(__file__).parent / "fixtures"


def _client(fixture: str) -> httpx.Client:
    """Serves the fixture for the first request of each path and query, and an empty page after."""
    served: set[str] = set()

    def handle(request: httpx.Request) -> httpx.Response:
        if (
            "pagina-" in request.url.path
            or request.url.params.get("page", "1") != "1"
            or str(request.url) in served
        ):
            return httpx.Response(
                404 if "laganzua" in request.url.host else 200, text="<html></html>"
            )
        served.add(str(request.url))
        return httpx.Response(200, text=(FIXTURES / fixture).read_text())

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_bol() -> None:
    found = bol.listings(_client("bol.html"))
    assert found[1] == Listing(
        source=Source.BOL,
        title="JOSÉ GONZÁLEZ | MISTY FEST",
        performers=[],
        starts_on=found[1].starts_on,
        venue=found[1].venue,
        city=found[1].city,
        country=Country.PORTUGAL,
        url=found[1].url,
    )
    assert found[1].url.startswith("https://www.bol.pt/")


def test_ticketline_lists_each_event_once() -> None:
    found = ticketline.listings(_client("ticketline.html"), date(2026, 11, 1), months=2)
    assert [(listing.title, listing.url) for listing in found] == [
        (
            "BRANDI CARLILE | THE HUMAN TOUR",
            "https://www.ticketline.pt/evento/brandi-carlile-the-human-tour-98399",
        )
    ]


def test_laganzua_skips_past_events() -> None:
    assert [
        listing.performers
        for listing in laganzua.listings(_client("laganzua.html"), date(2026, 11, 1))
    ] == [["Drugos"], ["Drugos"]]
    assert laganzua.listings(_client("laganzua.html"), date(2027, 6, 1)) == []


def test_bandsintown_keeps_only_portugal_and_spain() -> None:
    found = bandsintown.listings(_client("bandsintown.json"))
    assert {
        (listing.performers[0], listing.city, listing.country) for listing in found
    } == {
        ("Richard Bona", "Madrid", Country.SPAIN),
        (found[1].performers[0], found[1].city, Country.SPAIN),
    }
    assert len(found) == 2
