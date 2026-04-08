from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import Settings
from src.utils.io import write_json


def run_quality_checks(settings: Settings, season: int) -> None:
    clubs_path = settings.processed_dir / str(season) / "clubs" / "cbf_clubs.csv"
    mapping_path = settings.processed_dir / str(season) / "clubs" / "club_mapping.csv"
    sport_competitions_path = settings.processed_dir / str(season) / "sport" / "sport_2026_competitions.csv"
    sport_matches_path = settings.processed_dir / str(season) / "sport" / "sport_2026_matches.csv"
    sport_team_stats_path = settings.processed_dir / str(season) / "sport" / "sport_2026_team_match_stats.csv"
    serie_b_matches_path = settings.processed_dir / str(season) / "matches" / "match_ids.csv"
    serie_b_results_path = settings.processed_dir / str(season) / "matches" / "matches.csv"
    team_stats_path = settings.processed_dir / str(season) / "matches" / "team_match_stats.csv"
    report_path = settings.curated_dir / "serie_b_2026" / "validation_report.json"
    report = {
        "season": season,
        "mode": "incremental",
        "checks": [],
    }
    if clubs_path.exists():
        clubs_df = pd.read_csv(clubs_path)
        report["checks"].append(
            {
                "name": "club_count",
                "status": "pass" if len(clubs_df) == 20 else "fail",
                "expected": 20,
                "actual": int(len(clubs_df)),
            }
        )
    else:
        report["checks"].append(
            {
                "name": "club_seed_exists",
                "status": "fail",
                "path": str(clubs_path),
            }
        )

    if mapping_path.exists():
        mapping_df = pd.read_csv(mapping_path)
        confirmed_count = int((mapping_df["mapping_status"] == "confirmed").sum())
        report["checks"].append(
            {
                "name": "confirmed_team_mapping_count",
                "status": "pass" if confirmed_count == 20 else "fail",
                "expected": 20,
                "actual": confirmed_count,
            }
        )
        missing_ids = int(mapping_df["sofascore_team_id"].isna().sum())
        report["checks"].append(
            {
                "name": "missing_sofascore_team_ids",
                "status": "pass" if missing_ids == 0 else "fail",
                "expected": 0,
                "actual": missing_ids,
            }
        )
    else:
        report["checks"].append(
            {
                "name": "team_mapping_exists",
                "status": "fail",
                "path": str(mapping_path),
            }
        )

    if sport_competitions_path.exists():
        sport_df = pd.read_csv(sport_competitions_path)
        report["checks"].append(
            {
                "name": "sport_competition_seed_exists",
                "status": "pass" if len(sport_df) >= 4 else "fail",
                "expected_min": 4,
                "actual": int(len(sport_df)),
            }
        )
    else:
        report["checks"].append(
            {
                "name": "sport_competition_seed_exists",
                "status": "fail",
                "path": str(sport_competitions_path),
            }
        )

    if sport_matches_path.exists():
        sport_matches_df = pd.read_csv(sport_matches_path)
        confirmed_matches = int(
            (sport_matches_df["status"] == "completed").sum()
        )
        report["checks"].append(
            {
                "name": "sport_confirmed_match_seed_count",
                "status": "pass" if confirmed_matches >= 1 else "fail",
                "expected_min": 1,
                "actual": confirmed_matches,
                "notes": "Counts matches with status=completed from the live API.",
            }
        )
        future_or_open_matches = int((sport_matches_df["is_completed"] == False).sum())  # noqa: E712
        report["checks"].append(
            {
                "name": "sport_incremental_open_match_rows",
                "status": "pass" if future_or_open_matches >= 1 else "warn",
                "expected_min": 1,
                "actual": future_or_open_matches,
                "notes": "Open rows are expected while the season is in progress.",
            }
        )
    else:
        report["checks"].append(
            {
                "name": "sport_match_seed_exists",
                "status": "fail",
                "path": str(sport_matches_path),
            }
        )

    if sport_team_stats_path.exists():
        sport_team_stats_df = pd.read_csv(sport_team_stats_path)
        report["checks"].append(
            {
                "name": "sport_team_advanced_stats_rows",
                "status": "pass" if len(sport_team_stats_df) >= 2 else "warn",
                "expected_min": 2,
                "actual": int(len(sport_team_stats_df)),
                "notes": "Sport team stats should grow incrementally as completed matches expose statistics on SofaScore.",
            }
        )
    else:
        report["checks"].append(
            {
                "name": "sport_team_advanced_stats_exists",
                "status": "warn",
                "path": str(sport_team_stats_path),
            }
        )

    if serie_b_matches_path.exists():
        serie_b_df = pd.read_csv(serie_b_matches_path)
        unique_rounds = int(serie_b_df["round"].nunique()) if not serie_b_df.empty else 0
        report["checks"].append(
            {
                "name": "serie_b_incremental_round_seed_count",
                "status": "pass" if unique_rounds >= 1 else "fail",
                "expected_min": 1,
                "actual": unique_rounds,
                "notes": "A live season should not require all 38 rounds upfront.",
            }
        )
        report["checks"].append(
            {
                "name": "serie_b_full_season_coverage",
                "status": "info",
                "expected_final": 38,
                "actual_now": unique_rounds,
                "notes": "This is informational during the live season and becomes mandatory only after season completion.",
            }
        )
    else:
        report["checks"].append(
            {
                "name": "serie_b_match_seed_exists",
                "status": "fail",
                "path": str(serie_b_matches_path),
            }
        )

    if serie_b_results_path.exists():
        results_df = pd.read_csv(serie_b_results_path)
        completed = int((results_df["status"] == "completed").sum()) if not results_df.empty else 0
        report["checks"].append(
            {
                "name": "serie_b_round_1_completed_results",
                "status": "pass" if completed >= 10 else "warn",
                "expected_round_1": 10,
                "actual": completed,
                "notes": "This measures whether round 1 already has enough final scores for basic analysis.",
            }
        )
    else:
        report["checks"].append(
            {
                "name": "serie_b_results_exists",
                "status": "fail",
                "path": str(serie_b_results_path),
            }
        )

    if team_stats_path.exists():
        team_stats_df = pd.read_csv(team_stats_path)
        advanced_count = int(len(team_stats_df))
        required_fields = [
            "expected_goals",
            "shots_total",
            "corners",
            "fouls",
            "passes_total",
            "tackles_total",
            "yellow_cards",
        ]
        report["checks"].append(
            {
                "name": "serie_b_team_advanced_stats_rows",
                "status": "pass" if advanced_count >= 20 else "warn",
                "expected_round_1_min": 20,
                "actual": advanced_count,
                "notes": "Two rows per match are expected for full round-level team analysis.",
            }
        )
        invalid_confirmed = 0
        if not team_stats_df.empty:
            confirmed_mask = team_stats_df["data_status"] == "advanced_stats_confirmed"
            if confirmed_mask.any():
                invalid_confirmed = int(
                    team_stats_df.loc[confirmed_mask, required_fields].isna().any(axis=1).sum()
                )
        report["checks"].append(
            {
                "name": "serie_b_team_advanced_stats_confirmed_consistency",
                "status": "pass" if invalid_confirmed == 0 else "fail",
                "expected": 0,
                "actual": invalid_confirmed,
                "notes": "Confirmed rows cannot have empty required advanced metrics.",
            }
        )
    else:
        report["checks"].append(
            {
                "name": "serie_b_team_advanced_stats_exists",
                "status": "fail",
                "path": str(team_stats_path),
            }
        )

    write_json(report_path, report)
    summary_path = settings.curated_dir / "serie_b_2026" / "validation_summary.md"
    _write_summary(summary_path, report)


def _write_summary(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Validation Summary", ""]
    for check in report["checks"]:
        lines.append(f"- {check['name']}: {check['status']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
