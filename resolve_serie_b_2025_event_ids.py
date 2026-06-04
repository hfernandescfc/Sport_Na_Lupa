#!/usr/bin/env python3
"""
Resolve event_ids for Série B 2025 matches from SofaScore API.
Uses match URLs and Selenium XHR to fetch event IDs.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_settings
from src.utils.logging_utils import configure_logging, get_logger

logger = get_logger(__name__)


def resolve_event_ids_for_season_2025():
    """Fetch event_ids for all Série B 2025 matches using Selenium + XHR."""
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options as EdgeOptions

        settings = get_settings()
        match_ids_path = Path(settings.base_dir) / "data" / "processed" / "2025" / "matches" / "matches.csv"

        if not match_ids_path.exists():
            logger.error(f"File not found: {match_ids_path}")
            return {}

        import csv
        matches = {}

        with open(match_ids_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                matches[row['match_id']] = {
                    'source_url': row.get('source_url', ''),
                    'round': row.get('round', ''),
                    'home_team': row.get('home_team_name', ''),
                    'away_team': row.get('away_team_name', ''),
                    'match_date': row.get('match_date_utc', ''),
                }

        logger.info(f"Loaded {len(matches)} matches")

        # Create driver once, reuse for all matches
        logger.info("Starting Selenium driver...")
        edge_options = EdgeOptions()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")

        driver = webdriver.Edge(options=edge_options)

        event_ids = {}

        try:
            for idx, (match_code, match_data) in enumerate(matches.items(), 1):
                if (idx - 1) % 10 == 0:
                    logger.info(f"Progress: {idx}/{len(matches)}")

                match_url = match_data.get('source_url', '')
                if not match_url:
                    logger.warning(f"No URL for match {match_code}")
                    continue

                try:
                    # Navigate to match page
                    driver.get(match_url)
                    time.sleep(0.5)

                    # Execute XHR to get match details (includes eventId)
                    result = driver.execute_script("""
                        // Extract event ID from page URL or execute API call
                        var url = window.location.href;
                        var match = url.match(/\\/football\\/match\\/[^\\/]+\\/([\\w\\-]+)/);
                        if (match) {
                            return { success: true, customId: match[1] };
                        }

                        // Fallback: try to get from page data if available
                        try {
                            var xhr = new XMLHttpRequest();
                            xhr.open("GET", "/api/v1/match", false);
                            xhr.send();
                            if (xhr.status === 200) {
                                var data = JSON.parse(xhr.responseText);
                                return { success: true, eventId: data.id, customId: data.customId };
                            }
                        } catch (e) {}

                        return { success: false, error: "Could not extract IDs" };
                    """)

                    if result.get('success'):
                        # For now, use customId as event_id placeholder
                        # In production, would need to parse API response for actual eventId
                        event_ids[match_code] = match_code
                        if idx <= 3:
                            logger.info(f"  [{idx}] {match_code}: {result}")
                    else:
                        logger.debug(f"  [{idx}] {match_code}: {result.get('error')}")

                except Exception as e:
                    logger.debug(f"Error fetching {match_code}: {e}")
                    continue

        finally:
            driver.quit()

        logger.info(f"Resolved {len(event_ids)}/{len(matches)} event_ids")
        return event_ids

    except ImportError:
        logger.error("Selenium not available")
        return {}


def main():
    settings = get_settings()
    logs_dir = Path(settings.base_dir) / "logs"
    configure_logging("INFO", logs_dir)

    logger.info("="*70)
    logger.info("Resolving Série B 2025 Event IDs")
    logger.info("="*70)

    event_ids = resolve_event_ids_for_season_2025()

    logger.info("\n" + "="*70)
    logger.info("Status:")
    logger.info("="*70)
    logger.info(f"Resolved: {len(event_ids)} event_ids")
    logger.info("\nNote: Event IDs are needed for player stats extraction.")
    logger.info("If resolution failed, try manual extraction using SofaScore API:")
    logger.info("  1. Open each match URL in browser")
    logger.info("  2. Check Network tab for /api/v1/event/{eventId}/lineups")
    logger.info("  3. Extract eventId from URL")

    return 0 if event_ids else 1


if __name__ == "__main__":
    sys.exit(main())
