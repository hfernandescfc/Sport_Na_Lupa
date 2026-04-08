"""Transform raw processed match and team-stat CSVs into curated tables.

Produces:
  data/curated/serie_b_2026/matches.csv          — 1 row per Série B match
  data/curated/serie_b_2026/team_match_stats.csv — 2 rows per Série B match (home + away)
  data/curated/sport_2026/matches.csv            — 1 row per Sport match (all competitions)
  data/curated/sport_2026/team_match_stats.csv   — Sport team stats (all competitions)
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


def transform_matches(settings: Settings, season: int) -> None:
    _transform_serie_b(settings, season)
    _transform_sport(settings, season)


# ---------------------------------------------------------------------------
# Série B
# ---------------------------------------------------------------------------

def _transform_serie_b(settings: Settings, season: int) -> None:
    processed = settings.processed_dir / str(season)
    curated = settings.curated_dir / "serie_b_2026"

    matches_df = _load_serie_b_matches(processed)
    stats_df = _load_serie_b_team_stats(processed)

    if matches_df.empty:
        logger.warning("No Série B match data found — skipping transform")
        return

    write_csv(curated / "matches.csv", matches_df.to_dict("records"))
    logger.info("Curated Série B matches: %s rows -> %s", len(matches_df), curated / "matches.csv")

    if not stats_df.empty:
        write_csv(curated / "team_match_stats.csv", stats_df.to_dict("records"))
        logger.info("Curated Série B team stats: %s rows -> %s", len(stats_df), curated / "team_match_stats.csv")


def _load_serie_b_matches(processed: Path) -> pd.DataFrame:
    matches_path = processed / "matches" / "matches.csv"
    ids_path = processed / "matches" / "match_ids.csv"

    if not matches_path.exists():
        logger.warning("matches.csv not found: %s", matches_path)
        return pd.DataFrame()

    df = pd.read_csv(matches_path, dtype=str)

    # Enrich with event_id from match_ids.csv
    if ids_path.exists():
        ids_df = pd.read_csv(ids_path, dtype=str)[["match_code", "event_id"]]
        df = df.merge(ids_df, left_on="match_id", right_on="match_code", how="left").drop(columns=["match_code"], errors="ignore")

    df = df.rename(columns={
        "match_id": "match_code",
        "home_team_name": "home_team",
        "away_team_name": "away_team",
    })
    df["home_team_key"] = df["home_team"].fillna("").apply(normalize_team_name)
    df["away_team_key"] = df["away_team"].fillna("").apply(normalize_team_name)
    df["competition"] = "serie_b"
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df["match_label"] = (
        df["home_team"] + " "
        + df["home_score"].fillna("?").astype(str) + " x "
        + df["away_score"].fillna("?").astype(str) + " "
        + df["away_team"]
    )
    df["transformed_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    cols = [
        "season", "competition", "round", "match_code", "event_id", "match_label",
        "match_date_utc", "home_team", "home_team_key", "away_team", "away_team_key",
        "home_score", "away_score", "status", "venue_name",
        "source_url", "data_status", "last_updated_at", "transformed_at",
    ]
    return df.reindex(columns=[c for c in cols if c in df.columns])


def _load_serie_b_team_stats(processed: Path) -> pd.DataFrame:
    path = processed / "matches" / "team_match_stats.csv"
    if not path.exists():
        logger.warning("team_match_stats.csv not found: %s", path)
        return pd.DataFrame()

    df = pd.read_csv(path, dtype=str)
    df = df.rename(columns={"match_id": "match_code"})
    df["team_key"] = df["team_name"].fillna("").apply(normalize_team_name)
    df["competition"] = "serie_b"
    df = _add_team_stat_derived(df)
    df["transformed_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    cols = [
        "season", "competition", "round", "match_code", "team_name", "team_key", "is_home",
        "possession", "expected_goals", "shots_total", "shots_on_target", "shots_on_target_pct",
        "corners", "fouls", "passes_total", "passes_accurate", "passes_accuracy_pct",
        "tackles_total", "yellow_cards", "red_cards",
        "data_status", "last_updated_at", "transformed_at",
    ]
    return df.reindex(columns=[c for c in cols if c in df.columns])


# ---------------------------------------------------------------------------
# Sport (all competitions)
# ---------------------------------------------------------------------------

def _transform_sport(settings: Settings, season: int) -> None:
    processed = settings.processed_dir / str(season)
    curated = settings.curated_dir / "sport_2026"
    curated.mkdir(parents=True, exist_ok=True)

    matches_df = _load_sport_matches(processed, season)
    stats_df = _load_sport_team_stats(processed, season)

    if matches_df.empty:
        logger.warning("No Sport match data found — skipping transform")
        return

    write_csv(curated / "matches.csv", matches_df.to_dict("records"))
    logger.info("Curated Sport matches: %s rows -> %s", len(matches_df), curated / "matches.csv")

    if not stats_df.empty:
        write_csv(curated / "team_match_stats.csv", stats_df.to_dict("records"))
        logger.info("Curated Sport team stats: %s rows -> %s", len(stats_df), curated / "team_match_stats.csv")


def _load_sport_matches(processed: Path, season: int) -> pd.DataFrame:
    path = processed / "sport" / f"sport_{season}_matches.csv"
    if not path.exists():
        logger.warning("sport matches file not found: %s", path)
        return pd.DataFrame()

    df = pd.read_csv(path, dtype=str)
    df["home_team_key"] = df["home_team"].fillna("").apply(normalize_team_name)
    df["away_team_key"] = df["away_team"].fillna("").apply(normalize_team_name)
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    df["match_label"] = (
        df["home_team"] + " "
        + df["home_score"].fillna("?").astype(str) + " x "
        + df["away_score"].fillna("?").astype(str) + " "
        + df["away_team"]
    )
    df["transformed_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    cols = [
        "season", "competition_scope", "competition_name", "competition_round",
        "match_code", "event_id", "match_label", "match_date_utc",
        "home_team", "home_team_key", "away_team", "away_team_key",
        "home_score", "away_score", "sport_outcome", "status", "is_completed",
        "venue_name", "match_url", "data_status", "last_updated_at", "transformed_at",
    ]
    return df.reindex(columns=[c for c in cols if c in df.columns])


def _load_sport_team_stats(processed: Path, season: int) -> pd.DataFrame:
    path = processed / "sport" / f"sport_{season}_team_match_stats.csv"
    if not path.exists():
        logger.warning("sport team_match_stats file not found: %s", path)
        return pd.DataFrame()

    df = pd.read_csv(path, dtype=str)
    df["team_key"] = df["team_name"].fillna("").apply(normalize_team_name)
    df = _add_team_stat_derived(df)
    df["transformed_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    cols = [
        "season", "competition_name", "competition_round", "match_id",
        "team_name", "team_key", "is_home",
        "possession", "expected_goals", "shots_total", "shots_on_target", "shots_on_target_pct",
        "corners", "fouls", "passes_total", "passes_accurate", "passes_accuracy_pct",
        "tackles_total", "yellow_cards", "red_cards",
        "data_status", "last_updated_at", "transformed_at",
    ]
    return df.reindex(columns=[c for c in cols if c in df.columns])


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _add_team_stat_derived(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["passes_total", "passes_accurate", "shots_total", "shots_on_target"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["passes_accuracy_pct"] = (
        (df["passes_accurate"] / df["passes_total"] * 100)
        .where(df["passes_total"] > 0)
        .round(1)
    )
    df["shots_on_target_pct"] = (
        (df["shots_on_target"] / df["shots_total"] * 100)
        .where(df["shots_total"] > 0)
        .round(1)
    )
    return df
