"""Extract rich per-player match statistics from SofaScore.

Endpoint: GET /api/v1/event/{event_id}/player/{player_id}/statistics

Returns detailed per-match stats including pass zones, progression distance,
carries, crosses, and defensive actions — much richer than the lineups endpoint.

Key fields not available in lineups:
  - totalProgression: total distance progressed toward opponent goal (passes + carries)
  - totalProgressiveBallCarriesDistance: progression from carries only
  - progressiveBallCarriesCount: number of progressive carries
  - accurateOwnHalfPasses / totalOwnHalfPasses: pass accuracy in own half
  - accurateOppositionHalfPasses / totalOppositionHalfPasses: pass accuracy in opp half
  - totalCross / accurateCross: cross statistics
  - keyPass: key passes
  - bestBallCarryProgression: longest single progressive carry
"""
from __future__ import annotations

import datetime
import json
import time
from pathlib import Path
from typing import Any

from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


# All statistics fields we extract from the response
STAT_FIELDS = [
    # Passes aggregate
    "total_pass",
    "accurate_pass",
    "total_long_balls",
    "accurate_long_balls",
    "goal_assist",
    "key_pass",
    "total_cross",
    "accurate_cross",
    # Pass zones
    "accurate_own_half_passes",
    "total_own_half_passes",
    "accurate_opposition_half_passes",
    "total_opposition_half_passes",
    # Progression
    "total_progression",
    "total_ball_carries_distance",
    "total_progressive_ball_carries_distance",
    "progressive_ball_carries_count",
    "best_ball_carry_progression",
    "ball_carries_count",
    # Shots
    "total_shots",
    "shots_on_target",
    # Defensive
    "aerial_won",
    "duel_lost",
    "duel_won",
    "challenge_lost",
    "dispossessed",
    "total_clearance",
    "interception_won",
    "ball_recovery",
    # General
    "touches",
    "possession_lost_ctrl",
    "fouls",
    "was_fouled",
    "minutes_played",
    "rating",
    "expected_assists",
    # Normalized values
    "pass_value_normalized",
    "dribble_value_normalized",
    "defensive_value_normalized",
    "goalkeeper_value_normalized",
]

# API camelCase → snake_case
_API_KEY_MAP = {
    "totalPass": "total_pass",
    "accuratePass": "accurate_pass",
    "totalLongBalls": "total_long_balls",
    "accurateLongBalls": "accurate_long_balls",
    "goalAssist": "goal_assist",
    "keyPass": "key_pass",
    "totalCross": "total_cross",
    "accurateCross": "accurate_cross",
    "accurateOwnHalfPasses": "accurate_own_half_passes",
    "totalOwnHalfPasses": "total_own_half_passes",
    "accurateOppositionHalfPasses": "accurate_opposition_half_passes",
    "totalOppositionHalfPasses": "total_opposition_half_passes",
    "totalProgression": "total_progression",
    "totalBallCarriesDistance": "total_ball_carries_distance",
    "totalProgressiveBallCarriesDistance": "total_progressive_ball_carries_distance",
    "progressiveBallCarriesCount": "progressive_ball_carries_count",
    "bestBallCarryProgression": "best_ball_carry_progression",
    "ballCarriesCount": "ball_carries_count",
    "totalShots": "total_shots",
    "onTargetScoringAttempt": "shots_on_target",
    "aerialWon": "aerial_won",
    "duelLost": "duel_lost",
    "duelWon": "duel_won",
    "challengeLost": "challenge_lost",
    "dispossessed": "dispossessed",
    "totalClearance": "total_clearance",
    "interceptionWon": "interception_won",
    "ballRecovery": "ball_recovery",
    "touches": "touches",
    "possessionLostCtrl": "possession_lost_ctrl",
    "fouls": "fouls",
    "wasFouled": "was_fouled",
    "minutesPlayed": "minutes_played",
    "rating": "rating",
    "expectedAssists": "expected_assists",
    "passValueNormalized": "pass_value_normalized",
    "dribbleValueNormalized": "dribble_value_normalized",
    "defensiveValueNormalized": "defensive_value_normalized",
    "goalkeeperValueNormalized": "goalkeeper_value_normalized",
}


def fetch_player_match_stats(
    driver: Any,
    event_id: str | int,
    player_id: str | int,
) -> dict[str, Any] | None:
    """Fetch player statistics for a specific match via XHR.

    Requires a Selenium driver already navigated to the SofaScore domain
    (for session cookies). Returns the raw parsed JSON or None on failure.
    """
    path = f"/api/v1/event/{event_id}/player/{player_id}/statistics"
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", arguments[0], false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            path,
        )
        if response.get("status") != 200:
            logger.warning(
                "Player stats fetch status %s: event=%s player=%s",
                response.get("status"), event_id, player_id,
            )
            return None
        return json.loads(response["body"])
    except Exception as exc:
        logger.warning("fetch_player_match_stats failed: event=%s player=%s: %s", event_id, player_id, exc)
        return None


def parse_player_match_stats(
    payload: dict[str, Any],
    event_id: str | int,
    match_meta: dict[str, Any],
) -> dict[str, Any]:
    """Parse the /statistics response into a flat row dict."""
    now = datetime.datetime.utcnow().isoformat() + "Z"
    player = payload.get("player") or {}
    team = payload.get("team") or {}
    raw_stats = payload.get("statistics") or {}

    row: dict[str, Any] = {
        "event_id": str(event_id),
        "match_code": match_meta.get("match_code"),
        "season": match_meta.get("season"),
        "competition": match_meta.get("competition"),
        "round": match_meta.get("round"),
        "home_team": match_meta.get("home_team"),
        "away_team": match_meta.get("away_team"),
        "player_id": player.get("id"),
        "player_name": player.get("name"),
        "player_slug": player.get("slug"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
        "position": payload.get("position"),
        "last_updated_at": now,
    }

    for api_key, field in _API_KEY_MAP.items():
        row[field] = raw_stats.get(api_key)

    # Derived: progressive pass distance (progression minus carries)
    total_prog = row.get("total_progression")
    carry_prog = row.get("total_progressive_ball_carries_distance")
    if total_prog is not None and carry_prog is not None:
        row["progressive_pass_distance"] = round(total_prog - carry_prog, 4)
    else:
        row["progressive_pass_distance"] = None

    return row


def fetch_match_player_stats_batch(
    event_id: str | int,
    player_ids: list[int],
    match_url: str,
    match_meta: dict[str, Any],
    output_path: Path | None = None,
    delay_seconds: float = 0.5,
) -> list[dict[str, Any]]:
    """Fetch statistics for multiple players in a single match.

    Opens one browser session, navigates to the match page, then
    fetches each player's statistics endpoint sequentially.

    Args:
        event_id: SofaScore event ID.
        player_ids: List of player IDs to fetch.
        match_url: Full URL of the match page (for session/cookies).
        match_meta: Dict with season, competition, round, home_team, away_team, match_code.
        output_path: If provided, saves results as JSON.
        delay_seconds: Pause between XHR calls to avoid rate limiting.

    Returns:
        List of flat row dicts, one per player.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except ImportError as exc:
        logger.warning("Selenium not available: %s", exc)
        return []

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(30)

    rows: list[dict[str, Any]] = []
    try:
        driver.get(match_url)
        time.sleep(3)

        for player_id in player_ids:
            payload = fetch_player_match_stats(driver, event_id, player_id)
            if payload is None:
                logger.warning("No data for event=%s player=%s", event_id, player_id)
                continue
            row = parse_player_match_stats(payload, event_id, match_meta)
            rows.append(row)
            logger.info(
                "Fetched: %s (event=%s) - progression=%.1fm passes=%s/%s",
                row.get("player_name"),
                event_id,
                row.get("total_progression") or 0,
                row.get("accurate_pass"),
                row.get("total_pass"),
            )
            if delay_seconds > 0:
                time.sleep(delay_seconds)

    finally:
        driver.quit()

    if output_path and rows:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"event_id": str(event_id), "row_count": len(rows), "rows": rows},
                       indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("Saved %s player stats rows to %s", len(rows), output_path)

    return rows
