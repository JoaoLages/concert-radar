from datetime import date
from pathlib import Path

import httpx
import pytest

from concert_radar.models import Country, Listing, Source
from concert_radar.sources import (
    bol,
    coliseu_porto,
    events_calendar,
    festivals,
    guimaraes,
    laganzua,
    ticketline,
    venue_pages,
)

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


def test_venue_page_lists_each_day_of_a_multi_day_show() -> None:
    meo_arena = next(v for v in venue_pages.VENUES if v.source == Source.MEO_ARENA)
    found = venue_pages.listings(_client("meo_arena.html"), meo_arena)
    assert [(listing.title, listing.starts_on) for listing in found] == [
        ("DURAN DURAN - FREE TO LOVE TOUR", date(2026, 11, 3)),
        ("BRYAN ADAMS - ROLL WITH THE PUNCHES", date(2026, 11, 20)),
        ("BRYAN ADAMS - ROLL WITH THE PUNCHES", date(2026, 11, 21)),
    ]
    assert found[0].url.startswith("https://arena.meo.pt/agenda/")


@pytest.mark.parametrize(
    ("event_page", "expected"),
    [
        (
            "ticketline_tour.html",
            [
                (date(2027, 4, 5), "Super Bock Arena - Pavilhão Rosa Mota"),
                (date(2027, 4, 6), "Sagres Campo Pequeno"),
            ],
        ),
        (
            "ticketline_sessions.html",
            [
                (date(2026, 12, 26), "Super Bock Arena - Pavilhão Rosa Mota"),
                (date(2026, 12, 27), "Super Bock Arena - Pavilhão Rosa Mota"),
                (date(2026, 12, 27), "Super Bock Arena - Pavilhão Rosa Mota"),
            ],
        ),
    ],
)
def test_ticketline_lists_every_date_of_an_event(
    event_page: str, expected: list[tuple[date, str]]
) -> None:
    search_page = (
        (FIXTURES / "ticketline.html")
        .read_text()
        .replace('<li class=" "', '<li class="has_multiple_sessions "', 1)
    )

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/pesquisa/":
            first = (
                request.url.params["page"] == "1"
                and request.url.params["month"] == "11"
            )
            return httpx.Response(200, text=search_page if first else "<html></html>")
        return httpx.Response(200, text=(FIXTURES / event_page).read_text())

    found = ticketline.listings(
        httpx.Client(transport=httpx.MockTransport(handle)), date(2026, 11, 1), months=2
    )
    assert [(listing.starts_on, listing.venue) for listing in found] == expected
    assert {listing.title for listing in found} == {"BRANDI CARLILE | THE HUMAN TOUR"}


def test_events_calendar_venue() -> None:
    venue = events_calendar.VENUES[0]
    found = events_calendar.listings(_client("events_calendar.json"), venue)
    assert [(listing.title, listing.starts_on, listing.venue) for listing in found] == [
        ("MAX COOPER", date(2026, 11, 5), venue.name),
        ("YOTTO | MISTY FEST – CANCELADO", date(2026, 11, 6), venue.name),
    ]


def test_coliseu_porto_keeps_upcoming_shows_in_lisbon_time() -> None:
    found = coliseu_porto.listings(_client("coliseu_porto.json"), date(2026, 11, 7))
    assert [(listing.title, listing.starts_on, listing.url) for listing in found] == [
        (
            "Late show",
            date(2026, 11, 8),
            "https://coliseu.pt/evento/20261107-late-show",
        )
    ]


def test_guimaraes_reads_events_from_the_sitemap() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        fixture = (
            "guimaraes_sitemap.xml"
            if request.url.path.endswith(".xml")
            else "guimaraes_event.html"
        )
        return httpx.Response(200, text=(FIXTURES / fixture).read_text())

    found = guimaraes.listings(httpx.Client(transport=httpx.MockTransport(handle)))
    assert [(listing.title, listing.starts_on, listing.url) for listing in found] == [
        (
            "A Primeira Depois da Ceia",
            date(2026, 12, 26),
            "https://multiusosdeguimaraes.pt/events/a-primeira-depois-da-ceia/",
        )
    ]


def test_nos_alive_lists_each_act_on_its_day() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        day_one = request.url.path == "/primeiro-dia/"
        return httpx.Response(
            200,
            text=(FIXTURES / "nos_alive_day.html").read_text()
            if day_one
            else "<html></html>",
        )

    found = festivals.nos_alive(
        httpx.Client(transport=httpx.MockTransport(handle)), date(2026, 11, 5)
    )
    assert [(listing.performers, listing.starts_on) for listing in found] == [
        (["The Strokes"], date(2027, 7, 8)),
        (["Tom Misch"], date(2027, 7, 8)),
    ]


def test_sonar_lists_each_act_on_the_first_day() -> None:
    found = festivals.sonar(_client("sonar.html"))
    assert [
        (listing.performers, listing.starts_on, listing.url) for listing in found
    ] == [
        (["Bonobo"], date(2027, 6, 17), "https://sonar.es/en/activity/bonobo"),
        (["Peggy Gou"], date(2027, 6, 17), "https://sonar.es/en/activity/peggy-gou"),
    ]
