from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field


class Country(StrEnum):
    PORTUGAL = "PT"
    SPAIN = "ES"


class Source(StrEnum):
    BOL = "BOL"
    TICKETLINE = "Ticketline"
    LA_GANZUA = "La Ganzúa"
    MEO_ARENA = "MEO Arena"
    CAMPO_PEQUENO = "Campo Pequeno"
    FORUM_BRAGA = "Forum Braga"
    GUIMARAES = "Multiusos Guimarães"
    SUPER_BOCK_ARENA = "Super Bock Arena"
    COLISEU_PORTO = "Coliseu Porto"
    LAV = "LAV"
    NOS_ALIVE = "NOS Alive"
    SONAR = "Sónar"
    PRIMAVERA_SOUND = "Primavera Sound"
    SONS_EM_TRANSITO = "Sons em Trânsito"


class Listing(BaseModel):
    """One event as a ticketing or listings site publishes it."""

    source: Source
    title: str
    performers: list[str] = Field(
        description="Performer names when the site lists them separately; empty when the artist is only in the title."
    )
    starts_on: date
    venue: str
    city: str
    country: Country
    url: str


class RadarState(BaseModel):
    """What one run remembers for the next."""

    first_seen: dict[str, date] = Field(
        description="Show key -> the day the show first appeared."
    )
    last_worked: dict[Source, date] = Field(
        description="The last day each source returned events."
    )
    # Defaults keep state files written before these fields existed readable.
    artists: dict[str, str] = Field(
        default_factory=dict,
        description="Spotify ID -> name of the playlist artists, as last read from Spotify.",
    )
    artists_read_on: date | None = Field(
        default=None, description="The day the artists were last read from Spotify."
    )


class MatchKind(StrEnum):
    ARTIST = "artist"  # the artist is playing
    RELATED = "related"  # a tribute, cover or other show about the artist


class Show(BaseModel):
    """A playlist artist's show on a given day, merged across every site that lists it."""

    titles: list[str] = Field(
        description="Each distinct title the sites give the event."
    )
    artist: str
    kind: MatchKind = Field(
        description="ARTIST if any site lists the artist as playing."
    )
    artist_ids: list[str] = Field(
        description="Spotify IDs of the playlist artists with this name; usually one."
    )
    starts_on: date
    venue: str
    city: str
    country: Country
    links: dict[Source, str]
    first_seen: date


class PlaylistArtist(BaseModel):
    """An artist from the user's playlists, as the page lists them for following."""

    id: str = Field(description="Spotify artist ID.")
    name: str
    upcoming: int = Field(description="How many upcoming shows they play.")
    related: int = Field(
        description="How many upcoming tributes and other related shows."
    )


class PageLogin(BaseModel):
    """What the page needs to log you in to Spotify from the browser. None of it is secret."""

    client_id: str
    redirect_uri: str
    scope: str


class PageData(BaseModel):
    """Data the page's script reads: how to log in, and the playlist artists to offer for following."""

    login: PageLogin
    artists: list[PlaylistArtist] = Field(
        description="Artists with upcoming shows first."
    )
