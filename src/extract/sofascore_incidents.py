"""Extract match incidents from SofaScore via /api/v1/event/{event_id}/incidents.

Scope:
- Sport Recife: all completed matches across all competitions
- Série B 2026: all completed matches (all 20 clubs)

Each match yields:
  - High-level incidents: goals, cards, substitutions, injury time
  - For goals: footballPassingNetworkAction — the passing chain with (x, y) coordinates

Output (processed):
  data/processed/{season}/incidents/sport_incidents.json
  data/processed/{season}/incidents/serie_b_incidents.json
"""
from __future__ import annotations

import csv
import datetime
import json
import time
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def sync_incidents(settings: Settings, season: int) -> None:
    """Fetch incidents for Sport (all comps) + Série B (all clubs)."""
    match_rows = _collect_match_rows(settings, season)
    if not match_rows:
        logger.warning("No matches found to fetch incidents for season %s", season)
        return

    logger.info("Fetching incidents for %d matches", len(match_rows))

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
    options.add_argument("--disable-dev-shm-usage")

    sport_records: list[dict[str, Any]] = []
    serie_b_records: list[dict[str, Any]] = []

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
            payload = _fetch_incidents_json(driver, event_id)
            if payload is None:
                logger.warning("No incidents data for event_id=%s", event_id)
                continue

            record = {
                "event_id": event_id,
                "match_code": match.get("match_code"),
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "competition": match.get("competition"),
                "round": match.get("round"),
                "scope": match.get("scope"),
                "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
                "incidents": payload.get("incidents", []),
            }

            n_incidents = len(record["incidents"])
            n_goals = sum(1 for i in record["incidents"] if i.get("incidentType") == "goal")
            label = f"{match.get('home_team')} x {match.get('away_team')}"
            logger.info(
                "Incidents fetched for %s: %d incidents (%d goals)",
                label, n_incidents, n_goals,
            )

            if match.get("scope") == "sport_all":
                sport_records.append(record)
            else:
                serie_b_records.append(record)

        except Exception as exc:
            logger.warning("Failed incidents for event_id=%s: %s", event_id, exc)
        finally:
            driver.quit()

    out_dir = settings.processed_dir / str(season) / "incidents"
    now = datetime.datetime.utcnow().isoformat() + "Z"

    if sport_records:
        write_json(out_dir / "sport_incidents.json", {
            "season": season, "scope": "sport_all",
            "match_count": len(sport_records),
            "fetched_at": now,
            "matches": sport_records,
        })
        logger.info("Sport incidents saved: %d matches", len(sport_records))

    if serie_b_records:
        write_json(out_dir / "serie_b_incidents.json", {
            "season": season, "scope": "serie_b",
            "match_count": len(serie_b_records),
            "fetched_at": now,
            "matches": serie_b_records,
        })
        logger.info("Série B incidents saved: %d matches", len(serie_b_records))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_incidents_json(driver: Any, event_id: str) -> dict[str, Any] | None:
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/api/v1/event/" + arguments[0] + "/incidents", false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            event_id,
        )
        if response.get("status") != 200:
            logger.warning(
                "Incidents API status %s for event_id=%s", response.get("status"), event_id
            )
            return None
        return json.loads(response["body"])
    except Exception as exc:
        logger.warning("_fetch_incidents_json failed for event_id=%s: %s", event_id, exc)
        return None


def _collect_match_rows(settings: Settings, season: int) -> list[dict[str, Any]]:
    """Same match list used by sync_player_stats."""
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    # Sport — all completed matches
    sport_path = settings.processed_dir / str(season) / "sport" / f"sport_{season}_matches.csv"
    if sport_path.exists():
        with open(sport_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("is_completed", "").lower() != "true":
                    continue
                eid = r.get("event_id", "")
                if not eid or eid in seen:
                    continue
                seen.add(eid)
                rows.append({
                    "event_id": eid,
                    "match_url": r.get("match_url") or _build_match_url(
                        r.get("match_code", ""), r.get("home_team", ""), r.get("away_team", "")
                    ),
                    "home_team": r.get("home_team"),
                    "away_team": r.get("away_team"),
                    "competition": r.get("competition_name", "sport_all"),
                    "round": r.get("competition_round"),
                    "match_code": r.get("match_code"),
                    "scope": "sport_all",
                })
    else:
        logger.warning("Sport matches file not found: %s", sport_path)

    # Série B — all completed matches
    serie_b_path = settings.processed_dir / str(season) / "matches" / "match_ids.csv"
    if serie_b_path.exists():
        with open(serie_b_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("is_completed", "").lower() != "true":
                    continue
                eid = r.get("event_id", "")
                if not eid or eid in seen:
                    continue
                seen.add(eid)
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

    logger.info("Collected %d unique matches for incidents extraction", len(rows))
    return rows


def _build_match_url(match_code: str, home_team: str, away_team: str) -> str:
    if not match_code:
        return ""
    slug = f"{home_team.lower().replace(' ', '-')}-{away_team.lower().replace(' ', '-')}"
    return f"https://www.sofascore.com/football/match/{slug}/{match_code}"
