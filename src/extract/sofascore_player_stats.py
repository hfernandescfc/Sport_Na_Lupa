"""Extract individual player statistics per match via the SofaScore lineups endpoint.

Scope:
- Sport Recife: all completed matches across all competitions (57 in 2026)
- Série B: all completed matches (all 20 clubs), sourced from match_ids.csv

Endpoint: GET /api/v1/event/{event_id}/lineups
One call per match, returns all players (starters + subs) for both teams with per-game stats.
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

# Player stat fields extracted from the lineups payload
PLAYER_STAT_FIELDS = [
    "minutes_played",
    "rating",
    # Passes aggregate
    "total_pass",
    "accurate_pass",
    "total_long_balls",
    "accurate_long_balls",
    "goal_assist",
    # Pass zones (own half vs opponent half)
    "accurate_own_half_passes",
    "total_own_half_passes",
    "accurate_opposition_half_passes",
    "total_opposition_half_passes",
    # Progression / ball carries
    "total_progression",
    "total_ball_carries_distance",
    "total_progressive_ball_carries_distance",
    "progressive_ball_carries_count",
    "best_ball_carry_progression",
    "ball_carries_count",
    # Shots
    "total_shots",
    # Defensive / duels
    "total_clearance",
    "duel_won",
    "was_fouled",
    # General
    "saves",
    "touches",
    "possession_lost_ctrl",
    "ball_recovery",
    "expected_assists",
    # Normalized value scores
    "pass_value_normalized",
    "dribble_value_normalized",
    "defensive_value_normalized",
    "goalkeeper_value_normalized",
    # GK-specific
    "keeper_save_value",
    "goals_prevented",
]

# Mapping from SofaScore camelCase keys to our snake_case field names
_STAT_KEY_MAP = {
    "minutesPlayed": "minutes_played",
    "rating": "rating",
    # Passes aggregate
    "totalPass": "total_pass",
    "accuratePass": "accurate_pass",
    "totalLongBalls": "total_long_balls",
    "accurateLongBalls": "accurate_long_balls",
    "goalAssist": "goal_assist",
    # Pass zones
    "accurateOwnHalfPasses": "accurate_own_half_passes",
    "totalOwnHalfPasses": "total_own_half_passes",
    "accurateOppositionHalfPasses": "accurate_opposition_half_passes",
    "totalOppositionHalfPasses": "total_opposition_half_passes",
    # Progression / ball carries
    "totalProgression": "total_progression",
    "totalBallCarriesDistance": "total_ball_carries_distance",
    "totalProgressiveBallCarriesDistance": "total_progressive_ball_carries_distance",
    "progressiveBallCarriesCount": "progressive_ball_carries_count",
    "bestBallCarryProgression": "best_ball_carry_progression",
    "ballCarriesCount": "ball_carries_count",
    # Shots
    "totalShots": "total_shots",
    # Defensive / duels
    "totalClearance": "total_clearance",
    "duelWon": "duel_won",
    "wasFouled": "was_fouled",
    # General
    "saves": "saves",
    "touches": "touches",
    "possessionLostCtrl": "possession_lost_ctrl",
    "ballRecovery": "ball_recovery",
    "expectedAssists": "expected_assists",
    # Normalized value scores
    "passValueNormalized": "pass_value_normalized",
    "dribbleValueNormalized": "dribble_value_normalized",
    "defensiveValueNormalized": "defensive_value_normalized",
    "goalkeeperValueNormalized": "goalkeeper_value_normalized",
    # GK-specific
    "keeperSaveValue": "keeper_save_value",
    "goalsPrevented": "goals_prevented",
}


def sync_player_stats(settings: Settings, season: int) -> None:
    """Main entry point: fetch player stats for Sport (all comps) + Série B (all clubs)."""
    match_rows = _collect_match_rows(settings, season)
    if not match_rows:
        logger.warning("No matches found to fetch player stats for season %s", season)
        return

    logger.info("Fetching player stats for %s matches", len(match_rows))

    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except Exception as exc:
        logger.warning("Selenium not available: %s", exc)
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    all_rows: list[dict[str, Any]] = []
    last_match_url: str | None = None

    for match in match_rows:
        event_id = match.get("event_id")
        match_url = match.get("match_url")
        if not event_id or not match_url:
            logger.warning("Skipping match with missing event_id or match_url: %s", match)
            continue

        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)
        try:
            driver.get(match_url)
            time.sleep(3)
            payload = _fetch_lineups_json(driver, event_id)
            if payload is None:
                logger.warning("No lineups data for event_id=%s", event_id)
                continue

            rows = _parse_lineups_payload(payload, match, season)
            all_rows.extend(rows)
            label = f"{match.get('home_team')} x {match.get('away_team')}"
            logger.info("Player stats fetched for %s: %s player rows", label, len(rows))
        except Exception as exc:
            logger.warning("Failed player stats for event_id=%s: %s", event_id, exc)
        finally:
            driver.quit()

    _persist_player_stats(settings, season, all_rows)
    logger.info("Player stats sync complete: %s total player-match rows", len(all_rows))


def _collect_match_rows(settings: Settings, season: int) -> list[dict[str, Any]]:
    """Build the list of matches to process:
    - All completed Sport matches from sport_2026_matches.csv
    - All Série B matches from match_ids.csv (deduped against Sport matches)
    """
    rows: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()

    # 1. Sport — all completed matches across all competitions
    sport_path = settings.processed_dir / str(season) / "sport" / f"sport_{season}_matches.csv"
    if sport_path.exists():
        with open(sport_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("is_completed", "").lower() != "true":
                    continue
                eid = r.get("event_id", "")
                if not eid or eid in seen_event_ids:
                    continue
                seen_event_ids.add(eid)
                rows.append({
                    "event_id": eid,
                    "match_url": r.get("match_url") or _build_match_url(r.get("match_code", ""), r.get("home_team", ""), r.get("away_team", "")),
                    "home_team": r.get("home_team"),
                    "away_team": r.get("away_team"),
                    "competition": r.get("competition_name", "sport_all"),
                    "round": r.get("competition_round"),
                    "match_code": r.get("match_code"),
                    "scope": "sport_all",
                })
    else:
        logger.warning("Sport matches file not found: %s", sport_path)

    # 2. Série B — all matches from match_ids.csv (non-Sport ones not yet included)
    serie_b_path = settings.processed_dir / str(season) / "matches" / "match_ids.csv"
    if serie_b_path.exists():
        with open(serie_b_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("is_completed", "").lower() != "true":
                    continue
                eid = r.get("event_id", "")
                if not eid or eid in seen_event_ids:
                    continue
                seen_event_ids.add(eid)
                rows.append({
                    "event_id": eid,
                    "match_url": r.get("match_url"),
                    "home_team": r.get("home_team"),
                    "away_team": r.get("away_team"),
                    "competition": "serie_b",
                    "round": r.get("round"),
                    "match_code": r.get("match_code"),
                    "scope": "serie_b",
                })
    else:
        logger.warning("Série B match_ids file not found: %s", serie_b_path)

    logger.info("Collected %s unique matches to process (%s already covered by Sport)", len(rows), len(seen_event_ids) - len(rows))
    return rows


def _fetch_lineups_json(driver: Any, event_id: str) -> dict[str, Any] | None:
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/api/v1/event/" + arguments[0] + "/lineups", false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            event_id,
        )
        if response.get("status") != 200:
            logger.warning("Lineups API status %s for event_id=%s", response.get("status"), event_id)
            return None
        return json.loads(response["body"])
    except Exception as exc:
        logger.warning("_fetch_lineups_json failed for event_id=%s: %s", event_id, exc)
        return None


def _parse_lineups_payload(
    payload: dict[str, Any],
    match: dict[str, Any],
    season: int,
) -> list[dict[str, Any]]:
    now = datetime.datetime.utcnow().isoformat() + "Z"
    rows: list[dict[str, Any]] = []

    for side, is_home in [("home", True), ("away", False)]:
        side_data = payload.get(side, {})
        team_name = (side_data.get("team") or {}).get("name", match.get("home_team" if is_home else "away_team", ""))
        team_id = (side_data.get("team") or {}).get("id")

        for player_entry in side_data.get("players", []):
            p = player_entry.get("player", {})
            stats = player_entry.get("statistics", {})

            row: dict[str, Any] = {
                "season": season,
                "competition": match.get("competition"),
                "round": match.get("round"),
                "event_id": match.get("event_id"),
                "match_code": match.get("match_code"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "team_id": team_id,
                "team_name": team_name,
                "is_home": is_home,
                "player_id": p.get("id"),
                "player_name": p.get("name"),
                "player_slug": p.get("slug"),
                "position": player_entry.get("position") or p.get("position"),
                "jersey_number": player_entry.get("jerseyNumber") or p.get("jerseyNumber"),
                "is_substitute": player_entry.get("substitute", False),
                "last_updated_at": now,
            }

            for api_key, field_name in _STAT_KEY_MAP.items():
                row[field_name] = stats.get(api_key)

            rows.append(row)

    return rows


def _build_match_url(match_code: str, home_team: str, away_team: str) -> str:
    if not match_code:
        return ""
    slug = f"{home_team.lower().replace(' ', '-')}-{away_team.lower().replace(' ', '-')}"
    return f"https://www.sofascore.com/football/match/{slug}/{match_code}"


def _persist_player_stats(settings: Settings, season: int, rows: list[dict[str, Any]]) -> None:
    if not rows:
        logger.warning("No player stat rows to persist")
        return

    out_dir = settings.processed_dir / str(season) / "players"

    # Full raw JSON
    write_json(
        out_dir / f"player_match_stats_{season}.json",
        {"season": season, "row_count": len(rows), "rows": rows},
    )

    write_csv(out_dir / f"player_match_stats_{season}.csv", rows)

    # Sport-only subset
    sport_rows = [r for r in rows if "Sport" in str(r.get("team_name", ""))]
    write_csv(out_dir / f"sport_{season}_player_match_stats.csv", sport_rows)

    logger.info(
        "Persisted %s player-match rows (%s Sport rows) to %s",
        len(rows), len(sport_rows), out_dir,
    )
