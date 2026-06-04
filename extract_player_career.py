#!/usr/bin/env python3
"""Extract player career history and 2026 advanced statistics."""

import csv
import json
from pathlib import Path
from typing import Any
from src.config import get_settings
from src.utils.http import get_json
from src.utils.logging_utils import configure_logging, get_logger

logger = get_logger(__name__)


def search_player(settings, player_name: str) -> dict[str, Any] | None:
    """Search for player by name and return player object."""
    logger.info(f"Searching for player: {player_name}")
    try:
        result = get_json(
            settings,
            "https://www.sofascore.com/api/v1/search",
            params={"q": player_name, "type": "player"}
        )

        if result.get("players"):
            players = result["players"]
            logger.info(f"Found {len(players)} players matching '{player_name}'")
            for player in players:
                logger.info(f"  - {player.get('name')} (ID: {player.get('id')}) — Team: {player.get('team', {}).get('name')}")
            return players
        else:
            logger.warning(f"No players found for '{player_name}'")
            return None
    except Exception as e:
        logger.error(f"Error searching for player: {e}")
        return None


def get_player_info(settings, player_id: int) -> dict[str, Any] | None:
    """Get detailed player information."""
    try:
        result = get_json(
            settings,
            f"https://www.sofascore.com/api/v1/player/{player_id}"
        )
        return result
    except Exception as e:
        logger.error(f"Error getting player info for {player_id}: {e}")
        return None


def get_player_statistics(settings, player_id: int) -> dict[str, Any] | None:
    """Get player statistics by tournament/season."""
    try:
        result = get_json(
            settings,
            f"https://www.sofascore.com/api/v1/player/{player_id}/statistics"
        )
        return result
    except Exception as e:
        logger.error(f"Error getting player statistics for {player_id}: {e}")
        return None


def get_player_events(settings, player_id: int, season: int | None = None, limit: int = 500) -> list[dict[str, Any]]:
    """Get player's matches/events."""
    try:
        params = {"limit": limit}
        if season:
            params["season"] = season

        result = get_json(
            settings,
            f"https://www.sofascore.com/api/v1/player/{player_id}/events",
            params=params
        )

        events = result.get("events", [])
        logger.info(f"Retrieved {len(events)} events for player {player_id}")
        return events
    except Exception as e:
        logger.error(f"Error getting player events for {player_id}: {e}")
        return []


def get_event_lineups(settings, event_id: int, player_id: int) -> dict[str, Any] | None:
    """Get full lineups for a specific match to extract advanced stats."""
    try:
        result = get_json(
            settings,
            f"https://www.sofascore.com/api/v1/event/{event_id}/lineups"
        )

        if result:
            # Find the player in both teams' lineups
            for team_key in ["home", "away"]:
                team_data = result.get(team_key, {})
                for player in team_data.get("players", []):
                    if player.get("player", {}).get("id") == player_id:
                        return {
                            "event_id": event_id,
                            "team": team_key,
                            "player_stats": player
                        }
        return None
    except Exception as e:
        logger.debug(f"Error getting lineups for event {event_id}: {e}")
        return None


def extract_player_career(player_name: str = "Alex Bruno", team_name: str = "ASA"):
    """Main extraction function."""
    settings = get_settings()
    logs_dir = Path("logs")
    configure_logging("INFO", logs_dir)

    logger.info(f"=== Extracting career data for {player_name} ===")

    # Search for player
    search_results = search_player(settings, player_name)
    if not search_results:
        logger.error("Player not found. Aborting.")
        return

    # Filter by team (ASA) if specified
    target_player = None
    for player in search_results:
        team = player.get("team", {}).get("name", "")
        if team_name.upper() in team.upper() or not team_name:
            target_player = player
            break

    if not target_player:
        logger.error(f"Player from {team_name} not found. Using first result.")
        target_player = search_results[0]

    player_id = target_player.get("id")
    logger.info(f"Selected player: {target_player.get('name')} (ID: {player_id})")

    # Create output directory
    output_dir = Path("data/processed/2026/players") / player_name.lower().replace(" ", "_")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get player info
    logger.info("Fetching player information...")
    player_info = get_player_info(settings, player_id)
    if player_info:
        with open(output_dir / "player_info.json", "w", encoding="utf-8") as f:
            json.dump(player_info, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved player info to {output_dir}/player_info.json")

    # Get statistics by tournament/season
    logger.info("Fetching career statistics...")
    stats = get_player_statistics(settings, player_id)
    if stats:
        with open(output_dir / "career_statistics.json", "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved career statistics to {output_dir}/career_statistics.json")

        # Parse and create summary CSV
        tournament_stats = []
        if stats.get("statistics"):
            for stat in stats["statistics"]:
                tournament_stats.append({
                    "tournament": stat.get("tournament", {}).get("name"),
                    "tournament_id": stat.get("tournament", {}).get("id"),
                    "season": stat.get("season", {}).get("name"),
                    "season_id": stat.get("season", {}).get("id"),
                    "team": stat.get("team", {}).get("name"),
                    "team_id": stat.get("team", {}).get("id"),
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
                })

        if tournament_stats:
            with open(output_dir / "tournament_summary.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=tournament_stats[0].keys())
                writer.writeheader()
                writer.writerows(tournament_stats)
            logger.info(f"Saved tournament summary to {output_dir}/tournament_summary.csv")

    # Get 2026 events
    logger.info("Fetching 2026 matches...")
    events_2026 = get_player_events(settings, player_id, season=2026, limit=500)

    if events_2026:
        # Save raw events
        with open(output_dir / "matches_2026.json", "w", encoding="utf-8") as f:
            json.dump(events_2026, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved {len(events_2026)} matches to {output_dir}/matches_2026.json")

        # Extract match summary
        matches_summary = []
        for event in events_2026:
            home_team = event.get("homeTeam", {})
            away_team = event.get("awayTeam", {})

            # Determine which team the player is on
            player_team = None
            opponent_team = None
            if home_team.get("id") in [t.get("id") for t in [player_info.get("team", {})] if player_info]:
                player_team = home_team
                opponent_team = away_team
                is_home = True
            else:
                player_team = away_team
                opponent_team = home_team
                is_home = False

            matches_summary.append({
                "match_id": event.get("customId"),
                "event_id": event.get("id"),
                "date": event.get("startTimestamp"),
                "season": event.get("season", {}).get("name"),
                "tournament": event.get("tournament", {}).get("name"),
                "team": player_team.get("name"),
                "opponent": opponent_team.get("name"),
                "is_home": is_home,
                "home_team": home_team.get("name"),
                "away_team": away_team.get("name"),
                "status": event.get("status"),
                "home_score": event.get("homeScore", {}).get("current"),
                "away_score": event.get("awayScore", {}).get("current"),
            })

        if matches_summary:
            with open(output_dir / "matches_2026_summary.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=matches_summary[0].keys())
                writer.writeheader()
                writer.writerows(matches_summary)
            logger.info(f"Saved {len(matches_summary)} match summaries to {output_dir}/matches_2026_summary.csv")

    logger.info(f"\n=== Extraction complete ===")
    logger.info(f"Output saved to: {output_dir}")


if __name__ == "__main__":
    extract_player_career(player_name="Alex Bruno", team_name="ASA")
