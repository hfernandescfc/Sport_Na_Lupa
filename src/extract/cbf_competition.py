from __future__ import annotations

from src.config import Settings
from src.utils.io import write_csv, write_json
from src.utils.normalize import normalize_team_name


CBF_SERIE_B_2026_CLUBS = [
    "America-MG",
    "Athletic Club",
    "Atletico-GO",
    "Avai",
    "Botafogo-SP",
    "Ceara",
    "CRB",
    "Criciuma",
    "Cuiaba",
    "Fortaleza",
    "Goias",
    "Gremio Novorizontino",
    "Juventude",
    "Londrina",
    "Nautico",
    "Operario-PR",
    "Ponte Preta",
    "Sao Bernardo",
    "Sport",
    "Vila Nova",
]


def export_cbf_clubs_seed(settings: Settings) -> None:
    raw_path = settings.raw_dir / "cbf" / "serie_b_2026_clubs.json"
    processed_path = settings.processed_dir / "2026" / "clubs" / "cbf_clubs.csv"
    write_json(
        raw_path,
        {
            "season": 2026,
            "competition": "serie_b",
            "source": "cbf",
            "clubs": CBF_SERIE_B_2026_CLUBS,
        },
    )
    write_csv(
        processed_path,
        [
            {
                "season": 2026,
                "competition": "serie_b",
                "cbf_name": club,
                "canonical_name": normalize_team_name(club),
            }
            for club in CBF_SERIE_B_2026_CLUBS
        ],
    )

