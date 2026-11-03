from datetime import date

import pytest

from concert_radar.sources.dates import portuguese_dates


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("03 NOV 2026", [date(2026, 11, 3)]),
        ("20 E 21 NOV 2026", [date(2026, 11, 20), date(2026, 11, 21)]),
        ("13 novembro 2026", [date(2026, 11, 13)]),
        ("6 março 2027", [date(2027, 3, 6)]),
        (
            "19 dezembro 2026 a 20 dezembro 2026",
            [date(2026, 12, 19), date(2026, 12, 20)],
        ),
        ("30 NOV E 01 DEZ 2026", [date(2026, 11, 30), date(2026, 12, 1)]),
        (
            "04 junho 2027 | 11:00 - 06 junho 2027 | 20:00",
            [date(2027, 6, 4), date(2027, 6, 6)],
        ),
        ("08 janeiro 2027 | 21:30", [date(2027, 1, 8)]),
    ],
)
def test_portuguese_dates(text: str, expected: list[date]) -> None:
    assert portuguese_dates(text) == expected


def test_unreadable_date_raises() -> None:
    with pytest.raises(ValueError, match="Date not understood"):
        portuguese_dates("em breve")
