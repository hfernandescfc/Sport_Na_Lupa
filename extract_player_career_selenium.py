#!/usr/bin/env python3
"""Extract player career history using Selenium + XHR síncrono."""

import csv
import json
from pathlib import Path
from typing import Any
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.config import get_settings
from src.utils.logging_utils import configure_logging, get_logger

logger = get_logger(__name__)


def search_player_selenium(player_name: str, team_name: str = "ASA") -> dict[str, Any] | None:
    """Search for player using Selenium + XHR síncrono."""
    driver = None
    try:
        driver = webdriver.Edge()
        logger.info(f"Searching for {player_name} from {team_name}...")

        # Go to SofaScore search
        search_url = f"https://www.sofascore.com/search?q={player_name.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(2)

        # Use XHR síncrono para buscar via API
        script = """
        var xhr = new XMLHttpRequest();
        xhr.open("GET", `/api/v1/search?q=${arguments[0]}&type=player`, false);
        xhr.setRequestHeader("User-Agent", "Mozilla/5.0");
        xhr.send();
        return {
            status: xhr.status,
            body: xhr.responseText
        };
        """

        result = driver.execute_script(script, player_name)
        logger.info(f"XHR Status: {result['status']}")

        if result['status'] == 200:
            data = json.loads(result['body'])
            players = data.get('players', [])
            logger.info(f"Found {len(players)} players")

            # Find player from specified team
            for player in players:
                team = player.get('team', {}).get('name', '')
                if team_name.upper() in team.upper():
                    logger.info(f"Selected: {player.get('name')} (ID: {player.get('id')}) — {team}")
                    return player

            # If not found by team, return first result
            if players:
                logger.info(f"Team '{team_name}' not found. Using first result: {players[0].get('name')}")
                return players[0]

        return None

    except Exception as e:
        logger.error(f"Error searching for player: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def get_player_data_selenium(player_id: int, endpoint: str) -> dict[str, Any] | None:
    """Fetch player data via XHR síncrono."""
    driver = None
    try:
        driver = webdriver.Edge()

        script = """
        var xhr = new XMLHttpRequest();
        xhr.open("GET", `/api/v1/player/${arguments[0]}/${arguments[1]}`, false);
        xhr.send();
        return {
            status: xhr.status,
            body: xhr.responseText
        };
        """

        result = driver.execute_script(script, player_id, endpoint)

        if result['status'] == 200:
            return json.loads(result['body'])

        logger.warning(f"XHR returned status {result['status']} for {endpoint}")
        return None

    except Exception as e:
        logger.error(f"Error fetching {endpoint}: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def extract_player_career(player_name: str = "Alex Bruno", team_name: str = "ASA"):
    """Main extraction function."""
    settings = get_settings()
    logs_dir = Path("logs")
    configure_logging("INFO", logs_dir)

    logger.info(f"=== Extracting career data for {player_name} ===")

    # Search for player
    player = search_player_selenium(player_name, team_name)
    if not player:
        logger.error("Player not found. Aborting.")
        return

    player_id = player.get("id")
    player_name_full = player.get("name")
    logger.info(f"Extracting data for: {player_name_full} (ID: {player_id})")

    # Create output directory
    output_dir = Path("data/processed/2026/players") / player_name_full.lower().replace(" ", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get player info
    logger.info("Fetching player information...")
    player_info = get_player_data_selenium(player_id, "")
    if player_info:
        with open(output_dir / "player_info.json", "w", encoding="utf-8") as f:
            json.dump(player_info, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved player info")

    # Get statistics by tournament/season
    logger.info("Fetching career statistics...")
    stats = get_player_data_selenium(player_id, "statistics")
    if stats:
        with open(output_dir / "career_statistics.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved career statistics")

        # Parse and create summary CSV
        tournament_stats = []
        if stats.get("statistics"):
            for stat in stats["statistics"]:
                tournament_stats.append({
                    "tournament": stat.get("tournament", {}).get("name"),
                    "season": stat.get("season", {}).get("name"),
                    "team": stat.get("team", {}).get("name"),
                    "matches_played": stat.get("matches_played"),
                    "minutes_played": stat.get("minutes_played"),
                    "goals": stat.get("goals"),
                    "assists": stat.get("assists"),
                    "rating": stat.get("rating"),
                    "tackles": stat.get("tackles"),
                    "blocks": stat.get("blocks"),
                    "interceptions": stat.get("interceptions"),
                    "dribbles": stat.get("dribbles"),
                    "passes": stat.get("passes"),
                    "yellow_cards": stat.get("yellow_cards"),
                    "red_cards": stat.get("red_cards"),
                })

        if tournament_stats:
            with open(output_dir / "tournament_summary.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=tournament_stats[0].keys())
                writer.writeheader()
                writer.writerows(tournament_stats)
            logger.info(f"Saved {len(tournament_stats)} tournament records")

    logger.info(f"\n=== Extraction complete ===")
    logger.info(f"Output saved to: {output_dir}")
    logger.info(f"Files:")
    logger.info(f"  - player_info.json")
    logger.info(f"  - career_statistics.json")
    logger.info(f"  - tournament_summary.csv")


if __name__ == "__main__":
    extract_player_career(player_name="Alex Bruno", team_name="ASA")
