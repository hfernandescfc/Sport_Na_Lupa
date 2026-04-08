from __future__ import annotations

import re
import unicodedata


ALIASES = {
    "america": "america-mg",
    "america mg": "america-mg",
    "athletic club": "athletic-club",
    "atletico goianiense": "atletico-go",
    "atletico goianiense saf": "atletico-go",
    "avai": "avai",
    "botafogo": "botafogo-sp",
    "botafogo sp": "botafogo-sp",
    "ceara": "ceara",
    "crb": "crb",
    "criciuma": "criciuma",
    "cuiaba": "cuiaba",
    "cuiaba saf": "cuiaba",
    "fortaleza": "fortaleza",
    "goias": "goias",
    "gremio novorizontino": "novorizontino",
    "gremio novorizontino saf": "novorizontino",
    "juventude": "juventude",
    "londrina": "londrina",
    "londrina saf": "londrina",
    "nautico": "nautico",
    "operario": "operario-pr",
    "operario pr": "operario-pr",
    "ponte preta": "ponte-preta",
    "sao bernardo": "sao-bernardo",
    "sport": "sport",
    "sport recife": "sport",
    "vila nova": "vila-nova",
}


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_team_name(name: str) -> str:
    value = _strip_accents(name).lower().strip()
    value = re.sub(r"[-_/]", " ", value)
    value = re.sub(r"\bsaf\b", "", value)
    value = re.sub(r"\s+", " ", value).strip()
    return ALIASES.get(value, value.replace(" ", "-"))

