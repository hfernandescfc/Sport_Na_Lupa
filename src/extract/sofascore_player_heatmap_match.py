"""Fetch per-match player heatmaps for Sport players in Série B.

Endpoint: GET /api/v1/event/{event_id}/player/{player_id}/heatmap

Returns {x, y} points (0-100 scale) representing positioning frequency within
the match. Coordinates are already normalised by SofaScore so the team always
appears attacking toward x=100, regardless of home/away.

  x: 0 = own goal area  →  100 = opponent goal area
  y: 0 = right touchline  →  100 = left touchline  (from team's attacking view)

Output:
  data/processed/{season}/player_positions/sport_serie_b_heatmaps.json
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


def sync_player_positions(settings: Settings, season: int) -> None:
    """Fetch match heatmaps for all Sport players in completed Série B matches."""
    player_match_pairs = _collect_pairs(settings, season)
    if not player_match_pairs:
        logger.warning("No player-match pairs found for season %s", season)
        return

    logger.info(
        "Fetching heatmaps for %d player-match pairs across %d matches",
        len(player_match_pairs),
        len({p["event_id"] for p in player_match_pairs}),
    )

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

    # Group by match to open one browser session per match
    matches: dict[str, list[dict[str, Any]]] = {}
    for pair in player_match_pairs:
        matches.setdefault(pair["event_id"], []).append(pair)

    results: list[dict[str, Any]] = []

    for event_id, pairs in matches.items():
        match_url = pairs[0]["match_url"]
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)
        try:
            driver.get(match_url)
            time.sleep(3)

            match_results: list[dict[str, Any]] = []
            for pair in pairs:
                player_id = pair["player_id"]
                heatmap_pts = _fetch_heatmap(driver, event_id, player_id)
                centroid = _centroid(heatmap_pts)

                match_results.append({
                    **pair,
                    "n_points": len(heatmap_pts),
                    "avg_x": centroid["x"],
                    "avg_y": centroid["y"],
                    "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
                })

            results.extend(match_results)
            fetched = sum(1 for r in match_results if r["n_points"] > 0)
            label = f"{pairs[0]['home_team']} x {pairs[0]['away_team']}"
            logger.info(
                "R%s %s: %d/%d heatmaps fetched",
                pairs[0]["round"], label, fetched, len(pairs),
            )

        except Exception as exc:
            logger.warning("Failed heatmaps for event_id=%s: %s", event_id, exc)
        finally:
            driver.quit()

    out_dir = settings.processed_dir / str(season) / "player_positions"
    write_json(out_dir / "sport_serie_b_heatmaps.json", {
        "season": season,
        "scope": "sport_serie_b",
        "coordinate_system": {
            "x": "0=own_goal_area, 100=opponent_goal_area",
            "y": "0=right_touchline, 100=left_touchline (from team attacking perspective)",
        },
        "record_count": len(results),
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "records": results,
    })
    logger.info("Player positions saved: %d records", len(results))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_heatmap(driver: Any, event_id: str, player_id: int) -> list[dict[str, Any]]:
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open(
                "GET",
                "/api/v1/event/" + arguments[0] + "/player/" + arguments[1] + "/heatmap",
                false
            );
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            event_id,
            player_id,
        )
        if response.get("status") != 200:
            return []
        return json.loads(response["body"]).get("heatmap", [])
    except Exception as exc:
        logger.warning(
            "Heatmap fetch failed: event=%s player=%s: %s", event_id, player_id, exc
        )
        return []


def _centroid(points: list[dict[str, Any]]) -> dict[str, float | None]:
    """Simple mean of x and y coordinates."""
    valid = [p for p in points if p.get("x") is not None and p.get("y") is not None]
    if not valid:
        return {"x": None, "y": None}
    return {
        "x": round(sum(p["x"] for p in valid) / len(valid), 2),
        "y": round(sum(p["y"] for p in valid) / len(valid), 2),
    }


def _collect_pairs(settings: Settings, season: int) -> list[dict[str, Any]]:
    """Return player-match pairs for Sport players in Série B with >= 1 min played."""
    curated_path = settings.curated_dir / f"sport_{season}" / "player_match_stats.csv"
    if not curated_path.exists():
        logger.warning("Sport player stats not found: %s", curated_path)
        return []

    # Also need match_url — read from match_ids.csv
    match_urls: dict[str, str] = {}
    match_meta: dict[str, dict[str, Any]] = {}
    match_ids_path = settings.processed_dir / str(season) / "matches" / "match_ids.csv"
    if match_ids_path.exists():
        with open(match_ids_path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                eid = r.get("event_id", "")
                if eid:
                    match_urls[eid] = r.get("match_url", "")
                    match_meta[eid] = {
                        "home_team": r.get("home_team"),
                        "away_team": r.get("away_team"),
                        "match_code": r.get("match_code"),
                    }

    pairs: list[dict[str, Any]] = []
    with open(curated_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            # Only Série B, only players with >= 1 min
            comp = r.get("competition", "")
            if "serie_b" not in comp.lower() and "série b" not in comp.lower():
                continue
            try:
                mins = float(r.get("minutes_played") or 0)
            except ValueError:
                mins = 0
            if mins < 1:
                continue

            event_id = r.get("event_id", "")
            meta = match_meta.get(event_id, {})
            pairs.append({
                "season": season,
                "competition": r.get("competition"),
                "round": r.get("round"),
                "event_id": event_id,
                "match_code": r.get("match_code") or meta.get("match_code"),
                "match_label": f"{r.get('home_team')} x {r.get('away_team')}",
                "home_team": r.get("home_team"),
                "away_team": r.get("away_team"),
                "is_home": r.get("is_home"),
                "match_url": match_urls.get(event_id, ""),
                "player_id": int(r["player_id"]) if r.get("player_id") else None,
                "player_name": r.get("player_name"),
                "player_slug": r.get("player_slug"),
                "position": r.get("position"),
                "jersey_number": r.get("jersey_number"),
                "is_substitute": r.get("is_substitute"),
                "minutes_played": mins,
            })

    logger.info("Collected %d player-match pairs for Sport Série B", len(pairs))
    return pairs
