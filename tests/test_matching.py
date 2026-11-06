from datetime import date

import pytest

from concert_radar.matching import ArtistMatcher
from concert_radar.models import Country, Listing, MatchKind, Source

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
    "António Zambujo",
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


A, R = MatchKind.ARTIST, MatchKind.RELATED


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("PROFJAM NO COLISEU", {"ProfJam": A}),
        ("Capitão Fausto Têm os Dias Contados: 10 anos", {"Capitão Fausto": A}),
        ("CAPITÃO FAUSTO | TÊM OS DIAS CONTADOS: 10 ANOS", {"Capitão Fausto": A}),
        ("TOY | 50 ANOS DE CARREIRA", {"Toy": A}),
        ("GNR | IN VIVO", {"GNR": A}),
        ("Ana Bacalhau", {"Ana Bacalhau": A}),
        ("AMON AMARTH | THE ALLFATHER AWAKENS", {"Amon Amarth": A}),
        # The headliner plays; another distinctive name mid-title is only related.
        (
            "Steve Hackett-The Best of Genesis&Solo Gems-2027",
            {"Steve Hackett": A, "Genesis": R},
        ),
        ("MANIFESTUM Mão Morta Redux e Pedro Serrazina", {"Mão Morta": R}),
        # Short names only count where they stand alone.
        ("ANTÓNIO ZAMBUJO MIGUEL ARAÚJO | 10 ANOS DEPOIS", {"António Zambujo": A}),
        ("Miguel Araújo", {}),
        ("Jazz nas Adegas | Feel Good Band | Quinta João Clara | 17H00", {}),
        ("LUAN SANTANA – REGISTRO HISTÓRICO", {"Santana": R}),
        ("COLDDAY | WORLD&#34;S NUMBER ONE COLDPLAY TRIBUTE", {"Coldplay": R}),
        ("THE BUZZ LOVERS | GENESIS EXPERIENCE", {"Genesis": R}),
        ("Tributo Pearl Jam + Alice In Chains - AC Marginália", {}),
        ("Miguel Araújo e António Zambujo", {"António Zambujo": A}),
        ("&#34;Filomúsica&#34; - Gala Lírica", {}),
        ("PROFJAM | MISTY FEST – CANCELADO", {}),
    ],
)
def test_title_matching(title: str, expected: dict[str, MatchKind]) -> None:
    assert ArtistMatcher(ARTISTS).artists_in(_titled(title)) == expected


def test_performer_matching_is_exact() -> None:
    listing = _titled("anything").model_copy(
        update={"performers": ["Amon Amarth", "Santana Jr"]}
    )
    assert ArtistMatcher(ARTISTS).artists_in(listing) == {"Amon Amarth": A}
