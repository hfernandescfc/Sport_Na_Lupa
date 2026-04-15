from __future__ import annotations

import argparse

from src.config import get_settings
from src.discover.endpoint_registry import discover_endpoints
from src.discover.team_mapper import build_team_mapping_stub
from src.extract.cbf_competition import export_cbf_clubs_seed
from src.extract.sofascore_competition import sync_competition_stub
from src.extract.sofascore_match import sync_matches_stub
from src.extract.sofascore_all_teams import sync_all_teams_stub
from src.extract.sofascore_player_stats import sync_player_stats
from src.extract.sofascore_incidents import sync_incidents
from src.extract.sofascore_player_heatmap_match import sync_player_positions
from src.extract.sofascore_attack_map import sync_attack_map
from src.extract.sofascore_team_heatmap import sync_team_heatmap
from src.extract.sofascore_opponent import sync_opponent
from src.extract.sofascore_opponent_strength import sync_opponent_strength
from src.extract.sofascore_sport import sync_sport_stub
from src.transform.attack_map import transform_attack_map
from src.transform.incidents import transform_incidents
from src.transform.player_positions import transform_player_positions
from src.transform.opponents import transform_opponent
from src.transform.matches import transform_matches
from src.transform.players import transform_players
from src.transform.standings import transform_standings
from src.extract.sofascore_serie_b_strength import sync_serie_b_strength
from src.extract.sofascore_logos import sync_logos
from src.extract.sofascore_team import sync_teams_stub
from src.utils.io import ensure_project_structure
from src.utils.logging_utils import configure_logging, get_logger
from src.validate.quality_checks import run_quality_checks


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SportSofa CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Create project folders and seed files")
    subparsers.add_parser(
        "discover-endpoints", help="Create a starter endpoint registry and discovery log"
    )

    sync_competition = subparsers.add_parser(
        "sync-competition", help="Sync competition artifacts"
    )
    sync_competition.add_argument("--season", type=int, required=True)

    sync_teams = subparsers.add_parser("sync-teams", help="Sync team artifacts")
    sync_teams.add_argument("--season", type=int, required=True)

    sync_sport = subparsers.add_parser("sync-sport", help="Sync Sport artifacts")
    sync_sport.add_argument("--season", type=int, required=True)

    sync_matches = subparsers.add_parser("sync-matches", help="Sync match artifacts")
    sync_matches.add_argument("--season", type=int, required=True)
    sync_matches.add_argument("--from-round", type=int, dest="from_round", default=1)
    sync_matches.add_argument("--to-round", type=int, dest="to_round", default=38)

    transform_cmd = subparsers.add_parser("transform", help="Transform processed data into curated tables")
    transform_cmd.add_argument("--season", type=int, required=True)

    sync_all_teams_cmd = subparsers.add_parser(
        "sync-all-teams",
        help="Sync matches for all Série B clubs across all competitions (no advanced stats)",
    )
    sync_all_teams_cmd.add_argument("--season", type=int, required=True)

    sync_player_stats_cmd = subparsers.add_parser(
        "sync-player-stats", help="Sync individual player stats (Sport all comps + Série B all clubs)"
    )
    sync_player_stats_cmd.add_argument("--season", type=int, required=True)

    sync_player_positions_cmd = subparsers.add_parser(
        "sync-player-positions",
        help="Fetch per-match heatmaps for Sport players in Série B and compute avg position",
    )
    sync_player_positions_cmd.add_argument("--season", type=int, required=True)

    transform_player_positions_cmd = subparsers.add_parser(
        "transform-player-positions",
        help="Normalize heatmap centroids into player_positions_serie_b.csv",
    )
    transform_player_positions_cmd.add_argument("--season", type=int, required=True)

    sync_incidents_cmd = subparsers.add_parser(
        "sync-incidents",
        help="Fetch match incidents (goals, cards, subs) + goal passing sequences with coordinates",
    )
    sync_incidents_cmd.add_argument("--season", type=int, required=True)

    transform_incidents_cmd = subparsers.add_parser(
        "transform-incidents",
        help="Normalize incidents JSON into match_incidents.csv + goal_sequences.csv",
    )
    transform_incidents_cmd.add_argument("--season", type=int, required=True)

    sync_opp_strength_cmd = subparsers.add_parser(
        "sync-opponent-strength",
        help="Fetch opponent squad market values (Sofascore) + performance proxy",
    )
    sync_opp_strength_cmd.add_argument("--season", type=int, required=True)

    sync_opponent_cmd = subparsers.add_parser(
        "sync-opponent",
        help="Fetch all matches + team stats + player stats for a specific opponent",
    )
    sync_opponent_cmd.add_argument("--team-key", dest="team_key", required=True,
                                   help="Canonical team key, e.g. vila-nova")
    sync_opponent_cmd.add_argument("--team-id", dest="team_id", type=int, required=True,
                                   help="SofaScore numeric team ID, e.g. 2021")
    sync_opponent_cmd.add_argument("--season", type=int, required=True)

    transform_opponent_cmd = subparsers.add_parser(
        "transform-opponent",
        help="Normalize processed opponent data into curated tables",
    )
    transform_opponent_cmd.add_argument("--team-key", dest="team_key", required=True)
    transform_opponent_cmd.add_argument("--season", type=int, required=True)

    sync_attack_map_cmd = subparsers.add_parser(
        "sync-attack-map",
        help="Fetch extended stats + shotmap for all completed opponent matches",
    )
    sync_attack_map_cmd.add_argument("--team-key", dest="team_key", required=True,
                                     help="Canonical team key, e.g. avai")
    sync_attack_map_cmd.add_argument("--season", type=int, required=True)

    transform_attack_map_cmd = subparsers.add_parser(
        "transform-attack-map",
        help="Aggregate extended stats + shotmap into attack_profile.json with pattern detection",
    )
    transform_attack_map_cmd.add_argument("--team-key", dest="team_key", required=True)
    transform_attack_map_cmd.add_argument("--season", type=int, required=True)

    sync_team_heatmap_cmd = subparsers.add_parser(
        "sync-team-heatmap",
        help="Fetch per-player heatmaps and aggregate into a team-level heatmap",
    )
    sync_team_heatmap_cmd.add_argument("--team-key", dest="team_key", required=True,
                                       help="Canonical team key, e.g. avai")
    sync_team_heatmap_cmd.add_argument("--competition", required=True,
                                       help="Competition name filter, e.g. 'Brasileirao Serie B'")
    sync_team_heatmap_cmd.add_argument("--season", type=int, required=True)

    sync_logos_cmd = subparsers.add_parser(
        "sync-logos",
        help="Download club shields for all 20 Serie B teams via Selenium (cached locally)",
    )
    sync_logos_cmd.add_argument("--season", type=int, required=True)

    sync_serie_b_strength_cmd = subparsers.add_parser(
        "sync-serie-b-strength",
        help="Fetch squad market values for all 20 Série B teams and build strength index",
    )
    sync_serie_b_strength_cmd.add_argument("--season", type=int, required=True)

    transform_standings_cmd = subparsers.add_parser(
        "transform-standings", help="Build expected-points table from curated xG data"
    )
    transform_standings_cmd.add_argument("--season", type=int, required=True)

    validate = subparsers.add_parser("validate", help="Run data validation checks")
    validate.add_argument("--season", type=int, required=True)

    return parser


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.logs_dir)
    logger = get_logger(__name__)
    args = build_parser().parse_args()

    if args.command == "bootstrap":
        ensure_project_structure(settings)
        export_cbf_clubs_seed(settings)
        build_team_mapping_stub(settings, season=2026)
        logger.info("Bootstrap completed at %s", settings.base_dir)
        return

    if args.command == "discover-endpoints":
        ensure_project_structure(settings)
        discover_endpoints(settings)
        logger.info("Endpoint discovery seed created")
        return

    if args.command == "sync-competition":
        ensure_project_structure(settings)
        sync_competition_stub(settings, season=args.season)
        logger.info("Competition sync stub completed for season %s", args.season)
        return

    if args.command == "sync-teams":
        ensure_project_structure(settings)
        sync_teams_stub(settings, season=args.season)
        logger.info("Team sync stub completed for season %s", args.season)
        return

    if args.command == "sync-sport":
        ensure_project_structure(settings)
        sync_sport_stub(settings, season=args.season)
        logger.info("Sport sync stub completed for season %s", args.season)
        return

    if args.command == "sync-matches":
        ensure_project_structure(settings)
        sync_matches_stub(
            settings,
            season=args.season,
            from_round=args.from_round,
            to_round=args.to_round,
        )
        logger.info(
            "Match sync stub completed for season %s, rounds %s-%s",
            args.season,
            args.from_round,
            args.to_round,
        )
        return

    if args.command == "transform":
        ensure_project_structure(settings)
        transform_matches(settings, season=args.season)
        transform_players(settings, season=args.season)
        logger.info("Transform completed for season %s", args.season)
        return

    if args.command == "sync-all-teams":
        ensure_project_structure(settings)
        sync_all_teams_stub(settings, season=args.season)
        logger.info("All-teams sync completed for season %s", args.season)
        return

    if args.command == "sync-player-stats":
        ensure_project_structure(settings)
        sync_player_stats(settings, season=args.season)
        logger.info("Player stats sync completed for season %s", args.season)
        return

    if args.command == "sync-player-positions":
        ensure_project_structure(settings)
        sync_player_positions(settings, season=args.season)
        logger.info("Player positions sync completed for season %s", args.season)
        return

    if args.command == "transform-player-positions":
        ensure_project_structure(settings)
        transform_player_positions(settings, season=args.season)
        logger.info("Player positions transform completed for season %s", args.season)
        return

    if args.command == "sync-incidents":
        ensure_project_structure(settings)
        sync_incidents(settings, season=args.season)
        logger.info("Incidents sync completed for season %s", args.season)
        return

    if args.command == "transform-incidents":
        ensure_project_structure(settings)
        transform_incidents(settings, season=args.season)
        logger.info("Incidents transform completed for season %s", args.season)
        return

    if args.command == "sync-opponent-strength":
        ensure_project_structure(settings)
        sync_opponent_strength(settings, season=args.season)
        logger.info("Opponent strength sync completed for season %s", args.season)
        return

    if args.command == "sync-opponent":
        ensure_project_structure(settings)
        sync_opponent(settings, team_key=args.team_key, team_id=args.team_id, season=args.season)
        logger.info(
            "Opponent sync completed for %s (id=%s) season %s",
            args.team_key,
            args.team_id,
            args.season,
        )
        return

    if args.command == "transform-opponent":
        ensure_project_structure(settings)
        transform_opponent(settings, team_key=args.team_key, season=args.season)
        logger.info("Opponent transform completed for %s season %s", args.team_key, args.season)
        return

    if args.command == "sync-attack-map":
        ensure_project_structure(settings)
        sync_attack_map(settings, team_key=args.team_key, season=args.season)
        logger.info("Attack map sync completed for %s season %s", args.team_key, args.season)
        return

    if args.command == "transform-attack-map":
        ensure_project_structure(settings)
        transform_attack_map(settings, team_key=args.team_key, season=args.season)
        logger.info("Attack map transform completed for %s season %s", args.team_key, args.season)
        return

    if args.command == "sync-team-heatmap":
        ensure_project_structure(settings)
        sync_team_heatmap(
            settings,
            team_key=args.team_key,
            competition_filter=args.competition,
            season=args.season,
        )
        logger.info("Team heatmap sync completed for %s season %s", args.team_key, args.season)
        return

    if args.command == "sync-logos":
        ensure_project_structure(settings)
        sync_logos(settings, season=args.season)
        logger.info("Logo sync completed for season %s", args.season)
        return

    if args.command == "sync-serie-b-strength":
        ensure_project_structure(settings)
        sync_serie_b_strength(settings, season=args.season)
        logger.info("Série B strength sync completed for season %s", args.season)
        return

    if args.command == "transform-standings":
        ensure_project_structure(settings)
        transform_standings(settings, season=args.season)
        logger.info("Standings transform completed for season %s", args.season)
        return

    if args.command == "validate":
        ensure_project_structure(settings)
        run_quality_checks(settings, season=args.season)
        logger.info("Validation completed for season %s", args.season)
        return


if __name__ == "__main__":
    main()
