from __future__ import annotations

import datetime
import json
from typing import Any

from src.config import Settings
from src.extract.sofascore_match import (
    REQUIRED_ADVANCED_FIELDS,
    STAT_FIELDS,
    extract_team_stats_for_matches,
)
from src.utils.io import write_csv, write_json
from src.utils.logging_utils import get_logger


logger = get_logger(__name__)


SPORT_2026_METADATA = {
    "season": 2026,
    "focus_team": "Sport Recife",
    "canonical_name": "sport",
    "sofascore_team_id": 1959,
    "sofascore_slug": "sport-recife",
    "team_url": "https://www.sofascore.com/pt/football/team/sport-recife/1959",
    "status": "in_progress",
    "coverage_status": "incremental_seed",
    "objective": "Track all Sport Recife matches in 2026 across all competitions.",
    "notes": [
        "Team ID 1959 confirmed from the public SofaScore team page.",
        "Competition-level discovery for all 2026 matches is still pending endpoint resolution.",
        "Rows are expected to be updated incrementally as new fixtures and results become available.",
    ],
}


SPORT_2026_COMPETITION_SEED = [
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_name": "Brasileirao Serie B",
        "competition_scope": "full",
        "source": "sofascore public team page",
        "status": "confirmed",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_name": "Copa Betano do Brasil",
        "competition_scope": "full",
        "source": "sofascore public team page",
        "status": "confirmed",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_name": "Pernambucano",
        "competition_scope": "full",
        "source": "sofascore public team page",
        "status": "confirmed",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_name": "Copa do Nordeste",
        "competition_scope": "full",
        "source": "sofascore public team page",
        "status": "confirmed",
    },
]


SPORT_2026_RESULT_SEED = [
    {
        "match_url": "https://www.sofascore.com/football/match/ad-jaguar-sport-recife/jOswXWd#id:15204423",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 2,
        "away_score": 2,
        "sport_outcome": "draw",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/retro-sport-recife/jOsOWEc#id:15204429",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 2,
        "away_score": 0,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/clube-nautico-capibaribe-sport-recife/jOslP#id:15204428",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 4,
        "away_score": 0,
        "sport_outcome": "loss",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/cuiaba-sport-recife/jOscJu",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 0,
        "away_score": 0,
        "sport_outcome": "draw",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/anapolis-sport-recife/jOsxMi",
        "match_state": "after_penalties",
        "decision_type": "penalties",
        "home_score": 1,
        "away_score": 1,
        "home_penalty_score": 4,
        "away_penalty_score": 3,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/athletic-club-sport-recife/jOsAfMc#id:15730737",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 1,
        "away_score": 3,
        "sport_outcome": "loss",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/desportiva-ferroviaria-sport-recife/jOslFn#id:15566116",
        "match_state": "after_penalties",
        "decision_type": "penalties",
        "home_score": 0,
        "away_score": 0,
        "home_penalty_score": 3,
        "away_penalty_score": 4,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/decisao-goiana-sport-recife/jOsToWd",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 5,
        "away_score": 0,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/santa-cruz-sport-recife/jOsBO#id:15204433",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 2,
        "away_score": 1,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/retro-sport-recife/jOsOWEc#id:15517019",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 0,
        "away_score": 1,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/academica-vitoria-sport-recife/jOsydn",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 3,
        "away_score": 0,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/maguary-sport-recife/jOsXMHd",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 1,
        "away_score": 1,
        "sport_outcome": "draw",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/retro-sport-recife/jOsOWEc",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 3,
        "away_score": 2,
        "sport_outcome": "win",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/nautico-sport-recife/jOslP#id:15601729",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 3,
        "away_score": 3,
        "sport_outcome": "draw",
    },
    {
        "match_url": "https://www.sofascore.com/football/match/nautico-sport-recife/jOslP",
        "match_state": "full_time",
        "decision_type": "regular_time",
        "home_score": 0,
        "away_score": 3,
        "sport_outcome": "win",
    },
]


SPORT_2026_MATCH_SEED = [
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-01-10T22:00:00Z",
        "home_team": "AD Jaguar",
        "away_team": "Sport",
        "venue_name": "",
        "source": "sofascore team results tab",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOswXWd",
        "match_url": "https://www.sofascore.com/football/match/ad-jaguar-sport-recife/jOswXWd#id:15204423",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-01-14T22:00:00Z",
        "home_team": "Sport",
        "away_team": "Retro",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore team results tab",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOsOWEc",
        "match_url": "https://www.sofascore.com/football/match/retro-sport-recife/jOsOWEc#id:15204429",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-01-18T21:00:00Z",
        "home_team": "Nautico",
        "away_team": "Sport",
        "venue_name": "Aflitos",
        "source": "sofascore team results tab",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOslP",
        "match_url": "https://www.sofascore.com/football/match/clube-nautico-capibaribe-sport-recife/jOslP#id:15204428",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": 1,
        "competition_name": "Brasileirao Serie B",
        "match_date_utc": "2026-03-21T23:30:00Z",
        "home_team": "Cuiaba",
        "away_team": "Sport",
        "venue_name": "Arena Pantanal",
        "source": "sofascore team page + public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOscJu",
        "match_url": "https://www.sofascore.com/football/match/cuiaba-sport-recife/jOscJu",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": 3,
        "competition_name": "Copa Betano do Brasil",
        "match_date_utc": "2026-03-13T00:30:00Z",
        "home_team": "Sport",
        "away_team": "Anapolis",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOsxMi",
        "match_url": "https://www.sofascore.com/football/match/anapolis-sport-recife/jOsxMi",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Copa Betano do Brasil",
        "match_date_utc": "2026-03-18T00:30:00Z",
        "home_team": "Sport",
        "away_team": "Athletic Club",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore team results tab + player page snippet",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOsAfMc",
        "match_url": "https://www.sofascore.com/football/match/athletic-club-sport-recife/jOsAfMc#id:15730737",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": 1,
        "competition_name": "Copa Betano do Brasil",
        "match_date_utc": "2026-03-05T00:30:00Z",
        "home_team": "Desportiva",
        "away_team": "Sport",
        "venue_name": "",
        "source": "sofascore team results tab",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOslFn",
        "match_url": "https://www.sofascore.com/football/match/desportiva-ferroviaria-sport-recife/jOslFn#id:15566116",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-01-21T22:00:00Z",
        "home_team": "Sport",
        "away_team": "Decisao Goiana",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOsToWd",
        "match_url": "https://www.sofascore.com/football/match/decisao-goiana-sport-recife/jOsToWd",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-01-31T22:00:00Z",
        "home_team": "Sport",
        "away_team": "Santa Cruz",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore team results tab",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOsBO",
        "match_url": "https://www.sofascore.com/football/match/santa-cruz-sport-recife/jOsBO#id:15204433",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-02-12T00:00:00Z",
        "home_team": "Retro",
        "away_team": "Sport",
        "venue_name": "",
        "source": "sofascore team results tab",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOsOWEc",
        "match_url": "https://www.sofascore.com/football/match/retro-sport-recife/jOsOWEc#id:15517019",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Copa do Nordeste",
        "match_date_utc": None,
        "home_team": "",
        "away_team": "",
        "venue_name": "",
        "source": "sofascore public team page",
        "source_confidence": "medium",
        "status": "competition_confirmed_matches_pending",
        "match_code": "",
        "match_url": "",
        "discovery_status": "competition_identified",
        "data_status": "competition_only",
        "is_completed": False,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-01-24T20:00:00Z",
        "home_team": "Sport",
        "away_team": "Academica Vitoria",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOsydn",
        "match_url": "https://www.sofascore.com/football/match/academica-vitoria-sport-recife/jOsydn",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-01-28T18:00:00Z",
        "home_team": "Maguary",
        "away_team": "Sport",
        "venue_name": "Estadio Municipal Arthur Tavares de Melo",
        "source": "sofascore public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOsXMHd",
        "match_url": "https://www.sofascore.com/football/match/maguary-sport-recife/jOsXMHd",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": None,
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-02-21T19:30:00Z",
        "home_team": "Sport",
        "away_team": "Retro",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOsOWEc",
        "match_url": "https://www.sofascore.com/football/match/retro-sport-recife/jOsOWEc",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": "playoffs",
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-03-01T21:00:00Z",
        "home_team": "Sport",
        "away_team": "Nautico",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore team results tab",
        "source_confidence": "medium",
        "status": "confirmed_team_results_tab",
        "match_code": "jOslP",
        "match_url": "https://www.sofascore.com/football/match/nautico-sport-recife/jOslP#id:15601729",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": "playoffs",
        "competition_name": "Pernambucano",
        "match_date_utc": "2026-03-08T21:00:00Z",
        "home_team": "Nautico",
        "away_team": "Sport",
        "venue_name": "Aflitos",
        "source": "sofascore search result snippet",
        "source_confidence": "medium",
        "status": "confirmed_search_snippet",
        "match_code": "jOslP",
        "match_url": "https://www.sofascore.com/football/match/nautico-sport-recife/jOslP",
        "discovery_status": "identified",
        "data_status": "fixture_or_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": 8,
        "competition_name": "Brasileirao Serie B",
        "match_date_utc": "2026-05-16T18:00:00Z",
        "home_team": "Sport",
        "away_team": "CRB",
        "venue_name": "Ilha do Retiro",
        "source": "sofascore public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOsHPi",
        "match_url": "https://www.sofascore.com/football/match/crb-sport-recife/jOsHPi",
        "discovery_status": "identified",
        "data_status": "fixture_only",
        "is_completed": False,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": 13,
        "competition_name": "Brasileirao Serie B",
        "match_date_utc": "2026-06-13T18:00:00Z",
        "home_team": "Sao Bernardo",
        "away_team": "Sport",
        "venue_name": "Estadio Primeiro de Maio",
        "source": "sofascore public match page",
        "source_confidence": "high",
        "status": "confirmed_public_page",
        "match_code": "jOseau",
        "match_url": "https://www.sofascore.com/football/match/sao-bernardo-sport-recife/jOseau",
        "discovery_status": "identified",
        "data_status": "fixture_only",
        "is_completed": False,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_round": 15,
        "competition_name": "Brasileirao Serie B",
        "match_date_utc": "2026-06-27T18:00:00Z",
        "home_team": "Fortaleza",
        "away_team": "Sport",
        "venue_name": "Estadio Governador Placido Castelo",
        "source": "sofascore search result snippet",
        "source_confidence": "medium",
        "status": "confirmed_search_snippet",
        "match_code": "jOsvP",
        "match_url": "https://www.sofascore.com/football/match/fortaleza-sport-recife/jOsvP",
        "discovery_status": "identified",
        "data_status": "fixture_only",
        "is_completed": False,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
]


def fetch_all_sport_matches(
    driver: Any,
    team_id: int,
    season_year: int,
) -> list[dict[str, Any]]:
    """Paginate through past and future team events and return all matches in season_year.

    The driver must already be on the sofascore.com origin before calling this.
    """
    season_start = int(datetime.datetime(season_year, 1, 1, tzinfo=datetime.timezone.utc).timestamp())
    season_end = int(datetime.datetime(season_year, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc).timestamp())

    past = _paginate_team_events(driver, team_id, "last", season_start, season_end)
    future = _paginate_team_events(driver, team_id, "next", season_start, season_end)

    seen: set[int] = set()
    result: list[dict[str, Any]] = []
    for event in past + future:
        eid = event.get("id")
        if eid and eid not in seen:
            seen.add(eid)
            result.append(_parse_team_event_to_match_row(event, season_year, team_id))

    result.sort(key=lambda r: r.get("match_date_utc") or "")
    logger.info("fetch_all_sport_matches: %s matches found for %s", len(result), season_year)
    return result


def _paginate_team_events(
    driver: Any,
    team_id: int,
    direction: str,
    season_start: int,
    season_end: int,
) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    page = 0
    while True:
        response = _fetch_team_events_json(driver, team_id, direction, page)
        if response is None:
            break
        events = response.get("events") or []
        if not events:
            break

        for event in events:
            ts = event.get("startTimestamp", 0)
            if season_start <= ts <= season_end:
                collected.append(event)

        has_next = response.get("hasNextPage", False)
        if not has_next:
            break

        timestamps = [e.get("startTimestamp", 0) for e in events]
        if direction == "last" and min(timestamps) < season_start:
            break
        if direction == "next" and max(timestamps) > season_end:
            break

        page += 1

    return collected


def _fetch_team_events_json(
    driver: Any,
    team_id: int,
    direction: str,
    page: int,
) -> dict[str, Any] | None:
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/api/v1/team/" + arguments[0] + "/events/" + arguments[1] + "/" + arguments[2], false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            team_id,
            direction,
            page,
        )
        if response.get("status") != 200:
            logger.warning(
                "Team events API status %s (%s page %s)",
                response.get("status"),
                direction,
                page,
            )
            return None
        return json.loads(response["body"])
    except Exception as exc:
        logger.warning("_fetch_team_events_json failed (%s page %s): %s", direction, page, exc)
        return None


def _parse_team_event_to_match_row(
    event: dict[str, Any],
    season: int,
    team_id: int,
) -> dict[str, Any]:
    ts = event.get("startTimestamp", 0)
    match_date_utc = datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None

    status_type = (event.get("status") or {}).get("type", "notstarted")
    is_completed = status_type == "finished"
    status = "completed" if is_completed else ("in_progress" if status_type == "inprogress" else "scheduled")

    home_team = event.get("homeTeam") or {}
    away_team = event.get("awayTeam") or {}
    home_score_obj = event.get("homeScore") or {}
    away_score_obj = event.get("awayScore") or {}
    venue = event.get("venue") or {}
    round_info = event.get("roundInfo") or {}
    tournament = event.get("tournament") or {}

    event_id = event.get("id")
    custom_id = event.get("customId", "")
    slug = event.get("slug", "")
    match_url = (
        f"https://www.sofascore.com/football/match/{slug}/{custom_id}"
        if slug and custom_id
        else None
    )

    home_score = home_score_obj.get("current") if is_completed else None
    away_score = away_score_obj.get("current") if is_completed else None
    sport_outcome = _determine_sport_outcome(home_team.get("id"), away_team.get("id"), home_score, away_score, team_id, is_completed)

    now = datetime.datetime.utcnow().isoformat() + "Z"

    return {
        "season": season,
        "team": "Sport Recife",
        "competition_scope": "all_competitions",
        "competition_name": tournament.get("name") or tournament.get("uniqueTournament", {}).get("name", ""),
        "competition_round": round_info.get("round"),
        "match_date_utc": match_date_utc,
        "event_id": event_id,
        "match_code": custom_id,
        "match_url": match_url,
        "home_team": home_team.get("name", ""),
        "away_team": away_team.get("name", ""),
        "venue_name": venue.get("name", ""),
        "home_score": home_score,
        "away_score": away_score,
        "match_state": "full_time" if is_completed else None,
        "decision_type": "regular_time" if is_completed else None,
        "sport_outcome": sport_outcome,
        "status": status,
        "is_completed": is_completed,
        "source": "sofascore_api",
        "source_confidence": "high",
        "discovery_status": "identified",
        "data_status": "score_confirmed" if is_completed else "scheduled",
        "last_seen_at": now,
        "last_updated_at": now,
    }


def _determine_sport_outcome(
    home_id: int | None,
    away_id: int | None,
    home_score: int | None,
    away_score: int | None,
    team_id: int,
    is_completed: bool,
) -> str | None:
    if not is_completed or home_score is None or away_score is None:
        return None
    if home_score == away_score:
        return "draw"
    sport_is_home = home_id == team_id
    sport_score = home_score if sport_is_home else away_score
    opp_score = away_score if sport_is_home else home_score
    return "win" if sport_score > opp_score else "loss"


def _fetch_sport_matches_from_api(settings: Settings, season: int) -> list[dict[str, Any]] | None:
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except Exception as exc:
        logger.warning("Selenium not available for sport match fetch: %s", exc)
        return None

    team_id = SPORT_2026_METADATA["sofascore_team_id"]
    team_url = SPORT_2026_METADATA["team_url"]

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)
    try:
        driver.get(team_url)
        matches = fetch_all_sport_matches(driver, team_id=team_id, season_year=season)
        return matches if matches else None
    except Exception as exc:
        logger.warning("_fetch_sport_matches_from_api failed: %s", exc)
        return None
    finally:
        driver.quit()


def sync_sport_stub(settings: Settings, season: int) -> None:
    raw_dir = settings.raw_dir / "sofascore" / "sport"
    processed_dir = settings.processed_dir / str(season) / "sport"

    metadata = dict(SPORT_2026_METADATA)
    metadata["season"] = season

    api_matches = _fetch_sport_matches_from_api(settings, season)
    if api_matches:
        match_rows = api_matches
        logger.info("Using API data: %s matches", len(match_rows))
        write_json(raw_dir / f"sport_{season}_matches_api.json", match_rows)
    else:
        match_rows = SPORT_2026_MATCH_SEED
        logger.warning("API unavailable; falling back to seed data (%s matches)", len(match_rows))

    write_json(raw_dir / f"sport_{season}_metadata.json", metadata)
    write_json(raw_dir / f"sport_{season}_competitions.json", SPORT_2026_COMPETITION_SEED)
    write_csv(processed_dir / "sport_2026_competitions.csv", SPORT_2026_COMPETITION_SEED)
    write_csv(processed_dir / "sport_2026_matches.csv", match_rows)
    write_csv(processed_dir / "sport_2026_results.csv", _build_sport_results_rows(match_rows, season))
    team_stats_rows = _extract_sport_team_stats(match_rows, season)
    write_csv(
        processed_dir / "sport_2026_team_match_stats.csv",
        team_stats_rows,
    )
    write_csv(
        processed_dir / "sport_2026_team_stats_coverage.csv",
        _build_sport_team_stats_coverage(team_stats_rows),
    )


def _extract_sport_team_stats(match_rows: list[dict], season: int) -> list[dict]:
    completed = [
        item
        for item in match_rows
        if item.get("season") == season
        and item.get("is_completed")
        and item.get("match_code")
        and item.get("match_url")
    ]

    stats_input = [
        {
            "season": item["season"],
            "competition": item["competition_name"],
            "round": item.get("competition_round"),
            "match_code": item["match_code"],
            "home_team": item["home_team"],
            "away_team": item["away_team"],
            "match_url": item["match_url"],
            "last_updated_at": item["last_updated_at"],
        }
        for item in completed
    ]

    extracted_rows = extract_team_stats_for_matches(stats_input)
    return [
        {
            "season": row["season"],
            "competition_name": row["competition"],
            "competition_round": row["round"],
            "match_id": row["match_id"],
            "team_name": row["team_name"],
            "is_home": row["is_home"],
            "possession": row["possession"],
            "expected_goals": row["expected_goals"],
            "shots_total": row["shots_total"],
            "shots_on_target": row["shots_on_target"],
            "corners": row["corners"],
            "fouls": row["fouls"],
            "passes_total": row["passes_total"],
            "passes_accurate": row["passes_accurate"],
            "tackles_total": row["tackles_total"],
            "yellow_cards": row["yellow_cards"],
            "red_cards": row["red_cards"],
            "source_url": row["source_url"],
            "data_status": row["data_status"],
            "last_updated_at": row["last_updated_at"],
        }
        for row in extracted_rows
    ]


def _build_sport_results_rows(match_rows: list[dict], season: int) -> list[dict]:
    # For seed rows (no scores embedded), fall back to SPORT_2026_RESULT_SEED lookup
    results_by_url = {item["match_url"]: item for item in SPORT_2026_RESULT_SEED}
    rows = []
    for item in match_rows:
        if item.get("season") != season or not item.get("is_completed"):
            continue

        if item.get("home_score") is not None:
            # API-fetched row: scores are already in the row
            rows.append(
                {
                    "season": item["season"],
                    "competition_name": item.get("competition_name", ""),
                    "competition_round": item.get("competition_round"),
                    "match_id": item.get("match_code", ""),
                    "match_date_utc": item.get("match_date_utc"),
                    "home_team": item.get("home_team", ""),
                    "away_team": item.get("away_team", ""),
                    "home_score": item["home_score"],
                    "away_score": item["away_score"],
                    "home_penalty_score": item.get("home_penalty_score"),
                    "away_penalty_score": item.get("away_penalty_score"),
                    "match_state": item.get("match_state", "full_time"),
                    "decision_type": item.get("decision_type", "regular_time"),
                    "sport_outcome": item.get("sport_outcome"),
                    "source_url": item.get("match_url", ""),
                    "last_updated_at": item.get("last_updated_at", ""),
                }
            )
        else:
            # Seed row: look up score in SPORT_2026_RESULT_SEED
            result = results_by_url.get(item.get("match_url", ""))
            if not result:
                continue
            rows.append(
                {
                    "season": item["season"],
                    "competition_name": item["competition_name"],
                    "competition_round": item["competition_round"],
                    "match_id": item["match_code"],
                    "match_date_utc": item["match_date_utc"],
                    "home_team": item["home_team"],
                    "away_team": item["away_team"],
                    "home_score": result["home_score"],
                    "away_score": result["away_score"],
                    "home_penalty_score": result.get("home_penalty_score"),
                    "away_penalty_score": result.get("away_penalty_score"),
                    "match_state": result["match_state"],
                    "decision_type": result["decision_type"],
                    "sport_outcome": result["sport_outcome"],
                    "source_url": item["match_url"],
                    "last_updated_at": item["last_updated_at"],
                }
            )
    return rows


def _build_sport_team_stats_coverage(team_stats_rows: list[dict]) -> list[dict]:
    coverage_rows = []
    for row in team_stats_rows:
        missing_fields = [field for field in STAT_FIELDS if row[field] is None]
        missing_required_fields = [
            field for field in REQUIRED_ADVANCED_FIELDS if row[field] is None
        ]
        coverage_rows.append(
            {
                "season": row["season"],
                "competition_name": row["competition_name"],
                "competition_round": row["competition_round"],
                "match_id": row["match_id"],
                "team_name": row["team_name"],
                "is_home": row["is_home"],
                "data_status": row["data_status"],
                "missing_fields_count": len(missing_fields),
                "missing_required_fields_count": len(missing_required_fields),
                "missing_fields": "|".join(missing_fields),
                "missing_required_fields": "|".join(missing_required_fields),
                "source_url": row["source_url"],
                "last_updated_at": row["last_updated_at"],
            }
        )
    return coverage_rows
