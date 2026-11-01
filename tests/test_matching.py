from datetime import date

import pytest

from concert_radar.matching import ArtistMatcher
from concert_radar.models import Country, Listing, Source

# Real BOL and Ticketline titles, against artists from a real set of playlists.
ARTISTS = [
    "ProfJam",
    "Capitão Fausto",
    "Miguel",
    "Santana",
    "Toy",
    "GNR",
    "Eva",
    "Genesis",
    "Coldplay",
    "Ana Bacalhau",
    "Steve Hackett",
    "Mão Morta",
    "グラハム・ブルバード",
    "Amon Amarth",
    "Nas",
]


def _titled(title: str) -> Listing:
    return Listing(
        source=Source.BOL,
        title=title,
        performers=[],
        starts_on=date(2027, 1, 1),
        venue="",
        city="",
        country=Country.PORTUGAL,
        url="",
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("PROFJAM NO COLISEU", ["ProfJam"]),
        ("Capitão Fausto Têm os Dias Contados: 10 anos", ["Capitão Fausto"]),
        ("CAPITÃO FAUSTO | TÊM OS DIAS CONTADOS: 10 ANOS", ["Capitão Fausto"]),
        ("TOY | 50 ANOS DE CARREIRA", ["Toy"]),
        ("GNR | IN VIVO", ["GNR"]),
        ("Ana Bacalhau", ["Ana Bacalhau"]),
        ("AMON AMARTH | THE ALLFATHER AWAKENS", ["Amon Amarth"]),
        ("Steve Hackett-The Best of Genesis&Solo Gems-2027", ["Steve Hackett"]),
        ("MANIFESTUM Mão Morta Redux e Pedro Serrazina", []),
        ("ANTÓNIO ZAMBUJO MIGUEL ARAÚJO | 10 ANOS DEPOIS", []),
        ("Miguel Araújo", []),
        ("LUAN SANTANA – REGISTRO HISTÓRICO", []),
        ("Jazz nas Adegas | Feel Good Band | Quinta João Clara | 17H00", []),
        ("COLDDAY | WORLD&#34;S NUMBER ONE COLDPLAY TRIBUTE", []),
        ("Tributo Pearl Jam + Alice In Chains - AC Marginália", []),
        ("&#34;Filomúsica&#34; - Gala Lírica", []),
    ],
)
def test_title_matching(title: str, expected: list[str]) -> None:
    assert ArtistMatcher(ARTISTS).artists_in(_titled(title)) == expected


def test_performer_matching_is_exact() -> None:
    listing = _titled("anything").model_copy(
        update={"performers": ["Amon Amarth", "Santana Jr"]}
    )
    assert ArtistMatcher(ARTISTS).artists_in(listing) == ["Amon Amarth"]
