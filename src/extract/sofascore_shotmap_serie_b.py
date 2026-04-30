"""Extract shotmap data for all completed Série B matches.

Endpoint: /api/v1/event/{event_id}/shotmap
Each shot record includes: shotType, situation, bodyPart, playerCoordinates, xg, xgot, time, isHome.

The `situation` field is the key data for visualising how teams create chances:
  - "regular"       — from open play / constructed attack
  - "fastBreak"     — counter-attack / transition
  - "corner"        — corner kick
  - "fromSet"       — free kick set piece
  - "penalty"       — penalty

Incremental: on each run the existing JSON is read, already-fetched event_ids are
skipped, and new records are merged before saving.

Auto-detect: when to_round is None the function detects the latest round where
every match in match_ids.csv is marked is_completed=True.

Output:
  data/processed/{season}/shotmaps/serie_b_shotmaps.json
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


def sync_shotmap_serie_b(
    settings: Settings,
    season: int,
    from_round: int = 1,
    to_round: int | None = None,
) -> None:
    """Fetch shotmaps for all completed Série B matches up to to_round.

    When to_round is None, auto-detects the latest fully-completed round.
    Runs incrementally: matches already present in the output JSON are skipped.
    """
    effective_to = to_round if to_round is not None else _detect_latest_completed_round(
        settings, season
    )
    if effective_to is None:
        logger.warning("No fully completed rounds found for season %s — nothing to fetch", season)
        return

    logger.info("Shotmap sync: rounds %s–%s (season %s)", from_round, effective_to, season)

    # Load existing records for incremental skip
    out_path = settings.processed_dir / str(season) / "shotmaps" / "serie_b_shotmaps.json"
    existing_records, already_fetched = _load_existing(out_path)
    if already_fetched:
        logger.info("Incremental: %d matches already fetched — will skip", len(already_fetched))

    match_rows = _collect_match_rows(
        settings, season,
        from_round=from_round,
        to_round=effective_to,
        skip_event_ids=already_fetched,
    )
    if not match_rows:
        logger.info("Shotmap sync: no new matches to fetch (all up to R%s already loaded)", effective_to)
        return

    logger.info("Fetching shotmaps for %d new matches", len(match_rows))

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

    new_records: list[dict[str, Any]] = []

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
            shots = _fetch_shotmap(driver, event_id)
            if shots is None:
                logger.warning("No shotmap data for event_id=%s", event_id)
                continue

            label = f"{match['home_team']} x {match['away_team']}"
            logger.info(
                "Shotmap fetched for R%s %s: %d shots",
                match["round"], label, len(shots),
            )

            new_records.append({
                "event_id": event_id,
                "match_code": match.get("match_code"),
                "round": match["round"],
                "home_team": match["home_team"],
                "away_team": match["away_team"],
                "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
                "shots": _parse_shots(shots, event_id, match),
            })

        except Exception as exc:
            logger.warning("Failed shotmap for event_id=%s: %s", event_id, exc)
        finally:
            driver.quit()

    all_records = existing_records + new_records
    all_records.sort(key=lambda r: (r.get("round", 0), r.get("event_id", "")))

    write_json(out_path, {
        "season": season,
        "scope": "serie_b",
        "to_round": effective_to,
        "match_count": len(all_records),
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "matches": all_records,
    })
    logger.info(
        "Série B shotmaps saved: %d total matches (%d new) → %s",
        len(all_records), len(new_records), out_path,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_latest_completed_round(settings: Settings, season: int) -> int | None:
    """Max round where every match in match_ids.csv is is_completed=True."""
    serie_b_path = settings.processed_dir / str(season) / "matches" / "match_ids.csv"
    if not serie_b_path.exists():
        return None

    round_total: dict[int, int] = {}
    round_done: dict[int, int] = {}

    with open(serie_b_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                rnd = int(r.get("round", 0))
            except (ValueError, TypeError):
                continue
            round_total[rnd] = round_total.get(rnd, 0) + 1
            if r.get("is_completed", "").lower() == "true":
                round_done[rnd] = round_done.get(rnd, 0) + 1

    full_rounds = [
        rnd for rnd, total in round_total.items()
        if round_done.get(rnd, 0) == total
    ]
    if not full_rounds:
        return None
    latest = max(full_rounds)
    logger.info("Auto-detected latest fully-completed round: R%s", latest)
    return latest


def _load_existing(out_path: Path) -> tuple[list[dict[str, Any]], set[str]]:
    """Return (existing_match_records, set_of_already_fetched_event_ids)."""
    if not out_path.exists():
        return [], set()
    try:
        data = json.loads(out_path.read_text(encoding="utf-8"))
        records = data.get("matches", [])
        return records, {str(r["event_id"]) for r in records if r.get("event_id")}
    except Exception as exc:
        logger.warning("Could not read existing shotmaps file: %s", exc)
        return [], set()


def _fetch_shotmap(driver: Any, event_id: str) -> list[dict[str, Any]] | None:
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/api/v1/event/" + arguments[0] + "/shotmap", false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            event_id,
        )
        if response.get("status") != 200:
            logger.warning(
                "Shotmap API status %s for event_id=%s", response.get("status"), event_id
            )
            return None
        data = json.loads(response["body"])
        return data.get("shotmap", [])
    except Exception as exc:
        logger.warning("_fetch_shotmap failed for event_id=%s: %s", event_id, exc)
        return None


def _parse_shots(
    raw_shots: list[dict[str, Any]],
    event_id: str,
    match: dict[str, Any],
) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for shot in raw_shots:
        coords = shot.get("playerCoordinates") or {}
        block_coords = shot.get("blockCoordinates") or {}
        player = shot.get("player") or {}
        is_home = shot.get("isHome", False)
        parsed.append({
            "event_id": event_id,
            "round": match["round"],
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "team_name": match["home_team"] if is_home else match["away_team"],
            "is_home": is_home,
            "shot_type": shot.get("shotType", ""),
            "situation": shot.get("situation", ""),
            "body_part": shot.get("bodyPart", ""),
            "player_x": coords.get("x"),
            "player_y": coords.get("y"),
            "block_x": block_coords.get("x"),
            "block_y": block_coords.get("y"),
            "xg": shot.get("xg"),
            "xgot": shot.get("xgot"),
            "minute": shot.get("time"),
            "added_time": shot.get("addedTime"),
            "player_name": player.get("shortName", ""),
            "player_id": player.get("id"),
            "goal_type": shot.get("goalType", ""),
        })
    return parsed


def _collect_match_rows(
    settings: Settings,
    season: int,
    from_round: int,
    to_round: int,
    skip_event_ids: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    serie_b_path = settings.processed_dir / str(season) / "matches" / "match_ids.csv"

    if not serie_b_path.exists():
        logger.warning("Série B match_ids file not found: %s", serie_b_path)
        return rows

    skipped = 0
    with open(serie_b_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("is_completed", "").lower() != "true":
                continue
            try:
                rnd = int(r.get("round", 0))
            except (ValueError, TypeError):
                continue
            if rnd < from_round or rnd > to_round:
                continue
            eid = r.get("event_id", "")
            if not eid:
                continue
            if eid in skip_event_ids:
                skipped += 1
                continue
            rows.append({
                "event_id": eid,
                "match_url": r.get("match_url", ""),
                "home_team": r.get("home_team", ""),
                "away_team": r.get("away_team", ""),
                "round": rnd,
                "match_code": r.get("match_code", ""),
            })

    logger.info(
        "Collected %d new matches (skipped %d already fetched) for rounds %s-%s",
        len(rows), skipped, from_round, to_round,
    )
    return rows
