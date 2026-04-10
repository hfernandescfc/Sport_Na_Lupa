"""Fetch per-match player heatmaps and aggregate them into a team heatmap.

For each completed match of an opponent in a given competition, fetches:
  /api/v1/event/{event_id}/player/{player_id}/heatmap

for every player with significant minutes (>= MIN_MINUTES) and aggregates
all {x, y} points into a single team-level heatmap.

Coordinate system (per-match endpoint):
  x: 0=left touchline, 100=right touchline    (lateral)
  y: 0=own goal,       100=attacking goal      (depth)

Output:
  data/processed/{season}/opponents/{team_key}/team_heatmap.json

Usage:
    python -m src.main sync-team-heatmap --team-key avai --competition "Brasileirao Serie B" --season 2026
"""
from __future__ import annotations

import csv
import datetime
import json
import time
import unicodedata
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

MIN_MINUTES = 30   # only include players with >= this many minutes played


def sync_team_heatmap(
    settings: Settings,
    team_key: str,
    competition_filter: str,
    season: int,
) -> None:
    """Fetch per-match player heatmaps and save an aggregated team heatmap."""

    player_stats_path = (
        settings.processed_dir / str(season) / "opponents" / team_key
        / "player_match_stats.csv"
    )
    if not player_stats_path.exists():
        logger.error(
            "player_match_stats.csv not found at %s — run sync-opponent first.",
            player_stats_path,
        )
        return

    rows = _read_csv(player_stats_path)

    # Filter: only opponent's own players, only in target competition, only completed
    cf_norm = _normalize(competition_filter)
    target_rows = [
        r for r in rows
        if cf_norm in _normalize(r.get("competition", ""))
        and _is_avai_player(r, team_key)
        and _minutes(r) >= MIN_MINUTES
    ]

    if not target_rows:
        logger.warning(
            "[%s] No player rows found for competition='%s'. "
            "Available competitions: %s",
            team_key, competition_filter,
            {r.get("competition") for r in rows},
        )
        return

    # Build unique (event_id, player_id, source_url) list — one request per combo
    combos: dict[tuple[int, int], dict[str, Any]] = {}
    for r in target_rows:
        eid = _int(r.get("event_id"))
        pid = _int(r.get("player_id"))
        if eid and pid:
            combos[(eid, pid)] = r

    logger.info(
        "[%s] Fetching heatmaps for %d player-match combos (%d players, %d matches)",
        team_key,
        len(combos),
        len({pid for _, pid in combos}),
        len({eid for eid, _ in combos}),
    )

    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except ImportError:
        logger.warning("Selenium not available — aborting sync-team-heatmap.")
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)

    all_points: list[dict[str, Any]] = []
    seen_events: set[int] = set()

    try:
        # Group by event to avoid reloading the page for every player
        events: dict[int, list[tuple[int, dict]]] = {}
        for (eid, pid), row in combos.items():
            events.setdefault(eid, []).append((pid, row))

        for eid, players in events.items():
            # Load page once per match (needed for session/cookies)
            source_url = players[0][1].get("source_url", "") if players else ""
            if not source_url:
                # Reconstruct from match_code
                mc = players[0][1].get("match_code", "")
                home = players[0][1].get("home_team", "").lower().replace(" ", "-")
                away = players[0][1].get("away_team", "").lower().replace(" ", "-")
                source_url = f"https://www.sofascore.com/football/match/{home}-{away}/{mc}"

            if eid not in seen_events:
                try:
                    driver.get(source_url)
                    time.sleep(1.5)
                except Exception as exc:
                    logger.warning("Page load failed for event=%s: %s", eid, exc)
                seen_events.add(eid)

            for pid, row in players:
                pts = _fetch_player_heatmap(driver, eid, pid)
                player_name = row.get("player_name", str(pid))
                position    = row.get("position", "?")
                for pt in pts:
                    all_points.append({
                        "x":          pt.get("x"),
                        "y":          pt.get("y"),
                        "event_id":   eid,
                        "player_id":  pid,
                        "player_name": player_name,
                        "position":   position,
                    })
                logger.info(
                    "  %s (%s) event=%s → %d pts", player_name, position, eid, len(pts)
                )

    finally:
        driver.quit()

    out_dir  = settings.processed_dir / str(season) / "opponents" / team_key
    now      = datetime.datetime.utcnow().isoformat() + "Z"
    payload  = {
        "team_key":          team_key,
        "season":            season,
        "competition":       competition_filter,
        "total_points":      len(all_points),
        "player_count":      len({p["player_id"] for p in all_points}),
        "match_count":       len({p["event_id"]  for p in all_points}),
        "fetched_at":        now,
        "points":            all_points,
    }
    write_json(out_dir / "team_heatmap.json", payload)
    logger.info(
        "[%s] Team heatmap saved — %d points, %d players, %d matches",
        team_key, len(all_points),
        payload["player_count"], payload["match_count"],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_player_heatmap(driver: Any, event_id: int, player_id: int) -> list[dict]:
    url = f"/api/v1/event/{event_id}/player/{player_id}/heatmap"
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
        logger.warning("XHR failed event=%s player=%s: %s", event_id, player_id, exc)
        return []

    if result.get("status") != 200:
        return []

    try:
        body = json.loads(result["body"])
        return body.get("heatmap", [])
    except Exception:
        return []


def _is_avai_player(row: dict, team_key: str) -> bool:
    """Return True if this row belongs to the opponent team."""
    team_name = _normalize(row.get("team_name", ""))
    key_part  = _normalize(team_key.split("-")[0])
    return key_part in team_name


def _minutes(row: dict) -> int:
    try:
        return int(float(row.get("minutes_played", 0) or 0))
    except (ValueError, TypeError):
        return 0


def _int(val: Any) -> int | None:
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _normalize(text: str) -> str:
    """Lowercase + strip accents for fuzzy competition matching."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        logger.error("Could not read %s: %s", path, exc)
        return []
