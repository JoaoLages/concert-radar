import argparse
import logging
import os
import time
from collections.abc import Callable
from datetime import date
from pathlib import Path

import httpx
from jinja2 import Environment, PackageLoader, select_autoescape

from concert_radar import spotify
from concert_radar.matching import ArtistMatcher
from concert_radar.models import Country, Listing, RadarState, Source
from concert_radar.shows import show_key, shows_from
from concert_radar.sources import bandsintown, bol, laganzua, ticketline

logger = logging.getLogger(__name__)

# Some sites turn away clients that don't look like a browser.
_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
_STATE_FILE = "state.json"


def _fetch_listings(
    today: date, pause_seconds: float, ticketline_months: int
) -> dict[Source, list[Listing]]:
    """Listings from every source that worked. A site that errors or returns nothing
    (usually a layout change or a block) is logged and left out, so the others still publish."""

    def pause(_: httpx.Request) -> None:
        time.sleep(pause_seconds)

    with httpx.Client(
        headers={"User-Agent": _USER_AGENT},
        timeout=30,
        follow_redirects=True,
        event_hooks={"request": [pause]},
    ) as client:
        fetchers: dict[Source, Callable[[], list[Listing]]] = {
            Source.BOL: lambda: bol.listings(client),
            Source.TICKETLINE: lambda: ticketline.listings(
                client, today, ticketline_months
            ),
            Source.LA_GANZUA: lambda: laganzua.listings(client, today),
            Source.BANDSINTOWN: lambda: bandsintown.listings(client),
        }
        worked: dict[Source, list[Listing]] = {}
        for source, fetch in fetchers.items():
            try:
                found = fetch()
            except Exception:
                logger.exception("%s failed; skipping it today", source)
                continue
            if not found:
                logger.error("%s returned no events; skipping it today", source)
                continue
            logger.info("%s: %d events", source, len(found))
            worked[source] = found
    return worked


def build(
    out_dir: Path, pause_seconds: float, ticketline_months: int, new_days: int
) -> None:
    today = date.today()
    artists = spotify.playlist_artists(
        os.environ["SPOTIFY_CLIENT_ID"],
        os.environ["SPOTIFY_CLIENT_SECRET"],
        os.environ["SPOTIFY_REFRESH_TOKEN"],
    )
    logger.info("Spotify: %d artists", len(artists))
    state_path = out_dir / _STATE_FILE
    state = (
        RadarState.model_validate_json(state_path.read_bytes())
        if state_path.exists()
        else RadarState(first_seen={}, last_worked={})
    )
    by_source = _fetch_listings(today, pause_seconds, ticketline_months)
    shows = shows_from(
        [listing for found in by_source.values() for listing in found],
        ArtistMatcher(artists),
        state.first_seen,
        today,
    )
    logger.info("Matched %d shows", len(shows))
    # Upcoming shows stay remembered while their source is down, so they aren't "new" again on its return.
    state = RadarState(
        first_seen={
            key: seen
            for key, seen in state.first_seen.items()
            if key.rsplit("|", 1)[1] >= today.isoformat()
        }
        | {show_key(s.artist, s.starts_on): s.first_seen for s in shows},
        last_worked=state.last_worked | dict.fromkeys(by_source, today),
    )

    template = Environment(
        loader=PackageLoader("concert_radar"), autoescape=select_autoescape()
    ).get_template("index.html.j2")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(
        template.render(
            shows=shows,
            artist_count=len(artists),
            countries=list(Country),
            sources=list(Source),
            last_worked=state.last_worked,
            today=today,
            new_days=new_days,
        ),
        encoding="utf-8",
    )
    state_path.write_text(state.model_dump_json(indent=1), encoding="utf-8")


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO"), format="%(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser(prog="concert-radar")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "login",
        help="Authorise Spotify once and print the refresh token to store as a secret.",
    )
    build_parser = commands.add_parser("build", help="Write the concerts page.")
    build_parser.add_argument(
        "--out",
        type=Path,
        default=Path("site"),
        help=f"Folder for index.html and {_STATE_FILE}.",
    )
    build_parser.add_argument(
        "--pause", type=float, default=0.5, help="Seconds to wait before each request."
    )
    build_parser.add_argument(
        "--ticketline-months",
        type=int,
        default=14,
        help="How many months ahead to search.",
    )
    build_parser.add_argument(
        "--new-days",
        type=int,
        default=7,
        help="Mark shows first seen this recently as new.",
    )
    args = parser.parse_args()
    if args.command == "login":
        print(
            spotify.login(
                os.environ["SPOTIFY_CLIENT_ID"], os.environ["SPOTIFY_CLIENT_SECRET"]
            )
        )
    elif args.command == "build":
        build(args.out, args.pause, args.ticketline_months, args.new_days)
    else:
        raise NotImplementedError(args.command)
