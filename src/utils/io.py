from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import Settings


PROJECT_DIRS = [
    "data/raw/cbf",
    "data/raw/sofascore/competition",
    "data/raw/sofascore/sport",
    "data/raw/sofascore/teams",
    "data/raw/sofascore/matches",
    "data/processed/2026/clubs",
    "data/processed/2026/sport",
    "data/processed/2026/matches",
    "data/processed/2026/events",
    "data/processed/2026/players",
    "data/processed/2026/all_teams",
    "data/curated/serie_b_2026",
    "data/curated/sport_2026",
    "logs",
    "notebooks",
    "src/discover",
    "src/extract",
    "src/transform",
    "src/validate",
    "tests",
]


def ensure_project_structure(settings: Settings) -> None:
    for relative in PROJECT_DIRS:
        (settings.base_dir / relative).mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
