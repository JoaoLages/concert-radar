import html
import re
import unicodedata
from collections.abc import Iterable

from concert_radar.models import Listing, MatchKind

# Pieces that split an event title into its acts: "A | Tour", "A + B", "A - B", "A & B", "A e B", ...
_SEPARATOR = r"(?:[|:+&,/]|\s[-–—]\s|\se\s)"
_CANCELLED = re.compile(r"cancelad")
# Words that mark a show as about an artist rather than by them: tributes, covers, orchestral takes.
_RELATED_WORDS = re.compile(
    r"tribut|\btrib\.|\bexperience\b|symphon|sinfoni|for solo piano|the music of|"
    r"a musica de|cancoes de|homenagem|revisita"
)
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
        # Distinctive names are also recognised mid-title ("THE WORLD OF HANS ZIMMER"), as related.
        self._anywhere_patterns = {
            name: re.compile(rf"(?<!\w){re.escape(name)}(?!\w)")
            for name in self._by_name
            if " " in name or len(name) >= _DISTINCTIVE_LENGTH
        }

    @staticmethod
    def _title_pattern(name: str) -> re.Pattern[str]:
        distinctive = " " in name or len(name) >= _DISTINCTIVE_LENGTH
        ending = r"(?!\w)" if distinctive else rf"(?=\s*(?:$|{_SEPARATOR}))"
        return re.compile(rf"(?:^|{_SEPARATOR})\s*{re.escape(name)}{ending}")

    def artists_in(self, listing: Listing) -> dict[str, MatchKind]:
        """The artists a listing is for, each as playing it or only related to it."""
        if listing.performers:
            return {
                self._by_name[n]: MatchKind.ARTIST
                for n in map(normalize, listing.performers)
                if n in self._by_name
            }
        title = normalize(listing.title)
        if _CANCELLED.search(title):
            return {}
        about_someone = bool(_RELATED_WORDS.search(title))
        found: dict[str, MatchKind] = {}
        for name, artist in self._by_name.items():
            if name not in title:  # cheap check before the regexes
                continue
            if self._title_patterns[name].search(title):
                found[artist] = MatchKind.RELATED if about_someone else MatchKind.ARTIST
            elif name in self._anywhere_patterns and self._anywhere_patterns[
                name
            ].search(title):
                found[artist] = MatchKind.RELATED
        return found
