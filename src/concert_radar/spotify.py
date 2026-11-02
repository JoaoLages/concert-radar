"""Reads the artists in a user's Spotify playlists."""

from pydantic import BaseModel, ConfigDict
from spotipy import Spotify, SpotifyOAuth
from spotipy.cache_handler import MemoryCacheHandler

# Must match a Redirect URI registered on the Spotify app. Spotify accepts loopback IPs, not "localhost".
REDIRECT_URI = "http://127.0.0.1:8888/callback"
_SCOPE = "playlist-read-private playlist-read-collaborative"
# What the page asks for when you log in on it: read and change the artists you follow.
PAGE_SCOPE = "user-follow-read user-follow-modify user-library-modify"


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore")


class _Owner(_Response):
    id: str


class _Playlist(_Response):
    id: str
    owner: _Owner
    collaborative: bool


class _PlaylistPage(_Response):
    items: list[_Playlist]
    next: str | None


class _Artist(_Response):
    id: str | None  # None for artists of local files added to a playlist
    name: str


class _Track(_Response):
    artists: list[_Artist] = []  # podcast episodes have no artists


class _Entry(_Response):
    item: _Track | None  # None for tracks removed from Spotify


class _EntryPage(_Response):
    items: list[_Entry]
    next: str | None


def _oauth(client_id: str, client_secret: str) -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=REDIRECT_URI,
        scope=_SCOPE,
        cache_handler=MemoryCacheHandler(),
    )


def login(client_id: str, client_secret: str) -> str:
    """Opens the Spotify consent page in a browser and returns a long-lived refresh token."""
    oauth = _oauth(client_id, client_secret)
    oauth.get_access_token(as_dict=False)
    token = oauth.get_cached_token()
    if token is None:
        raise RuntimeError("Spotify login finished without a token")
    return token["refresh_token"]


def playlist_artists(
    client_id: str, client_secret: str, refresh_token: str
) -> dict[str, str]:
    """Spotify ID -> name of every artist credited on a track in a playlist the user owns or collaborates on."""
    spotify = Spotify(
        auth=_oauth(client_id, client_secret).refresh_access_token(refresh_token)[
            "access_token"
        ]
    )
    user_id = _Owner.model_validate(spotify.current_user()).id
    artists: dict[str, str] = {}
    playlists = _PlaylistPage.model_validate(spotify.current_user_playlists())
    while True:
        for playlist in playlists.items:
            if playlist.owner.id != user_id and not playlist.collaborative:
                continue
            entries = _EntryPage.model_validate(
                spotify.playlist_items(playlist.id, limit=100)
            )
            while True:
                artists |= {
                    a.id: a.name
                    for e in entries.items
                    if e.item
                    for a in e.item.artists
                    if a.id
                }
                if not entries.next:
                    break
                entries = _EntryPage.model_validate(spotify.next(entries.model_dump()))
        if not playlists.next:
            break
        playlists = _PlaylistPage.model_validate(spotify.next(playlists.model_dump()))
    return artists
