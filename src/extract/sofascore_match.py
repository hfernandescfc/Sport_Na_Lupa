from __future__ import annotations

from dataclasses import dataclass
import datetime
import json
from typing import Any

import csv

from src.config import Settings
from src.extract.sofascore_competition import (
    SERIE_B_2026_METADATA,
    fetch_round_matches,
    load_season_id,
    resolve_season_id,
)
from src.utils.io import write_csv, write_json
from src.utils.logging_utils import get_logger


logger = get_logger(__name__)


STAT_FIELDS = [
    "possession",
    "expected_goals",
    "shots_total",
    "shots_on_target",
    "corners",
    "fouls",
    "passes_total",
    "passes_accurate",
    "tackles_total",
    "yellow_cards",
    "red_cards",
]

REQUIRED_ADVANCED_FIELDS = [
    "expected_goals",
    "shots_total",
    "corners",
    "fouls",
    "passes_total",
    "tackles_total",
    "yellow_cards",
]

JSON_STAT_LABELS = {
    "Ball possession": "possession",
    "Expected goals": "expected_goals",
    "Total shots": "shots_total",
    "Shots on target": "shots_on_target",
    "Corner kicks": "corners",
    "Fouls": "fouls",
    "Passes": "passes_total",
    "Accurate passes": "passes_accurate",
    "Total tackles": "tackles_total",
    "Yellow cards": "yellow_cards",
    "Red cards": "red_cards",
}

DOM_STAT_LABELS = {
    "Ball possession": "possession",
    "Expected goals (xG)": "expected_goals",
    "Total shots": "shots_total",
    "Shots on target": "shots_on_target",
    "Corner kicks": "corners",
    "Fouls": "fouls",
    "Passes": "passes_total",
    "Accurate passes": "passes_accurate",
    "Total tackles": "tackles_total",
    "Yellow cards": "yellow_cards",
    "Red cards": "red_cards",
}


@dataclass
class MatchStatsResult:
    rows: list[dict[str, Any]]
    status: str
    error: str | None = None


def sync_matches_stub(settings: Settings, season: int, from_round: int, to_round: int) -> None:
    season_id = load_season_id(settings, season) or SERIE_B_2026_METADATA.get("season_id")
    if season_id is None:
        logger.info("season_id not cached; attempting to resolve via Selenium...")
        season_id = resolve_season_id(settings, season)

    if season_id is None:
        logger.error(
            "season_id unavailable for season %s — run 'sync-competition --season %s' first",
            season,
            season,
        )
        return

    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except Exception as exc:
        logger.warning("Selenium not available for match sync: %s", exc)
        return

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)

    all_matches: list[dict[str, Any]] = []
    try:
        driver.get(SERIE_B_2026_METADATA["competition_url"])
        for round_num in range(from_round, to_round + 1):
            matches = fetch_round_matches(
                driver,
                tournament_id=SERIE_B_2026_METADATA["tournament_id"],
                season_id=season_id,
                round_num=round_num,
                season=season,
            )
            logger.info("Round %s: %s matches fetched", round_num, len(matches))
            all_matches.extend(matches)
    finally:
        driver.quit()

    completed = [m for m in all_matches if m["status"] == "completed"]

    raw_dir = settings.raw_dir / "sofascore" / "matches"
    write_json(
        raw_dir / f"serie_b_{season}_rounds_{from_round}_{to_round}.json",
        {
            "season": season,
            "season_id": season_id,
            "from_round": from_round,
            "to_round": to_round,
            "match_count": len(all_matches),
            "completed_count": len(completed),
            "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        },
    )

    base = settings.processed_dir / str(season) / "matches"

    # matches.csv: upsert by match_id so previous rounds are preserved
    _upsert_matches_csv(base / "matches.csv", [_build_match_row(m) for m in all_matches])

    # team_match_stats.csv: skip matches already processed in prior runs
    existing_stats_csv = base / "team_match_stats.csv"
    existing_stats_rows: list[dict] = []
    already_processed: set[str] = set()
    if existing_stats_csv.exists():
        with open(existing_stats_csv, encoding="utf-8") as f:
            existing_stats_rows = list(csv.DictReader(f))
            already_processed = {r["match_id"] for r in existing_stats_rows if r.get("match_id")}

    new_completed = [m for m in completed if m.get("match_code") not in already_processed]
    if new_completed:
        logger.info(
            "Extracting team stats for %s new completed matches (skipping %s already persisted)",
            len(new_completed), len(already_processed),
        )
        new_stats_rows = _extract_round_team_stats(new_completed)
        all_stats_rows = existing_stats_rows + new_stats_rows
    else:
        logger.info("Team stats up to date — no new completed matches to process")
        all_stats_rows = existing_stats_rows

    write_csv(base / "team_match_stats.csv", all_stats_rows)
    write_csv(base / "lineups.csv", [])
    write_csv(settings.processed_dir / str(season) / "events" / "events.csv", [])
    write_csv(settings.processed_dir / str(season) / "events" / "shots.csv", [])
    _upsert_match_ids(base / "match_ids.csv", all_matches)


def _upsert_matches_csv(path: "Path", new_rows: list[dict[str, Any]]) -> None:
    """Merge new match rows into matches.csv, keyed on match_id. Preserves existing rows."""
    from pathlib import Path as _Path

    existing: dict[str, dict] = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = row.get("match_id", "")
                if key:
                    existing[key] = row

    for row in new_rows:
        key = str(row.get("match_id", "") or "")
        if key:
            existing[key] = row

    rows = list(existing.values())
    if rows:
        write_csv(path, rows)
        logger.info("matches.csv upserted: %s total rows", len(rows))


_MATCH_IDS_COLS = [
    "season", "competition", "round", "home_team", "away_team",
    "match_date_utc", "home_score", "away_score", "status",
    "event_id", "match_code", "match_url",
    "seed_status", "discovery_status", "data_status", "is_completed",
]


def _upsert_match_ids(path: "Path", matches: list[dict[str, Any]]) -> None:
    """Merge `matches` into match_ids.csv, keyed on event_id. Preserves existing rows."""
    from pathlib import Path as _Path

    existing: dict[str, dict] = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                key = row.get("event_id", "")
                if key:
                    existing[key] = row

    for m in matches:
        eid = str(m.get("event_id", "") or "")
        if not eid:
            continue
        existing[eid] = {
            "season": m.get("season"),
            "competition": m.get("competition"),
            "round": m.get("round"),
            "home_team": m.get("home_team"),
            "away_team": m.get("away_team"),
            "match_date_utc": m.get("match_date_utc"),
            "home_score": m.get("home_score"),
            "away_score": m.get("away_score"),
            "status": m.get("status"),
            "event_id": eid,
            "match_code": m.get("match_code"),
            "match_url": m.get("match_url"),
            "seed_status": "resolved" if m.get("match_code") else "pending",
            "discovery_status": m.get("discovery_status", "identified"),
            "data_status": m.get("data_status"),
            "is_completed": m.get("is_completed"),
        }

    rows = list(existing.values())
    if rows:
        write_csv(path, rows)
        logger.info("match_ids.csv upserted: %s total rows", len(rows))


def _build_match_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "season": item["season"],
        "competition": item["competition"],
        "round": item["round"],
        "match_id": item["match_code"],
        "match_date_utc": item["match_date_utc"],
        "home_team_name": item["home_team"],
        "away_team_name": item["away_team"],
        "home_score": item["home_score"],
        "away_score": item["away_score"],
        "status": item["status"],
        "venue_name": item["venue_name"],
        "source": item["source"],
        "source_detail": item["source_detail"],
        "source_url": item["match_url"],
        "data_status": item["data_status"],
        "last_updated_at": item["last_updated_at"],
    }


def _extract_round_team_stats(round_matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return extract_team_stats_for_matches(
        [item for item in round_matches if item.get("event_id")]
    )


def _extract_match_team_stats(driver: Any, match_row: dict[str, Any]) -> MatchStatsResult:
    last_error: str | None = None
    for _attempt in range(2):
        try:
            driver.get(match_row["match_url"])
            parsed = _fetch_statistics_json(driver, match_row)
            if parsed is None:
                parsed = _extract_statistics_from_dom(driver)
            status = _classify_statistics_status(parsed)
            rows = []
            for side, team_name in [("home", match_row["home_team"]), ("away", match_row["away_team"])]:
                rows.append(
                    {
                        "season": match_row["season"],
                        "competition": match_row["competition"],
                        "round": match_row["round"],
                        "match_id": match_row["match_code"],
                        "team_name": team_name,
                        "is_home": side == "home",
                        **_build_team_stat_fields(parsed, side, status),
                        "source_url": match_row["match_url"],
                        "data_status": status,
                        "last_updated_at": match_row["last_updated_at"],
                    }
                )
            return MatchStatsResult(rows=rows, status=status)
        except Exception as exc:
            last_error = str(exc)
            continue
    rows = _build_missing_match_rows(match_row)
    return MatchStatsResult(rows=rows, status="advanced_stats_missing", error=last_error)


def _fetch_statistics_json(driver: Any, match_row: dict[str, Any]) -> dict[str, dict[str, Any]] | None:
    event_id = match_row.get("event_id") or _extract_event_id_from_match_url(match_row.get("match_url"))
    if not event_id:
        return None

    try:
        response = driver.execute_script(
            """
            var xhr = new XMLHttpRequest();
            xhr.open("GET", "/api/v1/event/" + arguments[0] + "/statistics", false);
            xhr.send();
            return {status: xhr.status, body: xhr.responseText};
            """,
            event_id,
        )
        if response.get("status") != 200:
            return None
        return _parse_statistics_json(json.loads(response["body"]))
    except Exception:
        return None


def _extract_statistics_from_dom(driver: Any) -> dict[str, dict[str, Any]]:
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    wait = WebDriverWait(driver, 20)
    tab = wait.until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-testid='tab-statistics']"))
    )
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", tab)
    driver.execute_script("arguments[0].click();", tab)
    wait.until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                "//*[contains(., 'Expected goals (xG)') or contains(., 'Ball possession')]",
            )
        )
    )
    parsed = wait.until(lambda current_driver: _parse_dom_statistics_when_ready(current_driver))
    return parsed


def _parse_dom_statistics_when_ready(driver: Any) -> dict[str, dict[str, Any]] | bool:
    from selenium.webdriver.common.by import By

    body_text = driver.find_element(By.TAG_NAME, "body").text
    parsed = _parse_statistics_text(body_text)
    if _classify_statistics_status(parsed) == "advanced_stats_missing":
        return False
    return parsed


def _parse_statistics_json(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    parsed: dict[str, dict[str, Any]] = {
        key: {"home": None, "away": None} for key in JSON_STAT_LABELS.values()
    }
    parsed["red_cards"] = {"home": 0, "away": 0}

    all_period = next((item for item in payload.get("statistics", []) if item.get("period") == "ALL"), None)
    if not all_period:
        return parsed

    for group in all_period.get("groups", []):
        for item in group.get("statisticsItems", []):
            field = JSON_STAT_LABELS.get(item.get("name"))
            if not field:
                continue
            parsed[field] = {
                "home": item.get("homeValue"),
                "away": item.get("awayValue"),
            }

    return parsed


def _parse_statistics_text(body_text: str) -> dict[str, dict[str, Any]]:
    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    parsed: dict[str, dict[str, Any]] = {
        key: {"home": None, "away": None} for key in DOM_STAT_LABELS.values()
    }
    parsed["red_cards"] = {"home": 0, "away": 0}

    for i in range(1, len(lines) - 1):
        field = DOM_STAT_LABELS.get(lines[i])
        if not field:
            continue
        if parsed[field]["home"] is not None:
            continue
        home_value = _coerce_stat_value(lines[i - 1])
        away_value = _coerce_stat_value(lines[i + 1])
        if "/" in str(home_value) or "/" in str(away_value):
            home_value = None
            away_value = None
        parsed[field] = {"home": home_value, "away": away_value}

    return parsed


def _coerce_stat_value(value: str) -> int | float | str | None:
    value = value.strip()
    if not value:
        return None
    if value.endswith("%"):
        value = value[:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _extract_event_id_from_match_url(match_url: str | None) -> int | None:
    if not match_url or "#id:" not in match_url:
        return None
    event_id_str = match_url.split("#id:")[-1].strip()
    if not event_id_str.isdigit():
        return None
    return int(event_id_str)


def _build_team_stat_fields(
    parsed: dict[str, dict[str, Any]],
    side: str,
    status: str,
) -> dict[str, Any]:
    if status == "advanced_stats_missing":
        return {field: None for field in STAT_FIELDS}
    return {field: parsed[field][side] for field in STAT_FIELDS}


def _build_missing_match_rows(match_row: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for side, team_name in [("home", match_row["home_team"]), ("away", match_row["away_team"])]:
        rows.append(
            {
                "season": match_row["season"],
                "competition": match_row["competition"],
                "round": match_row["round"],
                "match_id": match_row["match_code"],
                "team_name": team_name,
                "is_home": side == "home",
                **{field: None for field in STAT_FIELDS},
                "source_url": match_row["match_url"],
                "data_status": "advanced_stats_missing",
                "last_updated_at": match_row["last_updated_at"],
            }
        )
    return rows


def _classify_statistics_status(parsed: dict[str, dict[str, Any]]) -> str:
    metric_values = [
        parsed[field][side]
        for field in REQUIRED_ADVANCED_FIELDS
        for side in ("home", "away")
    ]
    present_count = sum(value is not None for value in metric_values)
    if present_count == 0:
        return "advanced_stats_missing"
    if present_count == len(metric_values):
        return "advanced_stats_confirmed"
    return "advanced_stats_partial"


def extract_team_stats_for_matches(match_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    try:
        from selenium import webdriver
        from selenium.webdriver.edge.options import Options
    except Exception as exc:  # pragma: no cover
        logger.warning("Selenium not available for team stats extraction: %s", exc)
        return []

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    rows: list[dict[str, Any]] = []
    for item in match_rows:
        if not item.get("match_url") or not item.get("match_code"):
            continue
        driver = webdriver.Edge(options=options)
        driver.set_page_load_timeout(30)
        try:
            result = _extract_match_team_stats(driver, item)
            if result.error:
                logger.warning(
                    "Failed to extract advanced stats for %s x %s: %s",
                    item["home_team"],
                    item["away_team"],
                    result.error,
                )
            logger.info(
                "Advanced stats status for %s x %s: %s",
                item["home_team"],
                item["away_team"],
                result.status,
            )
            rows.extend(result.rows)
        finally:
            driver.quit()

    return rows
