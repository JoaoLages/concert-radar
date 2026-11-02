from datetime import date
from pathlib import Path

import pytest

from concert_radar import cli, spotify
from concert_radar.models import Country, Listing, RadarState, Source

TODAY = date.today()


def _listing(source: Source, title: str, starts_on: date) -> Listing:
    return Listing(
        source=source,
        title=title,
        performers=[],
        starts_on=starts_on,
        venue="Coliseu",
        city="Lisboa",
        country=Country.PORTUGAL,
        url=f"https://example.com/{title}",
    )


def test_failed_source_is_skipped_and_its_shows_stay_remembered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        spotify,
        "playlist_artists",
        lambda *_: {"id1": "ProfJam", "id2": "Capitão Fausto"},
    )
    for name in ("SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REFRESH_TOKEN"):
        monkeypatch.setenv(name, "x")
    upcoming = TODAY.replace(year=TODAY.year + 1)
    seen_long_ago = date(2020, 1, 1)
    (tmp_path / "state.json").write_text(
        RadarState(
            first_seen={
                "profjam|" + upcoming.isoformat(): seen_long_ago,
                "old show|2020-01-01": seen_long_ago,
            },
            last_worked={Source.BOL: seen_long_ago},
        ).model_dump_json()
    )
    # BOL is down today; only Ticketline answers.
    monkeypatch.setattr(
        cli,
        "_fetch_listings",
        lambda *_: {
            Source.TICKETLINE: [_listing(Source.TICKETLINE, "CAPITÃO FAUSTO", upcoming)]
        },
    )

    cli.build(
        tmp_path,
        page_url="https://example.com/",
        pause_seconds=0,
        ticketline_months=1,
        new_days=7,
    )

    state = RadarState.model_validate_json((tmp_path / "state.json").read_text())
    assert state.first_seen == {
        "profjam|" + upcoming.isoformat(): seen_long_ago,
        "capitao fausto|" + upcoming.isoformat(): TODAY,
    }
    assert state.last_worked == {Source.BOL: seen_long_ago, Source.TICKETLINE: TODAY}
    page = (tmp_path / "index.html").read_text()
    assert "Capitão Fausto" in page
    assert 'data-ids="id2"' in page
    assert '"id": "id2", "name": "Capit' in page
    assert "BOL\n      ✗ last worked 1 Jan" in page
    assert "La Ganzúa\n      ✗ never worked" in page
