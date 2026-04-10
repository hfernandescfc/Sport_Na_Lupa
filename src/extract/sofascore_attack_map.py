"""Fetch extended match stats + shotmap for an opponent across all 2026 matches.

Uses the curated matches CSV (output of transform-opponent) to get event_ids
and home/away context, then fetches:
  - /api/v1/event/{event_id}/statistics  → all stat groups (flat CSV per match)
  - /api/v1/event/{event_id}/shotmap     → all shots for the opponent team

Output:
  data/processed/{season}/opponents/{team_key}/
    extended_stats.csv      — per-match extended stats for the opponent team
    shotmap.json            — all opponent shots across matches (with event_id)

Usage:
    python -m src.main sync-attack-map --team-key avai --season 2026
"""
from __future__ import annotations

import csv
import datetime
import json
import time
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_csv, write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Mapping from SofaScore stat keys → our field names
STAT_KEY_MAP: dict[str, str] = {
    "ballPossession":           "possession",
    "expectedGoals":            "expected_goals",
    "bigChanceCreated":         "big_chances_created",
    "bigChanceScored":          "big_chances_scored",
    "totalShotsOnGoal":         "shots_total",
    "shotsOnGoal":              "shots_on_target",
    "shotsOffGoal":             "shots_off_target",
    "blockedScoringAttempt":    "shots_blocked",
    "totalShotsInsideBox":      "shots_inside_box",
    "totalShotsOutsideBox":     "shots_outside_box",
    "hitWoodwork":              "hit_woodwork",
    "cornerKicks":              "corners",
    "fouls":                    "fouls",
    "passes":                   "passes_total",
    "accuratePasses":           "passes_accurate",
    "throwIns":                 "throw_ins",
    "finalThirdEntries":        "final_third_entries",
    "finalThirdPhaseStatistic": "final_third_phases",
    "accurateLongBalls":        "long_balls_accurate",
    "accurateCross":            "crosses_accurate",
    "touchesInOppBox":          "touches_opp_box",
    "fouledFinalThird":         "fouls_suffered_final_third",
    "offsides":                 "offsides",
    "duelWonPercent":           "duels_won_pct",
    "dispossessed":             "dispossessed",
    "groundDuelsPercentage":    "ground_duels_pct",
    "aerialDuelsPercentage":    "aerial_duels_pct",
    "dribblesPercentage":       "dribbles_success_pct",
    "wonTacklePercent":         "tackles_won_pct",
    "totalTackle":              "tackles_total",
    "interceptionWon":          "interceptions",
    "ballRecovery":             "ball_recovery",
    "totalClearance":           "clearances",
    "errorsLeadToShot":         "errors_lead_to_shot",
    "goalkeeperSaves":          "gk_saves",
    "goalsPrevented":           "goals_prevented",
}


def sync_attack_map(settings: Settings, team_key: str, season: int) -> None:
    """Fetch extended stats + shotmap for all completed matches of an opponent."""

    curated_matches_path = (
        settings.curated_dir / f"opponents_{season}" / team_key / "matches.csv"
    )
    if not curated_matches_path.exists():
        logger.error(
            "Curated matches not found at %s — run sync-opponent + transform-opponent first.",
            curated_matches_path,
        )
        return

    matches = _read_csv(curated_matches_path)
    completed = [
        m for m in matches
        if m.get("status") == "completed" and m.get("event_id") and m.get("source_url")
    ]

    if not completed:
        logger.warning("[%s] No completed matches found in curated data.", team_key)
        return

    logger.info(
        "[%s] Fetching extended stats + shotmap for %d completed matches",
        team_key, len(completed),
    )

    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except ImportError:
        logger.warning("Selenium not available — aborting sync-attack-map.")
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)

    extended_rows: list[dict[str, Any]] = []
    all_shots: list[dict[str, Any]] = []

    try:
        for match in completed:
            event_id = int(match["event_id"])
            source_url = match["source_url"]
            is_home = match.get("is_home_team", "").lower() in ("true", "1", "yes")
            side = "home" if is_home else "away"

            logger.info("  → event_id=%s  side=%s  url=%s", event_id, side, source_url)

            try:
                driver.get(source_url)
                time.sleep(2)
            except Exception as exc:
                logger.warning("Failed to load page %s: %s", source_url, exc)
                continue

            # --- Extended team stats ---
            stats_row = _fetch_extended_stats(driver, event_id, match, is_home)
            if stats_row:
                extended_rows.append(stats_row)

            # --- Shotmap ---
            shots = _fetch_shotmap(driver, event_id, is_home)
            all_shots.extend(shots)

    finally:
        driver.quit()

    out_dir = settings.processed_dir / str(season) / "opponents" / team_key
    now = datetime.datetime.utcnow().isoformat() + "Z"

    if extended_rows:
        write_csv(out_dir / "extended_stats.csv", extended_rows)
        logger.info("[%s] Extended stats saved: %d rows", team_key, len(extended_rows))
    else:
        logger.warning("[%s] No extended stats retrieved.", team_key)

    shotmap_payload = {
        "team_key": team_key,
        "season": season,
        "total_shots": len(all_shots),
        "fetched_at": now,
        "shots": all_shots,
    }
    write_json(out_dir / "shotmap.json", shotmap_payload)
    logger.info("[%s] Shotmap saved: %d shots", team_key, len(all_shots))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_extended_stats(
    driver: Any,
    event_id: int,
    match: dict[str, Any],
    is_home: bool,
) -> dict[str, Any] | None:
    """Fetch /statistics for a match and return a flat row for the opponent team."""
    url = f"/api/v1/event/{event_id}/statistics"
    try:
        result = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", arguments[0], false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            url,
        )
    except Exception as exc:
        logger.warning("XHR failed for stats event=%s: %s", event_id, exc)
        return None

    if result.get("status") != 200:
        logger.warning("Stats HTTP %s for event=%s", result.get("status"), event_id)
        return None

    try:
        body = json.loads(result["body"])
    except Exception as exc:
        logger.warning("JSON parse error for stats event=%s: %s", event_id, exc)
        return None

    # Extract only the ALL period
    side_key = "home" if is_home else "away"
    row: dict[str, Any] = {
        "event_id":    event_id,
        "match_date":  match.get("match_date_utc", ""),
        "competition": match.get("competition_name", ""),
        "round":       match.get("competition_round", ""),
        "is_home":     is_home,
        "home_score":  match.get("home_score", ""),
        "away_score":  match.get("away_score", ""),
        "outcome":     match.get("team_outcome", ""),
    }

    for period_data in body.get("statistics", []):
        if period_data.get("period") != "ALL":
            continue
        for group in period_data.get("groups", []):
            for item in group.get("statisticsItems", []):
                sfs_key = item.get("key", "")
                our_key = STAT_KEY_MAP.get(sfs_key)
                if our_key is None:
                    continue
                raw_val = item.get(f"{side_key}Value")
                if raw_val is not None:
                    row[our_key] = raw_val

    return row


def _fetch_shotmap(
    driver: Any,
    event_id: int,
    is_home: bool,
) -> list[dict[str, Any]]:
    """Fetch /shotmap and return opponent shots as flat dicts."""
    url = f"/api/v1/event/{event_id}/shotmap"
    try:
        result = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", arguments[0], false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            url,
        )
    except Exception as exc:
        logger.warning("XHR failed for shotmap event=%s: %s", event_id, exc)
        return []

    if result.get("status") != 200:
        logger.warning("Shotmap HTTP %s for event=%s", result.get("status"), event_id)
        return []

    try:
        body = json.loads(result["body"])
    except Exception as exc:
        logger.warning("JSON parse error for shotmap event=%s: %s", event_id, exc)
        return []

    shots: list[dict[str, Any]] = []
    for shot in body.get("shotmap", []):
        shot_is_home = shot.get("isHome", False)
        if shot_is_home != is_home:
            continue  # filter to opponent shots only

        coords = shot.get("playerCoordinates") or {}
        shots.append({
            "event_id":    event_id,
            "shot_type":   shot.get("shotType", ""),
            "situation":   shot.get("situation", ""),
            "body_part":   shot.get("bodyPart", ""),
            "player_x":    coords.get("x"),   # 0=attacking goal, 100=own goal
            "player_y":    coords.get("y"),   # 0=left, 100=right
            "xg":          shot.get("xg"),
            "xgot":        shot.get("xgot"),
            "minute":      shot.get("time"),
            "player_name": (shot.get("player") or {}).get("shortName", ""),
        })

    logger.info("    shotmap: %d opponent shots for event=%s", len(shots), event_id)
    return shots


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        logger.error("Could not read %s: %s", path, exc)
        return []
