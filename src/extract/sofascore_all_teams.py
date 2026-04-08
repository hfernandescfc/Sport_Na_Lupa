from __future__ import annotations

import csv
import datetime
from typing import Any

from src.config import Settings
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


def sync_all_teams_stub(settings: Settings, season: int) -> None:
    """Fetch matches for all Série B clubs across all competitions.

    Matches and results are collected for every club.
    Advanced stats are NOT extracted here — Série B stats are already
    covered by the sync-matches command.
    """
    mapping_path = settings.processed_dir / str(season) / "clubs" / "club_mapping.csv"
    clubs = _load_club_mapping(mapping_path)

    if not clubs:
        logger.error("No clubs found at %s", mapping_path)
        return

    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except Exception as exc:
        logger.warning("Selenium not available for all-teams sync: %s", exc)
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    seen_codes: set[str] = set()
    all_matches: list[dict[str, Any]] = []

    for club in clubs:
        team_id = int(club["sofascore_team_id"])
        team_name = club["cbf_name"]
        team_url = club["sofascore_url"]

        logger.info("Fetching matches for %s (id=%s)", team_name, team_id)

        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)
        try:
            driver.get(team_url)
            matches = _fetch_all_matches_for_team(driver, team_id, season)
        except Exception as exc:
            logger.warning("Failed to fetch matches for %s: %s", team_name, exc)
            matches = []
        finally:
            driver.quit()

        new = 0
        for match in matches:
            code = match.get("match_code")
            if code and code not in seen_codes:
                seen_codes.add(code)
                all_matches.append(match)
                new += 1

        logger.info("%s: %s matches fetched, %s new unique", team_name, len(matches), new)

    all_matches.sort(key=lambda r: r.get("match_date_utc") or "")

    out_dir = settings.processed_dir / str(season) / "all_teams"
    write_csv(out_dir / "all_teams_matches.csv", all_matches)
    write_csv(
        out_dir / "all_teams_results.csv",
        [r for r in all_matches if r.get("is_completed")],
    )

    logger.info(
        "All-teams sync complete: %s unique matches across %s clubs",
        len(all_matches),
        len(clubs),
    )


def _load_club_mapping(path: Any) -> list[dict[str, str]]:
    try:
        with open(path, newline="", encoding="utf-8") as fh:
            return list(csv.DictReader(fh))
    except Exception as exc:
        logger.error("Could not read club mapping at %s: %s", path, exc)
        return []


def _fetch_all_matches_for_team(
    driver: Any,
    team_id: int,
    season_year: int,
) -> list[dict[str, Any]]:
    season_start = int(
        datetime.datetime(season_year, 1, 1, tzinfo=datetime.timezone.utc).timestamp()
    )
    season_end = int(
        datetime.datetime(season_year, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc).timestamp()
    )

    past = _paginate_team_events(driver, team_id, "last", season_start, season_end)
    future = _paginate_team_events(driver, team_id, "next", season_start, season_end)

    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for event in past + future:
        eid = event.get("id")
        if eid and eid not in seen:
            seen.add(eid)
            result.append(_parse_event_to_match_row(event, season_year))

    result.sort(key=lambda r: r.get("match_date_utc") or "")
    return result


def _parse_event_to_match_row(event: dict[str, Any], season: int) -> dict[str, Any]:
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
    match_url = (
        f"https://www.sofascore.com/football/match/{slug}/{custom_id}"
        if slug and custom_id
        else None
    )
    now = datetime.datetime.utcnow().isoformat() + "Z"

    return {
        "season": season,
        "competition_name": (
            tournament.get("name")
            or (tournament.get("uniqueTournament") or {}).get("name", "")
        ),
        "competition_round": round_info.get("round"),
        "match_code": custom_id,
        "match_date_utc": match_date_utc,
        "home_team": home_team.get("name", ""),
        "away_team": away_team.get("name", ""),
        "home_score": home_score_obj.get("current") if is_completed else None,
        "away_score": away_score_obj.get("current") if is_completed else None,
        "venue_name": venue.get("name", ""),
        "status": status,
        "is_completed": is_completed,
        "source": "sofascore_api",
        "source_url": match_url,
        "last_updated_at": now,
    }
