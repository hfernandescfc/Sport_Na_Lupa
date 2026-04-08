"""Extract player heatmap data from SofaScore.

Endpoint:
  GET /api/v1/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/heatmap

Returns a list of {x, y, count} points (0-100 scale) representing
the player's positioning frequency across the season.
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from src.utils.io import write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def fetch_player_heatmap(
    player_id: int,
    tournament_id: int,
    season_id: int,
) -> list[dict[str, Any]]:
    """Fetch heatmap points for a player in a given tournament/season.

    Returns list of {x, y, count} dicts, or empty list on failure.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except ImportError:
        logger.warning("Selenium not available — skipping heatmap fetch.")
        return []

    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Edge(options=opts)
    try:
        driver.get("https://www.sofascore.com")
        url = (
            f"/api/v1/player/{player_id}"
            f"/unique-tournament/{tournament_id}"
            f"/season/{season_id}/heatmap"
        )
        result = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", arguments[0], false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            url,
        )
        if result["status"] != 200:
            logger.warning(
                "Heatmap fetch failed: player=%s tournament=%s season=%s status=%s",
                player_id, tournament_id, season_id, result["status"],
            )
            return []
        data = json.loads(result["body"])
        return data.get("points", [])
    except Exception as exc:
        logger.warning("Heatmap fetch error: %s", exc)
        return []
    finally:
        driver.quit()


def save_player_heatmap(
    player_id: int,
    player_slug: str,
    tournament_id: int,
    season_id: int,
    season_label: str,
    output_dir: Path,
) -> Path | None:
    """Fetch and persist heatmap JSON. Returns the saved path or None."""
    points = fetch_player_heatmap(player_id, tournament_id, season_id)
    if not points:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    slug = f"{player_slug}_t{tournament_id}_s{season_id}"
    out_path = output_dir / f"{slug}_heatmap.json"

    payload = {
        "player_id": player_id,
        "player_slug": player_slug,
        "tournament_id": tournament_id,
        "season_id": season_id,
        "season_label": season_label,
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "points": points,
    }
    write_json(payload, out_path)
    logger.info("Heatmap saved: %s (%d points)", out_path, len(points))
    return out_path
