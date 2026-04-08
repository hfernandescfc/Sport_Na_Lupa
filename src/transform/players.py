"""Transform raw player-match stats into curated scout tables.

Produces:
  data/curated/serie_b_2026/player_match_stats.csv — scouts Série B (todos os clubes)
  data/curated/sport_2026/player_match_stats.csv   — scouts Sport (todas as competições)
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger
from src.utils.normalize import normalize_team_name


logger = get_logger(__name__)

SERIE_B_COMPETITION_KEY = "serie_b"

CURATED_COLS = [
    "season", "competition", "round", "event_id", "match_code",
    "match_label", "home_team", "away_team",
    "team_name", "team_key", "is_home",
    "player_id", "player_name", "player_slug", "position", "jersey_number", "is_substitute",
    "minutes_played", "rating",
    "total_pass", "accurate_pass", "pass_accuracy_pct",
    "total_long_balls", "accurate_long_balls", "long_ball_accuracy_pct",
    "total_shots", "goal_assist", "saves",
    "touches", "possession_lost_ctrl", "ball_recovery",
    "expected_assists",
    "pass_value_normalized", "dribble_value_normalized",
    "defensive_value_normalized", "goalkeeper_value_normalized",
    "last_updated_at", "transformed_at",
]


def transform_players(settings: Settings, season: int) -> None:
    processed = settings.processed_dir / str(season) / "players"
    all_path = processed / f"player_match_stats_{season}.csv"
    sport_path = processed / f"sport_{season}_player_match_stats.csv"

    if not all_path.exists():
        logger.warning("player_match_stats file not found: %s", all_path)
        return

    df = pd.read_csv(all_path, dtype=str)
    df = _enrich(df)

    # Série B subset
    serie_b_df = df[df["competition"] == SERIE_B_COMPETITION_KEY].copy()
    _write(settings.curated_dir / "serie_b_2026" / "player_match_stats.csv", serie_b_df)
    logger.info("Curated Série B player stats: %s rows", len(serie_b_df))

    # Sport subset (all competitions) — use sport-specific file if available
    if sport_path.exists():
        sport_df = pd.read_csv(sport_path, dtype=str)
        sport_df = _enrich(sport_df)
    else:
        sport_df = df[df["team_name"].str.contains("Sport", na=False)].copy()

    _write(settings.curated_dir / "sport_2026" / "player_match_stats.csv", sport_df)
    logger.info("Curated Sport player stats: %s rows", len(sport_df))


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["team_key"] = df["team_name"].fillna("").apply(normalize_team_name)

    for col in ["total_pass", "accurate_pass", "total_long_balls", "accurate_long_balls",
                "total_shots", "minutes_played", "rating", "touches",
                "possession_lost_ctrl", "ball_recovery", "expected_assists",
                "goal_assist", "saves",
                "pass_value_normalized", "dribble_value_normalized",
                "defensive_value_normalized", "goalkeeper_value_normalized"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["pass_accuracy_pct"] = (
        (df["accurate_pass"] / df["total_pass"] * 100)
        .where(df["total_pass"] > 0)
        .round(1)
    )
    df["long_ball_accuracy_pct"] = (
        (df["accurate_long_balls"] / df["total_long_balls"] * 100)
        .where(df["total_long_balls"] > 0)
        .round(1)
    )

    # match_label for readability
    df["match_label"] = df["home_team"] + " x " + df["away_team"]
    df["transformed_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    return df


def _write(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [c for c in CURATED_COLS if c in df.columns]
    write_csv(path, df.reindex(columns=cols).to_dict("records"))
