#!/usr/bin/env python3
"""Extract complete career history for Alex Bruno using Selenium + XHR síncrono."""

import csv
import json
import time
from pathlib import Path
from typing import Any
from collections import defaultdict

from selenium import webdriver
from selenium.webdriver.common.by import By

from src.utils.logging_utils import configure_logging, get_logger

logger = get_logger(__name__)

PLAYER_ID = 1468444
PLAYER_NAME = "Alex Bruno"

def get_player_info_xhr(driver) -> dict[str, Any]:
    """Fetch player info via XHR síncrono."""
    script = """
    var xhr = new XMLHttpRequest();
    xhr.open("GET", `/api/v1/player/${arguments[0]}`, false);
    xhr.send();
    return {
        status: xhr.status,
        body: xhr.responseText
    };
    """
    result = driver.execute_script(script, PLAYER_ID)
    if result['status'] == 200:
        return json.loads(result['body'])
    return {}


def get_player_statistics_xhr(driver) -> dict[str, Any]:
    """Fetch player statistics (career by tournament/season) via XHR síncrono."""
    script = """
    var xhr = new XMLHttpRequest();
    xhr.open("GET", `/api/v1/player/${arguments[0]}/statistics`, false);
    xhr.send();
    return {
        status: xhr.status,
        body: xhr.responseText
    };
    """
    result = driver.execute_script(script, PLAYER_ID)
    if result['status'] == 200:
        return json.loads(result['body'])
    return {}


def get_player_events_xhr(driver, season: int | None = None, limit: int = 500) -> list[dict]:
    """Fetch player's matches/events via XHR síncrono."""
    script = """
    var params = "limit=${arguments[1]}";
    if (arguments[2]) {
        params += "&season=" + arguments[2];
    }
    var xhr = new XMLHttpRequest();
    xhr.open("GET", `/api/v1/player/${arguments[0]}/events?` + params, false);
    xhr.send();
    return {
        status: xhr.status,
        body: xhr.responseText
    };
    """
    result = driver.execute_script(script, PLAYER_ID, limit, season)
    if result['status'] == 200:
        data = json.loads(result['body'])
        return data.get('events', [])
    return []


def extract_complete_history():
    """Extract complete career history for Alex Bruno."""
    logs_dir = Path("logs")
    configure_logging("INFO", logs_dir)

    driver = None
    try:
        logger.info("="*80)
        logger.info(f"EXTRACTING COMPLETE HISTORY: {PLAYER_NAME} (ID: {PLAYER_ID})")
        logger.info("="*80)

        # Initialize Selenium Edge driver (headless)
        options = webdriver.EdgeOptions()
        options.add_argument("--headless=new")
        driver = webdriver.Edge(options=options)

        # Navigate to SofaScore to establish session
        logger.info("Initializing SofaScore session...")
        driver.get("https://www.sofascore.com")
        time.sleep(2)

        # Create output directory
        output_dir = Path("data/processed/2026/players/alex_bruno")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 1. Fetch player info
        logger.info("\n[1/4] Fetching player information...")
        player_info = get_player_info_xhr(driver)
        if player_info:
            with open(output_dir / "player_info.json", "w", encoding="utf-8") as f:
                json.dump(player_info, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Player Info:")
            logger.info(f"  Name: {player_info.get('name')}")
            logger.info(f"  Position: {player_info.get('position')}")
            logger.info(f"  Height: {player_info.get('height')} cm")
            logger.info(f"  Weight: {player_info.get('weight')} kg")
            logger.info(f"  Birth Date: {player_info.get('dateOfBirthTimestamp')}")
            current_team = player_info.get('team', {})
            logger.info(f"  Current Team: {current_team.get('name')} (ID: {current_team.get('id')})")
        else:
            logger.warning("Could not fetch player info")

        # 2. Fetch career statistics by tournament/season
        logger.info("\n[2/4] Fetching career statistics...")
        stats = get_player_statistics_xhr(driver)
        if stats and stats.get('statistics'):
            with open(output_dir / "career_statistics.json", "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)

            # Parse into CSV
            tournament_records = []
            for stat in stats['statistics']:
                tournament_records.append({
                    "tournament": stat.get("tournament", {}).get("name", ""),
                    "tournament_id": stat.get("tournament", {}).get("id", ""),
                    "season": stat.get("season", {}).get("name", ""),
                    "season_id": stat.get("season", {}).get("id", ""),
                    "team": stat.get("team", {}).get("name", ""),
                    "team_id": stat.get("team", {}).get("id", ""),
                    "matches_played": stat.get("matches_played", 0),
                    "minutes_played": stat.get("minutes_played", 0),
                    "goals": stat.get("goals", 0),
                    "assists": stat.get("assists", 0),
                    "rating": stat.get("rating", 0),
                    "tackles": stat.get("tackles", 0),
                    "blocks": stat.get("blocks", 0),
                    "interceptions": stat.get("interceptions", 0),
                    "dribbles": stat.get("dribbles", 0),
                    "passes": stat.get("passes", 0),
                    "yellow_cards": stat.get("yellow_cards", 0),
                    "red_cards": stat.get("red_cards", 0),
                })

            if tournament_records:
                with open(output_dir / "tournament_summary.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=tournament_records[0].keys())
                    writer.writeheader()
                    writer.writerows(tournament_records)

                logger.info(f"✓ Found {len(tournament_records)} season/tournament records:")
                for rec in sorted(tournament_records, key=lambda x: x['season'], reverse=True)[:10]:
                    logger.info(
                        f"  {rec['season']:10} | {rec['team']:30} | "
                        f"{rec['matches_played']:3}J {rec['minutes_played']:5}min | "
                        f"{rec['goals']:2}G {rec['assists']:2}A | Rating: {rec['rating']:.1f}"
                    )
        else:
            logger.warning("Could not fetch career statistics")

        # 3. Fetch 2026 events
        logger.info("\n[3/4] Fetching 2026 matches...")
        events_2026 = get_player_events_xhr(driver, season=2026, limit=500)
        if events_2026:
            with open(output_dir / "matches_2026_raw.json", "w", encoding="utf-8") as f:
                json.dump(events_2026, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Found {len(events_2026)} matches in 2026")
        else:
            logger.warning("Could not fetch 2026 matches")

        # 4. Fetch all-time events (for complete match history)
        logger.info("\n[4/4] Fetching complete match history (all seasons)...")
        all_events = get_player_events_xhr(driver, season=None, limit=500)
        if all_events:
            with open(output_dir / "matches_all_raw.json", "w", encoding="utf-8") as f:
                json.dump(all_events, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ Found {len(all_events)} total matches")

            # Parse matches by season
            matches_by_season = defaultdict(list)
            for event in all_events:
                season = event.get('season', {}).get('name', 'Unknown')
                matches_by_season[season].append(event)

            # Create summary CSV
            matches_summary = []
            for event in all_events:
                home_team = event.get("homeTeam", {})
                away_team = event.get("awayTeam", {})
                current_team_id = player_info.get('team', {}).get('id') if player_info else None

                is_home = home_team.get('id') == current_team_id
                player_team = home_team if is_home else away_team
                opponent = away_team if is_home else home_team

                matches_summary.append({
                    "date": event.get("startTimestamp", "")[:10],
                    "season": event.get("season", {}).get("name", ""),
                    "tournament": event.get("tournament", {}).get("name", ""),
                    "team": player_team.get("name", ""),
                    "opponent": opponent.get("name", ""),
                    "position": "home" if is_home else "away",
                    "status": event.get("status", ""),
                    "score": f"{event.get('homeScore', {}).get('current', 'N/A')} - {event.get('awayScore', {}).get('current', 'N/A')}",
                    "match_id": event.get("customId", ""),
                })

            if matches_summary:
                with open(output_dir / "matches_all_summary.csv", "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=matches_summary[0].keys())
                    writer.writeheader()
                    writer.writerows(matches_summary)

            logger.info(f"✓ Parsed into summary CSV")
            logger.info(f"\n  Matches by season:")
            for season in sorted(matches_by_season.keys(), reverse=True):
                logger.info(f"    {season}: {len(matches_by_season[season])} matches")
        else:
            logger.warning("Could not fetch complete match history")

        logger.info("\n" + "="*80)
        logger.info(f"EXTRACTION COMPLETE")
        logger.info(f"Output directory: {output_dir}/")
        logger.info(f"Files generated:")
        logger.info(f"  - player_info.json")
        logger.info(f"  - career_statistics.json")
        logger.info(f"  - tournament_summary.csv")
        logger.info(f"  - matches_2026_raw.json")
        logger.info(f"  - matches_all_raw.json")
        logger.info(f"  - matches_all_summary.csv")
        logger.info("="*80)

    except Exception as e:
        logger.error(f"Error during extraction: {e}", exc_info=True)
    finally:
        if driver:
            driver.quit()
            logger.info("Selenium driver closed")


if __name__ == "__main__":
    extract_complete_history()
