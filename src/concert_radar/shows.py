"""Turns raw listings into the deduplicated shows the page displays."""

from collections import defaultdict
from datetime import date

from concert_radar.matching import ArtistMatcher, normalize
from concert_radar.models import Listing, Show


def show_key(artist: str, starts_on: date) -> str:
    """Ends with the show's ISO date, so keys of past shows can be dropped."""
    return f"{normalize(artist)}|{starts_on.isoformat()}"


def shows_from(
    listings: list[Listing],
    artists: dict[str, str],
    first_seen: dict[str, date],
    today: date,
) -> list[Show]:
    """One show per artist and day, for artists given as Spotify ID -> name. Sites spell venues
    differently, so the first site to list a show names its venue. A show missing from
    `first_seen` is new today."""
    ids_by_name: dict[str, list[str]] = defaultdict(list)
    for artist_id, name in artists.items():
        ids_by_name[normalize(name)].append(artist_id)
    matcher = ArtistMatcher(artists.values())
    shows: dict[str, Show] = {}
    for listing in listings:
        for artist in matcher.artists_in(listing):
            key = show_key(artist, listing.starts_on)
            if key in shows:
                shows[key].links.setdefault(listing.source, listing.url)
                continue
            shows[key] = Show(
                artist=artist,
                artist_ids=sorted(ids_by_name[normalize(artist)]),
                starts_on=listing.starts_on,
                venue=listing.venue,
                city=listing.city,
                country=listing.country,
                links={listing.source: listing.url},
                first_seen=first_seen.get(key, today),
            )
    return sorted(shows.values(), key=lambda s: (s.starts_on, normalize(s.artist)))
