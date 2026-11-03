import html
import re
import unicodedata
from collections.abc import Iterable

from concert_radar.models import Listing

# Pieces that split an event title into its acts: "A | Tour", "A + B", "A - B", "A & B", ...
_SEPARATOR = r"(?:[|:+&,/]|\s[-–—]\s)"
# Tribute nights aren't the artist, and cancelled shows aren't happening.
_SKIPPED = re.compile(r"tribut|\btrib\.|cancelad")
# A name this long, or with several words, is unlikely to be the start of someone else's name,
# so it may be followed by free text ("ProfJam no Coliseu"). Shorter names must stand alone
# in their part of the title, so "Miguel" doesn't match "Miguel Araújo".
_DISTINCTIVE_LENGTH = 7


def normalize(text: str) -> str:
    """Casefold, decode HTML entities, drop accents and collapse whitespace."""
    decomposed = unicodedata.normalize("NFKD", html.unescape(text).casefold())
    return " ".join(
        "".join(c for c in decomposed if not unicodedata.combining(c)).split()
    )


class ArtistMatcher:
    """Finds which of a set of artists an event listing is for."""

    def __init__(self, artists: Iterable[str]) -> None:
        self._by_name = {normalize(a): a for a in artists}
        self._title_patterns = {
            name: self._title_pattern(name) for name in self._by_name
        }

    @staticmethod
    def _title_pattern(name: str) -> re.Pattern[str]:
        distinctive = " " in name or len(name) >= _DISTINCTIVE_LENGTH
        ending = r"(?!\w)" if distinctive else rf"(?=\s*(?:$|{_SEPARATOR}))"
        return re.compile(rf"(?:^|{_SEPARATOR})\s*{re.escape(name)}{ending}")

    def artists_in(self, listing: Listing) -> list[str]:
        if listing.performers:
            return [
                self._by_name[n]
                for n in map(normalize, listing.performers)
                if n in self._by_name
            ]
        title = normalize(listing.title)
        if _SKIPPED.search(title):
            return []
        return [
            self._by_name[n]
            for n, pattern in self._title_patterns.items()
            if pattern.search(title)
        ]
