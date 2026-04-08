"""Extract all match data for a specific opponent team.

Fetches across all competitions in the season:
1. All matches (results + fixtures)
2. Advanced team stats for each completed match
3. Individual player stats for each completed match

Output: data/processed/{season}/opponents/{team_key}/
  - matches.csv
  - team_match_stats.csv
  - player_match_stats.csv

Usage:
    python -m src.main sync-opponent --team-key vila-nova --team-id 2021 --season 2026
"""
from __future__ import annotations

import datetime
import json
import time
from typing import Any

from src.config import Settings
from src.extract.sofascore_match import extract_team_stats_for_matches
from src.extract.sofascore_player_stats import (
    _fetch_lineups_json,
    _parse_lineups_payload,
)
from src.extract.sofascore_sport import (
    _fetch_team_events_json,
    _paginate_team_events,
)
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger


logger = get_logger(__name__)

_SOFASCORE_STATUS_MAP = {
    "finished": "completed",
    "inprogress": "in_progress",
    "notstarted": "scheduled",
    "postponed": "postponed",
    "canceled": "canceled",
}


def sync_opponent(
    settings: Settings,
    team_key: str,
    team_id: int,
    season: int,
) -> None:
    """Fetch all match data (matches + team stats + player stats) for one opponent."""
    team_url = f"https://www.sofascore.com/pt/football/team/{team_key}/{team_id}"
    out_dir = settings.processed_dir / str(season) / "opponents" / team_key

    logger.info("Syncing opponent %s (id=%s) for season %s", team_key, team_id, season)

    # 1. Matches (all competitions)
    matches = _fetch_opponent_matches(team_url, team_id, season)
    if not matches:
        logger.warning("No matches found for %s", team_key)
        return

    write_csv(out_dir / "matches.csv", matches)
    logger.info("%s matches fetched for %s", len(matches), team_key)

    # 2. Advanced team stats — completed matches only
    completed = [m for m in matches if m.get("is_completed")]
    logger.info("Fetching team stats for %s completed matches", len(completed))

    now = datetime.datetime.utcnow().isoformat() + "Z"
    stats_input = [
        {
            "match_url": m["source_url"],
            "match_code": m["match_code"],
            "home_team": m["home_team"],
            "away_team": m["away_team"],
            "season": season,
            "competition": m.get("competition_name"),
            "round": m.get("competition_round"),
            "last_updated_at": m.get("last_updated_at", now),
        }
        for m in completed
        if m.get("source_url") and m.get("match_code")
    ]

    team_stats = extract_team_stats_for_matches(stats_input)
    if team_stats:
        write_csv(out_dir / "team_match_stats.csv", team_stats)
        logger.info("Team stats: %s rows", len(team_stats))

    # 3. Player stats — completed matches only
    logger.info("Fetching player stats for %s completed matches", len(completed))
    player_rows = _fetch_player_stats(completed, season)
    if player_rows:
        write_csv(out_dir / "player_match_stats.csv", player_rows)
        logger.info("Player stats: %s rows", len(player_rows))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_opponent_matches(
    team_url: str, team_id: int, season: int
) -> list[dict[str, Any]]:
    """Open one Edge driver, paginate team events, return parsed match rows."""
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except Exception as exc:
        logger.warning("Selenium not available: %s", exc)
        return []

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    season_start = int(
        datetime.datetime(season, 1, 1, tzinfo=datetime.timezone.utc).timestamp()
    )
    season_end = int(
        datetime.datetime(season, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc).timestamp()
    )

    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)
    try:
        driver.get(team_url)
        past = _paginate_team_events(driver, team_id, "last", season_start, season_end)
        future = _paginate_team_events(driver, team_id, "next", season_start, season_end)
    except Exception as exc:
        logger.warning("Failed to paginate events for team_id=%s: %s", team_id, exc)
        return []
    finally:
        driver.quit()

    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for event in past + future:
        eid = event.get("id")
        if eid and eid not in seen:
            seen.add(eid)
            result.append(_parse_opponent_event(event, season))

    result.sort(key=lambda r: r.get("match_date_utc") or "")
    return result


def _parse_opponent_event(event: dict[str, Any], season: int) -> dict[str, Any]:
    """Parse a raw SofaScore event into a match row, including numeric event_id."""
    ts = event.get("startTimestamp", 0)
    match_date_utc = (
        datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None
    )

    status_type = (event.get("status") or {}).get("type", "notstarted")
    status = _SOFASCORE_STATUS_MAP.get(status_type, status_type)
    is_completed = status == "completed"

    home_team = event.get("homeTeam") or {}
    away_team = event.get("awayTeam") or {}
    home_score_obj = event.get("homeScore") or {}
    away_score_obj = event.get("awayScore") or {}
    venue = event.get("venue") or {}
    round_info = event.get("roundInfo") or {}
    tournament = event.get("tournament") or {}

    custom_id = event.get("customId", "")
    slug = event.get("slug", "")
    source_url = (
        f"https://www.sofascore.com/football/match/{slug}/{custom_id}"
        if slug and custom_id
        else None
    )

    return {
        "season": season,
        "competition_name": (
            tournament.get("name")
            or (tournament.get("uniqueTournament") or {}).get("name", "")
        ),
        "competition_round": round_info.get("round"),
        "event_id": event.get("id"),
        "match_code": custom_id,
        "match_date_utc": match_date_utc,
        "home_team": home_team.get("name", ""),
        "away_team": away_team.get("name", ""),
        "home_score": home_score_obj.get("current") if is_completed else None,
        "away_score": away_score_obj.get("current") if is_completed else None,
        "venue_name": venue.get("name", ""),
        "status": status,
        "is_completed": is_completed,
        "source_url": source_url,
        "last_updated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }


def _fetch_player_stats(
    completed_matches: list[dict[str, Any]], season: int
) -> list[dict[str, Any]]:
    """Fetch individual player stats for a list of completed matches."""
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except Exception as exc:
        logger.warning("Selenium not available for player stats: %s", exc)
        return []

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    all_rows: list[dict[str, Any]] = []

    for match in completed_matches:
        event_id = match.get("event_id")
        source_url = match.get("source_url")
        if not event_id or not source_url:
            logger.warning(
                "Skipping player stats — missing event_id or source_url: match_code=%s",
                match.get("match_code"),
            )
            continue

        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)
        try:
            driver.get(source_url)
            time.sleep(3)
            payload = _fetch_lineups_json(driver, str(event_id))
            if payload is None:
                logger.warning("No lineups payload for event_id=%s", event_id)
                continue

            match_ctx = {
                "event_id": event_id,
                "match_code": match.get("match_code"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "competition": match.get("competition_name"),
                "round": match.get("competition_round"),
            }
            rows = _parse_lineups_payload(payload, match_ctx, season)
            all_rows.extend(rows)
            logger.info(
                "Player stats: %s x %s → %s rows",
                match.get("home_team"),
                match.get("away_team"),
                len(rows),
            )
        except Exception as exc:
            logger.warning("Player stats failed for event_id=%s: %s", event_id, exc)
        finally:
            driver.quit()

    return all_rows
