"""Transform processed opponent data into curated tables.

Input:  data/processed/{season}/opponents/{team_key}/
Output: data/curated/opponents_{season}/{team_key}/

Tables produced:
  - matches.csv          — all matches with team_outcome column
  - team_match_stats.csv — advanced stats for both teams per match
  - player_match_stats.csv — individual scouts for both teams per match
"""
from __future__ import annotations

import csv
import datetime
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger
from src.utils.normalize import normalize_team_name


logger = get_logger(__name__)


def transform_opponent(settings: Settings, team_key: str, season: int) -> None:
    """Normalize processed opponent data into curated tables."""
    in_dir = settings.processed_dir / str(season) / "opponents" / team_key
    out_dir = settings.curated_dir / f"opponents_{season}" / team_key

    # --- Matches ---
    matches_path = in_dir / "matches.csv"
    if matches_path.exists():
        matches = _read_csv(matches_path)
        curated_matches = _curate_matches(matches, team_key)
        write_csv(out_dir / "matches.csv", curated_matches)
        logger.info("[%s] Curated matches: %s rows", team_key, len(curated_matches))
    else:
        logger.warning("[%s] matches.csv not found at %s", team_key, matches_path)

    # --- Team stats ---
    stats_path = in_dir / "team_match_stats.csv"
    if stats_path.exists():
        stats = _read_csv(stats_path)
        write_csv(out_dir / "team_match_stats.csv", stats)
        logger.info("[%s] Curated team stats: %s rows", team_key, len(stats))
    else:
        logger.warning("[%s] team_match_stats.csv not found at %s", team_key, stats_path)

    # --- Player stats ---
    players_path = in_dir / "player_match_stats.csv"
    if players_path.exists():
        players = _read_csv(players_path)
        write_csv(out_dir / "player_match_stats.csv", players)
        logger.info("[%s] Curated player stats: %s rows", team_key, len(players))
    else:
        logger.warning("[%s] player_match_stats.csv not found at %s", team_key, players_path)


def _curate_matches(
    matches: list[dict[str, Any]], team_key: str
) -> list[dict[str, Any]]:
    """Enrich match rows with team_outcome and is_home_team columns."""
    now = datetime.datetime.utcnow().isoformat() + "Z"
    curated: list[dict[str, Any]] = []

    for m in matches:
        home_key = normalize_team_name(m.get("home_team", ""))
        # Match if canonical key starts with team_key or team_key starts with home_key
        # e.g. "vila-nova-fc" should match team_key "vila-nova"
        is_home = home_key == team_key or home_key.startswith(team_key) or team_key.startswith(home_key)

        outcome = _determine_outcome(
            m.get("home_score"), m.get("away_score"), is_home
        )

        curated.append({
            **m,
            "team_key": team_key,
            "is_home_team": is_home,
            "team_outcome": outcome,
            "transformed_at": now,
        })

    return curated


def _determine_outcome(
    home_score: Any, away_score: Any, is_home: bool
) -> str | None:
    if home_score is None or away_score is None:
        return None
    try:
        h, a = int(home_score), int(away_score)
    except (ValueError, TypeError):
        return None
    if is_home:
        return "win" if h > a else "loss" if h < a else "draw"
    return "win" if a > h else "loss" if a < h else "draw"


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        logger.error("Could not read %s: %s", path, exc)
        return []
