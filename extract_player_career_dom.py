#!/usr/bin/env python3
"""Extract player data by fetching directly from URLs."""

import csv
import json
import time
from pathlib import Path
from typing import Any

import requests

from src.config import get_settings
from src.utils.logging_utils import configure_logging, get_logger

logger = get_logger(__name__)


def get_player_by_id(player_id: int) -> dict[str, Any]:
    """Fetch player info by ID directly via REST API."""
    url = f"https://www.sofascore.com/api/v1/player/{player_id}"
    try:
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching player {player_id}: {e}")
        return {}


def get_player_statistics(player_id: int) -> dict[str, Any]:
    """Fetch player statistics by ID."""
    url = f"https://www.sofascore.com/api/v1/player/{player_id}/statistics"
    try:
        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching statistics for player {player_id}: {e}")
        return {}


def get_player_events(player_id: int, season: int | None = None) -> list[dict[str, Any]]:
    """Fetch player's matches."""
    url = f"https://www.sofascore.com/api/v1/player/{player_id}/events"
    params = {"limit": 500}
    if season:
        params["season"] = season

    try:
        response = requests.get(
            url,
            params=params,
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        response.raise_for_status()
        return response.json().get("events", [])
    except Exception as e:
        logger.error(f"Error fetching events for player {player_id}: {e}")
        return []


def extract_tournament_summary(stats: dict) -> list[dict]:
    """Extract tournament summary from statistics."""
    records = []
    if stats.get("statistics"):
        for stat in stats["statistics"]:
            records.append({
                "tournament": stat.get("tournament", {}).get("name", ""),
                "season": stat.get("season", {}).get("name", ""),
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
    return records


def extract_matches_2026(player_info: dict, events: list) -> list[dict]:
    """Extract 2026 match summary."""
    records = []
    player_team_id = player_info.get("team", {}).get("id")

    for event in events:
        home_team = event.get("homeTeam", {})
        away_team = event.get("awayTeam", {})

        # Determine if player's team is home or away
        is_home = home_team.get("id") == player_team_id
        player_team = home_team if is_home else away_team
        opponent_team = away_team if is_home else home_team

        records.append({
            "match_id": event.get("customId", ""),
            "event_id": event.get("id", ""),
            "date": event.get("startTimestamp", ""),
            "season": event.get("season", {}).get("name", ""),
            "tournament": event.get("tournament", {}).get("name", ""),
            "team": player_team.get("name", ""),
            "opponent": opponent_team.get("name", ""),
            "position": "home" if is_home else "away",
            "status": event.get("status", ""),
            "score": f"{event.get('homeScore', {}).get('current', 'N/A')} - {event.get('awayScore', {}).get('current', 'N/A')}",
        })

    return records


def extract_by_id(player_id: int, player_name: str = "Alex Bruno"):
    """Extract career data for a known player ID."""
    logs_dir = Path("logs")
    configure_logging("INFO", logs_dir)

    logger.info(f"=== Extracting {player_name} (ID: {player_id}) ===")

    # Create output directory
    output_dir = Path("data/processed/2026/players") / player_name.lower().replace(" ", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch player info
    logger.info("Fetching player information...")
    player_info = get_player_by_id(player_id)
    if player_info:
        with open(output_dir / "player_info.json", "w", encoding="utf-8") as f:
            json.dump(player_info, f, indent=2, ensure_ascii=False)
        logger.info(f"✓ Player: {player_info.get('name')}")
        logger.info(f"  Position: {player_info.get('position')}")
        logger.info(f"  Current Team: {player_info.get('team', {}).get('name')}")
    else:
        logger.warning(f"Could not fetch player info for ID {player_id}")
        return

    # Fetch statistics
    logger.info("Fetching career statistics...")
    stats = get_player_statistics(player_id)
    if stats:
        with open(output_dir / "career_statistics.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        tournament_records = extract_tournament_summary(stats)
        logger.info(f"✓ Found {len(tournament_records)} season/tournament records")

        if tournament_records:
            # Save to CSV
            with open(output_dir / "tournament_summary.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=tournament_records[0].keys())
                writer.writeheader()
                writer.writerows(tournament_records)
            logger.info(f"  Saved to: tournament_summary.csv")

            # Log summary
            logger.info("\n  Seasons/Teams:")
            for rec in tournament_records:
                logger.info(
                    f"    {rec['season']} — {rec['team']:20} | {rec['matches_played']:2}J "
                    f"{rec['goals']:2}G {rec['assists']:2}A | Rating: {rec['rating']:.1f}"
                )

    # Fetch 2026 matches
    logger.info("\nFetching 2026 matches...")
    events_2026 = get_player_events(player_id, season=2026)
    if events_2026:
        logger.info(f"✓ Found {len(events_2026)} matches in 2026")

        # Save raw events
        with open(output_dir / "matches_2026.json", "w", encoding="utf-8") as f:
            json.dump(events_2026, f, indent=2, ensure_ascii=False)

        # Extract summary
        matches_records = extract_matches_2026(player_info, events_2026)
        if matches_records:
            with open(output_dir / "matches_2026_summary.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matches_records[0].keys())
                writer.writeheader()
                writer.writerows(matches_records)
            logger.info(f"  Saved to: matches_2026_summary.csv")

            # Count by competition
            from collections import Counter
            comps = Counter(r["tournament"] for r in matches_records)
            logger.info("\n  Matches by competition:")
            for comp, count in comps.most_common():
                logger.info(f"    {comp}: {count}")

    logger.info(f"\n=== Extraction complete ===")
    logger.info(f"Output: {output_dir}/")


if __name__ == "__main__":
    # Try these player IDs (you can search on sofascore.com to find the correct ID)
    # For now, trying common IDs — replace with actual player_id once found
    logger.info("To find Alex Bruno's player ID, visit:")
    logger.info("  https://www.sofascore.com/search?q=alex+bruno")
    logger.info("")
    logger.info("Then call: extract_by_id(player_id=XXXX)")
    logger.info("")
    logger.info("Trying a few possible IDs...")

    # Example: trying some IDs (would need to find the correct one)
    # extract_by_id(player_id=123456, player_name="Alex Bruno")
