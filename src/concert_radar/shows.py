"""Turns raw listings into the deduplicated shows the page displays."""

from collections import defaultdict
from datetime import date

from concert_radar.matching import ArtistMatcher, normalize
from concert_radar.models import Listing, MatchKind, Show


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
        # Some sites keep listing an event that started in the past (a long exhibition, a run of shows).
        if listing.starts_on < today:
            continue
        for artist, kind in matcher.artists_in(listing).items():
            key = show_key(artist, listing.starts_on)
            if key in shows:
                show = shows[key]
                show.links.setdefault(listing.source, listing.url)
                if normalize(listing.title) not in map(normalize, show.titles):
                    show.titles.append(listing.title)
                if kind == MatchKind.ARTIST:
                    show.kind = MatchKind.ARTIST
                continue
            shows[key] = Show(
                titles=[listing.title],
                artist=artist,
                kind=kind,
                artist_ids=sorted(ids_by_name[normalize(artist)]),
                starts_on=listing.starts_on,
                venue=listing.venue,
                city=listing.city,
                country=listing.country,
                links={listing.source: listing.url},
                first_seen=first_seen.get(key, today),
            )
    return sorted(shows.values(), key=lambda s: (s.starts_on, normalize(s.artist)))
