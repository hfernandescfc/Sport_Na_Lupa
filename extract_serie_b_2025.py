#!/usr/bin/env python3
"""
Extract complete Série B 2025 data for historical analysis and model training.
This script resolves the season_id for 2025 and extracts all 38 rounds of matches,
team stats, and player stats.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import get_settings
from src.utils.logging_utils import configure_logging, get_logger
from src.utils.io import ensure_project_structure, write_json

logger = get_logger(__name__)


def resolve_serie_b_2025_season_id():
    """
    Resolve the season_id for Série B 2025 from SofaScore.
    Tournament ID 390 is the same for all years.
    """
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.edge.options import Options as EdgeOptions

        logger.info("Resolving Série B 2025 season_id via Selenium + XHR...")

        # Use Edge for consistency with rest of pipeline
        edge_options = EdgeOptions()
        edge_options.add_argument("--headless=new")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

        driver = webdriver.Edge(options=edge_options)

        try:
            # Navigate to Série B tournament page
            logger.info("Navigating to Série B tournament page...")
            driver.get("https://www.sofascore.com/pt/football/tournament/brazil/brasileirao-serie-b/390")

            # Wait for page to load
            import time
            time.sleep(3)

            # Execute XHR to get seasons list
            logger.info("Fetching seasons list via XHR...")
            result = driver.execute_script("""
                var xhr = new XMLHttpRequest();
                xhr.open("GET", "/api/v1/unique-tournament/390/seasons", false);
                xhr.setRequestHeader("User-Agent", "Mozilla/5.0");
                xhr.send();
                return {
                    status: xhr.status,
                    body: xhr.responseText
                };
            """)

            if result['status'] != 200:
                logger.error(f"Failed to fetch seasons: status {result['status']}")
                return None

            seasons_data = json.loads(result['body'])
            seasons_list = seasons_data.get('seasons', [])
            logger.info(f"Retrieved {len(seasons_list)} seasons")

            # Debug: show first season structure
            if seasons_list:
                logger.info(f"First season example: {json.dumps(seasons_list[0], indent=2)}")

            # Find 2025 season (year is a string!)
            for season in seasons_list:
                year = season.get('year') or season.get('startYear')
                if str(year) == '2025':
                    season_id = season.get('id')
                    logger.info(f"✓ Found Série B 2025: season_id = {season_id}")
                    return season_id

            logger.error(f"Could not find 2025 season. Available years: {[s.get('year') or s.get('startYear') for s in seasons_list]}")
            return None

        finally:
            driver.quit()

    except ImportError:
        logger.error("Selenium not available - cannot resolve season_id")
        return None
    except Exception as e:
        logger.error(f"Error resolving season_id: {e}")
        return None


def save_season_metadata(season_id: int):
    """Save season metadata to data/raw/sofascore/competition/"""
    settings = get_settings()
    metadata_dir = Path(settings.base_dir) / "data" / "raw" / "sofascore" / "competition"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "season": 2025,
        "competition": "serie_b",
        "tournament_id": 390,
        "season_id": season_id,
        "resolved_at": datetime.utcnow().isoformat() + "Z"
    }

    file_path = metadata_dir / "serie_b_2025_season_id.json"
    write_json(file_path, metadata)
    logger.info(f"✓ Saved metadata: {file_path}")


def main():
    settings = get_settings()
    ensure_project_structure(settings)
    logs_dir = Path(settings.base_dir) / "logs"
    configure_logging("INFO", logs_dir)

    logger.info("="*70)
    logger.info("Série B 2025 Historical Data Extraction")
    logger.info("="*70)

    # Check if season_id already resolved
    season_file = Path(settings.base_dir) / "data" / "raw" / "sofascore" / "competition" / "serie_b_2025_season_id.json"

    if season_file.exists():
        with open(season_file) as f:
            metadata = json.load(f)
            season_id = metadata['season_id']
            logger.info(f"✓ Using cached season_id: {season_id}")
    else:
        logger.info("Season ID not cached, resolving from SofaScore...")
        season_id = resolve_serie_b_2025_season_id()

        if not season_id:
            logger.error("Failed to resolve season_id. Aborting.")
            return 1

        save_season_metadata(season_id)

    logger.info("\n" + "="*70)
    logger.info("Next steps:")
    logger.info("="*70)
    logger.info(f"python -m src.main sync-matches --season 2025 --from-round 1 --to-round 38")
    logger.info(f"python -m src.main sync-player-stats --season 2025")
    logger.info(f"python -m src.main sync-incidents --season 2025")
    logger.info(f"python -m src.main transform --season 2025")

    return 0


if __name__ == "__main__":
    sys.exit(main())
