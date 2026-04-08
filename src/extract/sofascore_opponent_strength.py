"""Fetch opponent squad market values and performance proxies for Sport Recife 2026."""
from __future__ import annotations

import datetime
import json
from typing import Any

import pandas as pd

from src.config import Settings
from src.utils.io import write_csv, write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

TEAM_NAME = "Sport Recife"


# ── Selenium helpers ──────────────────────────────────────────────────────────

def _xhr_get(driver: Any, path: str) -> dict | None:
    """Synchronous XHR GET against the Sofascore internal API."""
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


# ── Step 1 — get opponent team IDs from event ─────────────────────────────────

def _fetch_team_id_from_event(driver: Any, event_id: int, opponent_name: str) -> int | None:
    data = _xhr_get(driver, f"/api/v1/event/{event_id}")
    if not data:
        return None
    event = data.get("event", {})
    home = event.get("homeTeam", {})
    away = event.get("awayTeam", {})
    for team in [home, away]:
        if team.get("name", "").lower() == opponent_name.lower():
            return team.get("id")
    # fallback: return whichever isn't Sport
    for team in [home, away]:
        if TEAM_NAME.lower() not in team.get("name", "").lower():
            return team.get("id")
    return None


# ── Step 2 — fetch squad market values ───────────────────────────────────────

def _fetch_squad_market_value(driver: Any, team_id: int) -> dict[str, Any]:
    """Returns squad total and avg market value (EUR) from the players endpoint."""
    data = _xhr_get(driver, f"/api/v1/team/{team_id}/players")
    if not data:
        return {"squad_market_value_eur": None, "squad_avg_market_value_eur": None,
                "players_with_value": 0, "raw_player_count": 0}

    players = data.get("players", [])
    values = []
    for entry in players:
        player = entry.get("player", entry)
        mv = player.get("proposedMarketValue") or player.get("marketValue")
        if mv and isinstance(mv, (int, float)) and mv > 0:
            values.append(mv)

    if not values:
        logger.warning("team_id=%s: no market values found in %s players", team_id, len(players))
        return {
            "squad_market_value_eur": None,
            "squad_avg_market_value_eur": None,
            "players_with_value": 0,
            "raw_player_count": len(players),
        }

    return {
        "squad_market_value_eur": sum(values),
        "squad_avg_market_value_eur": sum(values) / len(values),
        "players_with_value": len(values),
        "raw_player_count": len(players),
    }


# ── Step 3 — performance proxy from all_teams_results ────────────────────────

def _build_performance_proxy(all_results_path: Any) -> dict[str, dict]:
    """Win rate + goal diff from all 2026 matches for each team."""
    try:
        df = pd.read_csv(all_results_path)
    except Exception as exc:
        logger.error("Could not read all_teams results: %s", exc)
        return {}

    completed = df.loc[df["is_completed"].eq(True)].copy()
    proxy: dict[str, dict] = {}

    all_teams = set(completed["home_team"].tolist() + completed["away_team"].tolist())
    for team in all_teams:
        home_games = completed.loc[completed["home_team"] == team]
        away_games = completed.loc[completed["away_team"] == team]

        gf = home_games["home_score"].sum() + away_games["away_score"].sum()
        ga = home_games["away_score"].sum() + away_games["home_score"].sum()

        hw = (home_games["home_score"] > home_games["away_score"]).sum()
        hd = (home_games["home_score"] == home_games["away_score"]).sum()
        aw = (away_games["away_score"] > away_games["home_score"]).sum()
        ad = (away_games["away_score"] == away_games["home_score"]).sum()

        wins = hw + aw
        draws = hd + ad
        games = len(home_games) + len(away_games)
        losses = games - wins - draws

        proxy[team] = {
            "perf_games": int(games),
            "perf_wins": int(wins),
            "perf_draws": int(draws),
            "perf_losses": int(losses),
            "perf_gf": int(gf),
            "perf_ga": int(ga),
            "perf_goal_diff": int(gf - ga),
            "perf_win_rate": round(wins / games, 3) if games > 0 else None,
            "perf_points_per_game": round((wins * 3 + draws) / games, 3) if games > 0 else None,
        }

    return proxy


# ── Main sync function ────────────────────────────────────────────────────────

def sync_opponent_strength(settings: Settings, season: int) -> None:
    matches_path = settings.raw_dir / "sofascore" / "sport" / f"sport_{season}_matches_api.json"
    all_results_path = settings.processed_dir / str(season) / "all_teams" / "all_teams_results.csv"
    out_dir = settings.processed_dir / str(season) / "sport"

    # Load Sport matches
    try:
        with open(matches_path, encoding="utf-8") as f:
            raw_matches = json.load(f)
    except Exception as exc:
        logger.error("Could not read matches API: %s", exc)
        return

    # Build unique opponent → event_id mapping
    opp_events: dict[str, int] = {}
    for m in raw_matches:
        if not m.get("is_completed"):
            continue
        home, away = m.get("home_team", ""), m.get("away_team", "")
        opp = away if home == TEAM_NAME else home
        eid = m.get("event_id")
        if opp and eid and opp not in opp_events:
            opp_events[opp] = eid

    logger.info("Unique opponents to process: %s", len(opp_events))

    # Performance proxy (no Selenium needed)
    perf_proxy = _build_performance_proxy(all_results_path)
    logger.info("Performance proxy built for %s teams", len(perf_proxy))

    # Selenium: fetch team IDs and market values
    try:
        from selenium import webdriver  # noqa: F401
    except ImportError as exc:
        logger.error("Selenium not available: %s", exc)
        return

    options = _make_options()
    rows: list[dict[str, Any]] = []
    raw_debug: dict[str, Any] = {}

    for opp_name, event_id in sorted(opp_events.items()):
        logger.info("Processing opponent: %s (event_id=%s)", opp_name, event_id)
        driver = None
        try:
            driver = _open_driver(options)

            team_id = _fetch_team_id_from_event(driver, event_id, opp_name)
            if not team_id:
                logger.warning("Could not resolve team_id for %s", opp_name)
                mv_data = {"squad_market_value_eur": None, "squad_avg_market_value_eur": None,
                           "players_with_value": 0, "raw_player_count": 0}
            else:
                logger.info("  team_id=%s — fetching squad market values", team_id)
                mv_data = _fetch_squad_market_value(driver, team_id)
                raw_debug[opp_name] = {"team_id": team_id, **mv_data}

            perf = perf_proxy.get(opp_name, {})
            row = {
                "season": season,
                "opponent_name": opp_name,
                "sofascore_team_id": team_id,
                "squad_market_value_eur": mv_data.get("squad_market_value_eur"),
                "squad_avg_market_value_eur": mv_data.get("squad_avg_market_value_eur"),
                "players_with_value": mv_data.get("players_with_value", 0),
                "raw_player_count": mv_data.get("raw_player_count", 0),
                **perf,
                "last_updated_at": datetime.datetime.utcnow().isoformat() + "Z",
            }
            rows.append(row)
            logger.info(
                "  market_value=%.0f  win_rate=%s  games=%s",
                row.get("squad_market_value_eur") or 0,
                row.get("perf_win_rate"),
                row.get("perf_games"),
            )

        except Exception as exc:
            logger.error("Failed processing %s: %s", opp_name, exc)
        finally:
            if driver:
                driver.quit()

    write_csv(out_dir / "sport_2026_opponent_strength.csv", rows)
    write_json(out_dir / "sport_2026_opponent_strength_debug.json", raw_debug)
    logger.info("Opponent strength sync complete: %s opponents written", len(rows))
