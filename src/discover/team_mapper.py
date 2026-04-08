from __future__ import annotations

from src.config import Settings
from src.extract.cbf_competition import CBF_SERIE_B_2026_CLUBS
from src.utils.io import write_csv
from src.utils.normalize import normalize_team_name


MANUAL_TEAM_MAPPINGS = {
    "america-mg": {
        "sofascore_team_id": 1973,
        "sofascore_slug": "america-mineiro",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/america-mineiro/1973",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "athletic-club": {
        "sofascore_team_id": 342775,
        "sofascore_slug": "athletic-club",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/athletic-club/342775",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "atletico-go": {
        "sofascore_team_id": 7314,
        "sofascore_slug": "atletico-goianiense",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/atletico-goianiense/7314",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "avai": {
        "sofascore_team_id": 7315,
        "sofascore_slug": "avai",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/avai/7315",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "botafogo-sp": {
        "sofascore_team_id": 1979,
        "sofascore_slug": "botafogo-sp",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/botafogo-sp/1979",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "ceara": {
        "sofascore_team_id": 2001,
        "sofascore_slug": "ceara",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/ceara/2001",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "crb": {
        "sofascore_team_id": 22032,
        "sofascore_slug": "crb",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/crb/22032",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "criciuma": {
        "sofascore_team_id": 1984,
        "sofascore_slug": "criciuma",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/criciuma/1984",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "cuiaba": {
        "sofascore_team_id": 49202,
        "sofascore_slug": "cuiaba",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/cuiaba/49202",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "fortaleza": {
        "sofascore_team_id": 2020,
        "sofascore_slug": "fortaleza",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/fortaleza/2020",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "goias": {
        "sofascore_team_id": 1960,
        "sofascore_slug": "goias",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/goias/1960",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "novorizontino": {
        "sofascore_team_id": 135514,
        "sofascore_slug": "novorizontino",
        "sofascore_url": "https://www.sofascore.com/football/team/novorizontino/135514",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "juventude": {
        "sofascore_team_id": 1980,
        "sofascore_slug": "juventude",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/juventude/1980",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "londrina": {
        "sofascore_team_id": 2022,
        "sofascore_slug": "londrina",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/londrina/2022",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "nautico": {
        "sofascore_team_id": 2011,
        "sofascore_slug": "nautico",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/nautico/2011",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "operario-pr": {
        "sofascore_team_id": 39634,
        "sofascore_slug": "operario-pr",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/operario-pr/39634",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "ponte-preta": {
        "sofascore_team_id": 1969,
        "sofascore_slug": "ponte-preta",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/ponte-preta/1969",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "sao-bernardo": {
        "sofascore_team_id": 47504,
        "sofascore_slug": "sao-bernardo",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/sao-bernardo/47504",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "sport": {
        "sofascore_team_id": 1959,
        "sofascore_slug": "sport-recife",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/sport-recife/1959",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
    "vila-nova": {
        "sofascore_team_id": 2021,
        "sofascore_slug": "vila-nova",
        "sofascore_url": "https://www.sofascore.com/pt/football/team/vila-nova/2021",
        "mapping_status": "confirmed",
        "mapping_notes": "Confirmed from SofaScore team page in March 2026.",
    },
}


def resolve_team_mapping(name: str) -> dict[str, str | int]:
    canonical_name = normalize_team_name(name)
    mapping = MANUAL_TEAM_MAPPINGS.get(canonical_name)
    if mapping:
        return {
            "canonical_name": canonical_name,
            **mapping,
        }

    return {
        "canonical_name": canonical_name,
        "sofascore_team_id": "",
        "sofascore_slug": "",
        "sofascore_url": "",
        "mapping_status": "pending",
        "mapping_notes": "Requires SofaScore lookup.",
    }


def build_team_mapping_stub(settings: Settings, season: int) -> None:
    output = settings.processed_dir / str(season) / "clubs" / "club_mapping.csv"
    rows = []
    for club in CBF_SERIE_B_2026_CLUBS:
        resolved = resolve_team_mapping(club)
        rows.append(
            {
                "season": season,
                "cbf_name": club,
                "canonical_name": resolved["canonical_name"],
                "sofascore_team_id": resolved["sofascore_team_id"],
                "sofascore_slug": resolved["sofascore_slug"],
                "sofascore_url": resolved["sofascore_url"],
                "mapping_status": resolved["mapping_status"],
                "mapping_notes": resolved["mapping_notes"],
            }
        )
    write_csv(output, rows)
