"""Transform raw per-match heatmap centroids into a curated position table.

Reads:
  data/processed/{season}/player_positions/sport_serie_b_heatmaps.json

Produces:
  data/curated/sport_{season}/player_positions_serie_b.csv

One row per player per round. Only players with heatmap data (n_points > 0).
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

CURATED_COLS = [
    "season", "competition", "round",
    "event_id", "match_code", "match_label",
    "home_team", "away_team", "is_home",
    "player_id", "player_name", "player_slug",
    "position", "jersey_number", "is_substitute",
    "minutes_played",
    "n_points",
    "avg_x", "avg_y",
    "transformed_at",
]


def transform_player_positions(settings: Settings, season: int) -> None:
    src_path = (
        settings.processed_dir / str(season) / "player_positions"
        / "sport_serie_b_heatmaps.json"
    )
    if not src_path.exists():
        logger.warning("Player positions source not found: %s", src_path)
        return

    data = json.loads(src_path.read_text(encoding="utf-8"))
    records = data.get("records", [])

    now = datetime.datetime.utcnow().isoformat() + "Z"
    rows: list[dict[str, Any]] = []

    for r in records:
        if not r.get("n_points"):
            continue   # skip players with no heatmap data
        row = {c: r.get(c) for c in CURATED_COLS if c != "transformed_at"}
        row["transformed_at"] = now
        rows.append(row)

    out_path = settings.curated_dir / f"sport_{season}" / "player_positions_serie_b.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_csv(out_path, [{c: r.get(c) for c in CURATED_COLS} for r in rows])

    logger.info(
        "Player positions curated: %d rows (%d with data / %d total) → %s",
        len(rows), len(rows), len(records), out_path,
    )
