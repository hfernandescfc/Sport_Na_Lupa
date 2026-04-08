"""Fetch squad market values for all 20 Série B 2026 teams and build a
strength index combining market value + 2026 performance.

The strength score mirrors the formula used in generate_temporada_cards.py:
    strength_score = 0.60 * mv_score + 0.40 * perf_score   (when MV available)
    strength_score = perf_score                              (fallback)

where:
    mv_score   = (squad_market_value_eur - min) / (max - min)  [0-1]
    perf_score = perf_points_per_game / max(perf_points_per_game)  [0-1]

Output
------
  data/processed/{season}/matches/serie_b_{season}_team_strength.csv
"""
from __future__ import annotations

import datetime
import json
from typing import Any

import pandas as pd

from src.config import Settings
from src.discover.team_mapper import MANUAL_TEAM_MAPPINGS
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger
from src.utils.normalize import normalize_team_name


logger = get_logger(__name__)


# ── Selenium helpers (same pattern as sofascore_opponent_strength.py) ─────────

def _xhr_get(driver: Any, path: str) -> dict | None:
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
            logger.warning("XHR %s → HTTP %s", path, response.get("status"))
            return None
        return json.loads(response["body"])
    except Exception as exc:
        logger.warning("XHR failed for %s: %s", path, exc)
        return None


def _open_driver(options: Any) -> Any:
    from selenium import webdriver
    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)
    driver.get("https://www.sofascore.com/pt/football")
    return driver


def _make_options() -> Any:
    from selenium.webdriver.edge.options import Options
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    return opts


def _fetch_squad_market_value(driver: Any, team_id: int) -> dict[str, Any]:
    data = _xhr_get(driver, f"/api/v1/team/{team_id}/players")
    if not data:
        return {
            "squad_market_value_eur": None,
            "squad_avg_market_value_eur": None,
            "players_with_value": 0,
            "raw_player_count": 0,
        }

    players = data.get("players", [])
    values = []
    for entry in players:
        player = entry.get("player", entry)
        mv = player.get("proposedMarketValue") or player.get("marketValue")
        if mv and isinstance(mv, (int, float)) and mv > 0:
            values.append(mv)

    if not values:
        logger.warning("team_id=%s: no market values in %s players", team_id, len(players))
        return {
            "squad_market_value_eur": None,
            "squad_avg_market_value_eur": None,
            "players_with_value": 0,
            "raw_player_count": len(players),
        }

    return {
        "squad_market_value_eur": sum(values),
        "squad_avg_market_value_eur": round(sum(values) / len(values), 2),
        "players_with_value": len(values),
        "raw_player_count": len(players),
    }


# ── Performance proxy ──────────────────────────────────────────────────────────

def _build_performance_proxy(all_results_path: Any) -> dict[str, dict]:
    """Points per game and goal diff from all 2026 completed matches, keyed by
    canonical team_key."""
    try:
        df = pd.read_csv(all_results_path)
    except Exception as exc:
        logger.error("Could not read all_teams results: %s", exc)
        return {}

    completed = df.loc[df["is_completed"].eq(True)].copy()
    proxy: dict[str, dict] = {}

    all_raw_teams = set(completed["home_team"].tolist() + completed["away_team"].tolist())

    for raw_name in all_raw_teams:
        team_key = normalize_team_name(raw_name)

        home = completed.loc[completed["home_team"] == raw_name]
        away = completed.loc[completed["away_team"] == raw_name]

        gf = float(home["home_score"].sum() + away["away_score"].sum())
        ga = float(home["away_score"].sum() + away["home_score"].sum())

        hw = int((home["home_score"] > home["away_score"]).sum())
        hd = int((home["home_score"] == home["away_score"]).sum())
        aw = int((away["away_score"] > away["home_score"]).sum())
        ad = int((away["away_score"] == away["home_score"]).sum())

        wins = hw + aw
        draws = hd + ad
        games = len(home) + len(away)
        losses = games - wins - draws

        proxy[team_key] = {
            "perf_games": games,
            "perf_wins": wins,
            "perf_draws": draws,
            "perf_losses": losses,
            "perf_gf": int(gf),
            "perf_ga": int(ga),
            "perf_goal_diff": int(gf - ga),
            "perf_win_rate": round(wins / games, 3) if games > 0 else None,
            "perf_points_per_game": round((wins * 3 + draws) / games, 3) if games > 0 else None,
        }

    return proxy


# ── Main sync ─────────────────────────────────────────────────────────────────

def sync_serie_b_strength(settings: Settings, season: int) -> None:
    all_results_path = settings.processed_dir / str(season) / "all_teams" / "all_teams_results.csv"
    out_path = settings.processed_dir / str(season) / "matches" / f"serie_b_{season}_team_strength.csv"

    perf_proxy = _build_performance_proxy(all_results_path)
    logger.info("Performance proxy built for %s teams", len(perf_proxy))

    # Only process the 20 confirmed Série B teams
    serie_b_teams = {
        key: val
        for key, val in MANUAL_TEAM_MAPPINGS.items()
        if val.get("mapping_status") == "confirmed"
    }
    logger.info("Fetching market values for %s Série B teams", len(serie_b_teams))

    try:
        from selenium import webdriver  # noqa: F401
    except ImportError as exc:
        logger.error("Selenium not available: %s", exc)
        return

    options = _make_options()
    rows: list[dict[str, Any]] = []

    for team_key, mapping in sorted(serie_b_teams.items()):
        team_id = mapping["sofascore_team_id"]
        logger.info("Processing %s (id=%s)", team_key, team_id)
        driver = None
        try:
            driver = _open_driver(options)
            mv_data = _fetch_squad_market_value(driver, team_id)
            perf = perf_proxy.get(team_key, {})

            row = {
                "season": season,
                "team_key": team_key,
                "sofascore_team_id": team_id,
                "squad_market_value_eur": mv_data["squad_market_value_eur"],
                "squad_avg_market_value_eur": mv_data["squad_avg_market_value_eur"],
                "players_with_value": mv_data["players_with_value"],
                "raw_player_count": mv_data["raw_player_count"],
                **perf,
                "last_updated_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            rows.append(row)
            logger.info(
                "  market_value=%s  ppg=%s  games=%s",
                mv_data["squad_market_value_eur"],
                perf.get("perf_points_per_game"),
                perf.get("perf_games"),
            )
        except Exception as exc:
            logger.error("Failed processing %s: %s", team_key, exc)
        finally:
            if driver:
                driver.quit()

    write_csv(out_path, rows)
    logger.info("Série B team strength sync complete: %s teams -> %s", len(rows), out_path)
