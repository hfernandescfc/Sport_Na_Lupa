from __future__ import annotations

import datetime
import json
from typing import Any

from src.config import Settings
from src.utils.io import write_csv, write_json
from src.utils.logging_utils import get_logger


logger = get_logger(__name__)


SERIE_B_2026_METADATA = {
    "season": 2026,
    "competition": "serie_b",
    "competition_name": "Brasileirao Serie B",
    "country": "Brazil",
    "source": "sofascore+cbf",
    "tournament_id": 390,
    "season_id": None,
    "status": "in_progress",
    "season_phase": "round_1",
    "coverage_status": "incremental_seed",
    "competition_url": "https://www.sofascore.com/pt/football/tournament/brazil/brasileirao-serie-b/390",
    "cbf_table_url": "https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/2026",
    "cbf_rounds_1_5_url": "https://www.cbf.com.br/futebol-brasileiro/noticias/undefined/acao-x-remo/cbf-divulga-tabela-detalhada-das-cinco-primeiras-rodadas-da-serie-b",
    "start_date": "2026-03-21",
    "end_date": "2026-11-29",
    "team_count": 20,
    "notes": [
        "Tournament ID 390 confirmed from the public SofaScore tournament URL.",
        "Season ID still unresolved because live network capture is blocked in the local environment.",
        "Round 1 schedule seeded from CBF article published on 2026-03-07.",
        "Validation must be incremental while the competition is still in progress.",
    ],
}


ROUND_1_MATCHES = [
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-21T18:00:00Z",
        "home_team": "Ceara",
        "away_team": "Sao Bernardo",
        "venue_name": "Estadio Governador Placido Castelo",
        "source": "cbf",
        "source_detail": "Wikipedia standings matrix + SofaScore public page",
        "match_url": "https://www.sofascore.com/football/match/sao-bernardo-ceara/bPseau",
        "match_code": "bPseau",
        "event_id": 15525988,
        "home_score": 1,
        "away_score": 1,
        "status": "completed",
        "discovery_status": "identified",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-21T20:00:00Z",
        "home_team": "Vila Nova",
        "away_team": "CRB",
        "venue_name": "Estadio Onesio Brasileiro Alvarenga",
        "source": "cbf",
        "source_detail": "SofaScore public page",
        "match_url": "https://www.sofascore.com/football/match/crb-vila-nova-fc/wPsHPi",
        "match_code": "wPsHPi",
        "event_id": 15525994,
        "home_score": 2,
        "away_score": 2,
        "status": "completed",
        "discovery_status": "identified",
        "data_status": "event_level_partial",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-21T18:00:00Z",
        "home_team": "Operario-PR",
        "away_team": "Atletico-GO",
        "venue_name": "Estadio Germano Kruger",
        "source": "cbf",
        "source_detail": "Wikipedia standings matrix",
        "match_url": "https://www.sofascore.com/football/match/operario-pr-atletico-goianiense/oWcsJRp",
        "match_code": "oWcsJRp",
        "event_id": 15525987,
        "home_score": 1,
        "away_score": 0,
        "status": "completed",
        "discovery_status": "scheduled",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-21T22:15:00Z",
        "home_team": "Botafogo-SP",
        "away_team": "Fortaleza",
        "venue_name": "Estadio Santa Cruz",
        "source": "cbf",
        "source_detail": "Wikipedia standings matrix + Reddit post-match thread",
        "match_url": "https://www.sofascore.com/football/match/fortaleza-botafogo-sp/EOsvP",
        "match_code": "EOsvP",
        "event_id": 15525984,
        "home_score": 4,
        "away_score": 0,
        "status": "completed",
        "discovery_status": "identified",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-21T23:30:00Z",
        "home_team": "Cuiaba",
        "away_team": "Sport",
        "venue_name": "Arena Pantanal",
        "source": "cbf",
        "source_detail": "SofaScore public page + team page",
        "match_url": "https://www.sofascore.com/football/match/cuiaba-sport-recife/jOscJu",
        "match_code": "jOscJu",
        "event_id": 15525993,
        "home_score": 0,
        "away_score": 0,
        "status": "completed",
        "discovery_status": "identified",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-22T18:00:00Z",
        "home_team": "Avai",
        "away_team": "Juventude",
        "venue_name": "Estadio da Ressacada",
        "source": "cbf",
        "source_detail": "Wikipedia standings matrix + Reddit match thread",
        "match_url": "https://www.sofascore.com/football/match/avai-juventude/FOspWc",
        "match_code": "FOspWc",
        "event_id": 15525991,
        "home_score": 2,
        "away_score": 0,
        "status": "completed",
        "discovery_status": "scheduled",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-22T19:00:00Z",
        "home_team": "Nautico",
        "away_team": "Criciuma",
        "venue_name": "Aflitos",
        "source": "cbf",
        "source_detail": "Wikipedia standings matrix + Reddit match thread",
        "match_url": "https://www.sofascore.com/football/match/nautico-criciuma/JOslP",
        "match_code": "JOslP",
        "event_id": 15525992,
        "home_score": 0,
        "away_score": 1,
        "status": "completed",
        "discovery_status": "identified",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-22T21:00:00Z",
        "home_team": "Athletic Club",
        "away_team": "Ponte Preta",
        "venue_name": "Estadio Joaquim Portugal",
        "source": "cbf",
        "source_detail": "SofaScore public page + Wikipedia standings matrix",
        "match_url": "https://www.sofascore.com/football/match/athletic-club-ponte-preta/uOsAfMc",
        "match_code": "uOsAfMc",
        "event_id": 15525986,
        "home_score": 2,
        "away_score": 1,
        "status": "completed",
        "discovery_status": "identified",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-22T21:00:00Z",
        "home_team": "Goias",
        "away_team": "America-MG",
        "venue_name": "Estadio da Serrinha",
        "source": "cbf",
        "source_detail": "Wikipedia standings matrix",
        "match_url": "https://www.sofascore.com/football/match/america-mineiro-goias/kOsyO",
        "match_code": "kOsyO",
        "event_id": 15525989,
        "home_score": 3,
        "away_score": 1,
        "status": "completed",
        "discovery_status": "scheduled",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
    {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_date_utc": "2026-03-22T23:00:00Z",
        "home_team": "Gremio Novorizontino",
        "away_team": "Londrina",
        "venue_name": "Estadio Jorge Ismael de Biasi",
        "source": "cbf",
        "source_detail": "Wikipedia standings matrix",
        "match_url": "https://www.sofascore.com/football/match/gremio-novorizontino-londrina/xPsokeb",
        "match_code": "xPsokeb",
        "event_id": 15525985,
        "home_score": 1,
        "away_score": 3,
        "status": "completed",
        "discovery_status": "scheduled",
        "data_status": "score_confirmed",
        "is_completed": True,
        "last_seen_at": "2026-03-23T00:00:00Z",
        "last_updated_at": "2026-03-23T00:00:00Z",
    },
]


_SOFASCORE_STATUS_MAP = {
    "finished": "completed",
    "inprogress": "in_progress",
    "notstarted": "scheduled",
    "postponed": "postponed",
    "canceled": "canceled",
}


def load_season_id(settings: Settings, season: int) -> int | None:
    """Load previously resolved season_id from disk. Returns None if not found."""
    path = settings.raw_dir / "sofascore" / "competition" / f"serie_b_{season}_season_id.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        value = data.get("season_id")
        return int(value) if value is not None else None
    except Exception as exc:
        logger.warning("Failed to load season_id from %s: %s", path, exc)
        return None


def fetch_round_matches(
    driver: Any,
    tournament_id: int,
    season_id: int,
    round_num: int,
    season: int,
) -> list[dict[str, Any]]:
    """Fetch all events for a single round and return them as match rows.

    The driver must already be on the sofascore.com origin before calling this.
    Returns an empty list if the API call fails or returns no events.
    """
    events = _fetch_round_events_json(driver, tournament_id, season_id, round_num)
    if not events:
        return []
    return [_parse_event_to_match_row(e, season) for e in events]


def _fetch_round_events_json(
    driver: Any,
    tournament_id: int,
    season_id: int,
    round_num: int,
) -> list[dict[str, Any]] | None:
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open(
              "GET",
              "/api/v1/unique-tournament/" + arguments[0] + "/season/" + arguments[1] + "/events/round/" + arguments[2],
              false
            );
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            tournament_id,
            season_id,
            round_num,
        )
        if response.get("status") != 200:
            logger.warning(
                "Round events API returned status %s for round %s",
                response.get("status"),
                round_num,
            )
            return None
        payload = json.loads(response["body"])
        return payload.get("events", [])
    except Exception as exc:
        logger.warning("_fetch_round_events_json failed for round %s: %s", round_num, exc)
        return None


def _parse_event_to_match_row(event: dict[str, Any], season: int) -> dict[str, Any]:
    ts = event.get("startTimestamp", 0)
    match_date_utc = datetime.datetime.utcfromtimestamp(ts).isoformat() + "Z" if ts else None

    status_type = (event.get("status") or {}).get("type", "notstarted")
    status = _SOFASCORE_STATUS_MAP.get(status_type, status_type)
    is_completed = status == "completed"

    home_team = event.get("homeTeam") or {}
    away_team = event.get("awayTeam") or {}
    home_score_obj = event.get("homeScore") or {}
    away_score_obj = event.get("awayScore") or {}
    venue = event.get("venue") or {}
    round_info = event.get("roundInfo") or {}

    event_id = event.get("id")
    custom_id = event.get("customId", "")
    slug = event.get("slug", "")
    match_url = (
        f"https://www.sofascore.com/football/match/{slug}/{custom_id}"
        if slug and custom_id
        else None
    )
    now = datetime.datetime.utcnow().isoformat() + "Z"

    return {
        "season": season,
        "competition": "serie_b",
        "round": round_info.get("round"),
        "event_id": event_id,
        "match_code": custom_id,
        "match_url": match_url,
        "match_date_utc": match_date_utc,
        "home_team": home_team.get("name"),
        "away_team": away_team.get("name"),
        "home_score": home_score_obj.get("current") if is_completed else None,
        "away_score": away_score_obj.get("current") if is_completed else None,
        "status": status,
        "is_completed": is_completed,
        "venue_name": venue.get("name"),
        "source": "sofascore_api",
        "source_detail": (
            f"api/v1/unique-tournament/{SERIE_B_2026_METADATA['tournament_id']}"
            f"/season/{{}}/events/round/{{}}"
        ),
        "data_status": "score_confirmed" if is_completed else "scheduled",
        "discovery_status": "identified",
        "last_seen_at": now,
        "last_updated_at": now,
    }


def resolve_season_id(settings: Settings, season: int) -> int | None:
    """Navigate to the SofaScore tournament page and call
    /api/v1/unique-tournament/390/seasons to find the season_id for `season`.

    Persists the result to data/raw/sofascore/competition/serie_b_{season}_season_id.json
    and patches SERIE_B_2026_METADATA["season_id"] in-memory.

    Tries a direct HTTP request first (faster, no browser); falls back to Selenium.
    """
    seasons = _fetch_seasons_via_requests(settings, tournament_id=SERIE_B_2026_METADATA["tournament_id"])
    if seasons is None:
        logger.info("requests fallback failed; trying Selenium for season_id resolution")
        seasons = _fetch_seasons_via_selenium(settings, tournament_id=SERIE_B_2026_METADATA["tournament_id"])

    if not seasons:
        logger.warning("No seasons returned from API for tournament %s", SERIE_B_2026_METADATA["tournament_id"])
        return None

    entry = next(
        (s for s in seasons if str(s.get("year", "")) == str(season)),
        None,
    )
    if entry is None:
        logger.warning("No season entry found for year %s in tournament %s", season, SERIE_B_2026_METADATA["tournament_id"])
        return None

    season_id = int(entry["id"])
    _persist_season_id(settings, season, season_id)
    SERIE_B_2026_METADATA["season_id"] = season_id
    logger.info("Resolved season_id=%s for serie_b %s", season_id, season)
    return season_id


def _fetch_seasons_via_requests(settings: Settings, tournament_id: int) -> list[dict[str, Any]] | None:
    """Try to fetch seasons list directly via requests (no browser required)."""
    try:
        import requests as _requests

        url = f"https://www.sofascore.com/api/v1/unique-tournament/{tournament_id}/seasons"
        headers = {
            "User-Agent": settings.user_agent,
            "Referer": "https://www.sofascore.com/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
        }
        resp = _requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning("Seasons API (requests) returned status %s", resp.status_code)
            return None
        return resp.json().get("seasons", [])
    except Exception as exc:
        logger.warning("_fetch_seasons_via_requests failed: %s", exc)
        return None


def _fetch_seasons_via_selenium(settings: Settings, tournament_id: int) -> list[dict[str, Any]] | None:
    """Load SofaScore in Edge headless and call the seasons API via synchronous XHR."""
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
        import time
    except Exception as exc:
        logger.warning("Selenium not available for season_id resolution: %s", exc)
        return None

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)
    try:
        driver.get(SERIE_B_2026_METADATA["competition_url"])
        time.sleep(4)  # allow page JS to settle before XHR
        return _fetch_seasons_json(driver, tournament_id=tournament_id)
    except Exception as exc:
        logger.warning("_fetch_seasons_via_selenium failed: %s", exc)
        return None
    finally:
        driver.quit()


def _fetch_seasons_json(driver: Any, tournament_id: int) -> list[dict[str, Any]] | None:
    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/api/v1/unique-tournament/" + arguments[0] + "/seasons", false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            tournament_id,
        )
        if response.get("status") != 200:
            logger.warning(
                "Seasons API returned status %s",
                response.get("status"),
            )
            return None
        payload = json.loads(response["body"])
        return payload.get("seasons", [])
    except Exception as exc:
        logger.warning("_fetch_seasons_json failed: %s", exc)
        return None


def _persist_season_id(settings: Settings, season: int, season_id: int) -> None:
    path = settings.raw_dir / "sofascore" / "competition" / f"serie_b_{season}_season_id.json"
    write_json(path, {
        "season": season,
        "competition": "serie_b",
        "tournament_id": SERIE_B_2026_METADATA["tournament_id"],
        "season_id": season_id,
        "resolved_at": datetime.datetime.utcnow().isoformat() + "Z",
    })


def sync_competition_stub(settings: Settings, season: int) -> None:
    base = settings.raw_dir / "sofascore" / "competition"
    metadata = dict(SERIE_B_2026_METADATA)
    metadata["season"] = season

    if metadata["season_id"] is None:
        resolved = resolve_season_id(settings, season)
        if resolved is not None:
            metadata["season_id"] = resolved
        else:
            logger.warning(
                "season_id could not be resolved for season %s; metadata will be written with season_id=null",
                season,
            )

    write_json(base / f"serie_b_{season}_metadata.json", metadata)
    write_json(base / f"serie_b_{season}_round_1_seed.json", ROUND_1_MATCHES)
    write_csv(
        settings.processed_dir / str(season) / "matches" / "match_ids.csv",
        [
            {
                "season": item["season"],
                "competition": item["competition"],
                "round": item["round"],
                "home_team": item["home_team"],
                "away_team": item["away_team"],
                "match_date_utc": item["match_date_utc"],
                "home_score": item["home_score"],
                "away_score": item["away_score"],
                "status": item["status"],
                "event_id": item["event_id"],
                "match_code": item["match_code"],
                "match_url": item["match_url"],
                "seed_status": "resolved" if item["match_code"] else "pending",
                "discovery_status": item["discovery_status"],
                "data_status": item["data_status"],
                "is_completed": item["is_completed"],
                "last_seen_at": item["last_seen_at"],
                "last_updated_at": item["last_updated_at"],
            }
            for item in ROUND_1_MATCHES
        ],
    )
