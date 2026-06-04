#!/usr/bin/env python3
"""
Extract advanced team statistics for Série B 2025 matches.
Requires: match URLs + Selenium to extract event_ids, then XHR for /event/{id}/statistics
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
import csv

sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_settings
from src.utils.logging_utils import configure_logging, get_logger
from src.utils.io import write_json, write_csv

logger = get_logger(__name__)


def resolve_event_ids_from_matches(season: int = 2025) -> dict:
    """
    Extract event_ids from match URLs using Selenium + XHR.
    Returns: {match_code: event_id}
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions
        import re

        settings = get_settings()
        matches_csv = Path(settings.base_dir) / "data" / "curated" / "serie_b_2025" / "matches_clean.csv"

        if not matches_csv.exists():
            logger.error(f"File not found: {matches_csv}")
            return {}

        df = pd.read_csv(matches_csv)
        logger.info(f"Loading {len(df)} matches from {matches_csv}")

        event_ids = {}

        # Create driver once
        logger.info("Starting Selenium driver...")
        edge_options = EdgeOptions()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")

        driver = webdriver.Edge(options=edge_options)

        try:
            for idx, row in df.iterrows():
                match_code = row['match_id']
                match_date = row['match_date_utc']

                if idx % 20 == 0:
                    logger.info(f"Progress: {idx}/{len(df)}")

                try:
                    # Build SofaScore URL from match_code
                    url = f"https://www.sofascore.com/football/match/{match_code}"

                    driver.get(url)
                    time.sleep(0.5)

                    # Execute XHR to get match details
                    result = driver.execute_script("""
                        var xhr = new XMLHttpRequest();
                        xhr.open("GET", "/api/v1/match", false);
                        xhr.send();
                        if (xhr.status === 200) {
                            try {
                                return JSON.parse(xhr.responseText);
                            } catch(e) {
                                return null;
                            }
                        }
                        return null;
                    """)

                    if result and result.get('id'):
                        event_id = result['id']
                        event_ids[match_code] = event_id
                        if idx < 5:
                            logger.info(f"  [{idx}] {match_code} -> event_id {event_id}")
                    else:
                        # Fallback: try to extract from page
                        logger.debug(f"  Could not get event_id from API for {match_code}")

                except Exception as e:
                    logger.debug(f"Error processing {match_code}: {e}")
                    continue

        finally:
            driver.quit()

        logger.info(f"Resolved {len(event_ids)}/{len(df)} event_ids")
        return event_ids

    except ImportError:
        logger.error("Selenium not available")
        return {}


def fetch_team_stats(event_ids: dict, season: int = 2025) -> list:
    """
    Fetch advanced team statistics for each match via /api/v1/event/{id}/statistics
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions

        settings = get_settings()
        edge_options = EdgeOptions()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")

        driver = webdriver.Edge(options=edge_options)
        stats_list = []

        try:
            for idx, (match_code, event_id) in enumerate(event_ids.items()):
                if idx % 20 == 0:
                    logger.info(f"Fetching stats: {idx}/{len(event_ids)}")

                try:
                    # Navigate to match page first
                    driver.get(f"https://www.sofascore.com/football/match/{match_code}")
                    time.sleep(0.3)

                    # XHR to get statistics
                    result = driver.execute_script("""
                        var xhr = new XMLHttpRequest();
                        xhr.open("GET", "/api/v1/event/" + arguments[0] + "/statistics", false);
                        xhr.send();
                        if (xhr.status === 200) {
                            try {
                                return JSON.parse(xhr.responseText);
                            } catch(e) {
                                return null;
                            }
                        }
                        return null;
                    """, event_id)

                    if result and result.get('statistics'):
                        for team_stats in result['statistics']:
                            stats_entry = {
                                'match_code': match_code,
                                'event_id': event_id,
                                'team_id': team_stats.get('teamId'),
                                'team_name': team_stats.get('teamName'),
                                **team_stats.get('statistics', {})
                            }
                            stats_list.append(stats_entry)
                    else:
                        logger.debug(f"No stats for {match_code} (event_id {event_id})")

                except Exception as e:
                    logger.debug(f"Error fetching stats for {match_code}: {e}")
                    continue

        finally:
            driver.quit()

        logger.info(f"Fetched stats for {len(stats_list)} team-matches")
        return stats_list

    except ImportError:
        logger.error("Selenium not available")
        return []


def main():
    settings = get_settings()
    logs_dir = Path(settings.base_dir) / "logs"
    configure_logging("INFO", logs_dir)

    logger.info("=" * 70)
    logger.info("Série B 2025 — Advanced Team Statistics Extraction")
    logger.info("=" * 70)

    # Step 1: Resolve event IDs
    logger.info("\nStep 1: Resolving event IDs from match URLs...")
    event_ids = resolve_event_ids_from_matches(season=2025)

    if not event_ids:
        logger.error("Failed to resolve event IDs. Check Selenium/API access.")
        return 1

    # Save event_ids mapping
    event_ids_file = Path(settings.base_dir) / "data" / "processed" / "2025" / "matches" / "event_ids.json"
    event_ids_file.parent.mkdir(parents=True, exist_ok=True)
    with open(event_ids_file, 'w') as f:
        json.dump(event_ids, f, indent=2)
    logger.info(f"Saved event_ids mapping to {event_ids_file}")

    # Step 2: Fetch advanced stats
    logger.info("\nStep 2: Fetching advanced team statistics...")
    stats_list = fetch_team_stats(event_ids, season=2025)

    if not stats_list:
        logger.error("Failed to fetch statistics.")
        return 1

    # Step 3: Save stats
    stats_file = Path(settings.base_dir) / "data" / "processed" / "2025" / "matches" / "team_match_stats.csv"
    stats_file.parent.mkdir(parents=True, exist_ok=True)

    # Convert to DataFrame for easier handling
    df_stats = pd.DataFrame(stats_list)
    df_stats.to_csv(stats_file, index=False)
    logger.info(f"Saved {len(df_stats)} team-match records to {stats_file}")

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("Complete: Advanced Statistics Extraction")
    logger.info("=" * 70)
    logger.info(f"\nStatistics extracted:")
    logger.info(f"  Total team-match records: {len(df_stats)}")
    logger.info(f"  Columns: {len(df_stats.columns)}")
    logger.info(f"  Sample columns: {list(df_stats.columns[:10])}")

    logger.info(f"\nNext step:")
    logger.info(f"  python -m src.main transform --season 2025")
    logger.info(f"  (will normalize stats into curated tables)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
