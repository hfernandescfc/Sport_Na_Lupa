from src.extract.sofascore_sport import (
    SPORT_2026_COMPETITION_SEED,
    SPORT_2026_MATCH_SEED,
    SPORT_2026_METADATA,
    SPORT_2026_RESULT_SEED,
    _build_sport_team_stats_coverage,
    _build_sport_results_rows,
    _extract_sport_team_stats,
)
from src.extract import sofascore_sport


def test_sport_team_id() -> None:
    assert SPORT_2026_METADATA["sofascore_team_id"] == 1959


def test_sport_scope_has_expected_competitions() -> None:
    names = {item["competition_name"] for item in SPORT_2026_COMPETITION_SEED}
    assert "Brasileirao Serie B" in names
    assert "Copa Betano do Brasil" in names
    assert "Pernambucano" in names
    assert "Copa do Nordeste" in names


def test_sport_has_public_match_seed_across_competitions() -> None:
    names = {item["competition_name"] for item in SPORT_2026_MATCH_SEED if item["status"] != "competition_confirmed_matches_pending"}
    assert "Brasileirao Serie B" in names
    assert "Copa Betano do Brasil" in names
    assert "Pernambucano" in names


def test_sport_has_enough_confirmed_matches() -> None:
    confirmed = [
        item
        for item in SPORT_2026_MATCH_SEED
        if item["status"] in {
            "confirmed_public_page",
            "confirmed_search_snippet",
            "confirmed_team_results_tab",
        }
    ]
    assert len(confirmed) >= 8


def test_sport_incremental_fields_exist() -> None:
    first = SPORT_2026_MATCH_SEED[0]
    assert "discovery_status" in first
    assert "data_status" in first
    assert "is_completed" in first
    assert "last_seen_at" in first
    assert "last_updated_at" in first


def test_sport_seed_includes_missing_pernambucano_and_copa_do_brasil_matches() -> None:
    pairs = {
        (item["competition_name"], item["home_team"], item["away_team"])
        for item in SPORT_2026_MATCH_SEED
    }
    assert ("Pernambucano", "AD Jaguar", "Sport") in pairs
    assert ("Pernambucano", "Sport", "Retro") in pairs
    assert ("Pernambucano", "Nautico", "Sport") in pairs
    assert ("Pernambucano", "Sport", "Santa Cruz") in pairs
    assert ("Pernambucano", "Retro", "Sport") in pairs
    assert ("Pernambucano", "Sport", "Nautico") in pairs
    assert ("Copa Betano do Brasil", "Desportiva", "Sport") in pairs


def test_sport_identified_matches_have_match_links_except_competition_placeholder() -> None:
    unresolved = [
        item
        for item in SPORT_2026_MATCH_SEED
        if item["status"] != "competition_confirmed_matches_pending"
        and (not item["match_code"] or not item["match_url"])
    ]
    assert unresolved == []


def test_extract_sport_team_stats_uses_completed_matches_only(monkeypatch) -> None:
    captured = {}

    def fake_extract(match_rows):
        captured["match_rows"] = match_rows
        return [
            {
                "season": 2026,
                "competition": "Pernambucano",
                "round": None,
                "match_id": "jOswXWd",
                "team_name": "Sport",
                "is_home": False,
                "possession": 50,
                "expected_goals": 1.2,
                "shots_total": 10,
                "shots_on_target": 4,
                "corners": 5,
                "fouls": 11,
                "passes_total": 400,
                "passes_accurate": 350,
                "tackles_total": 13,
                "yellow_cards": 2,
                "red_cards": 0,
                "source_url": "https://example.com/match",
                "data_status": "advanced_stats_confirmed",
                "last_updated_at": "2026-03-23T00:00:00Z",
            }
        ]

    monkeypatch.setattr(sofascore_sport, "extract_team_stats_for_matches", fake_extract)

    rows = _extract_sport_team_stats(2026)

    assert rows[0]["competition_name"] == "Pernambucano"
    assert rows[0]["match_id"] == "jOswXWd"
    assert rows[0]["data_status"] == "advanced_stats_confirmed"
    assert all(item["match_code"] for item in captured["match_rows"])
    assert all(item["match_url"] for item in captured["match_rows"])
    assert all(item["last_updated_at"] for item in captured["match_rows"])


def test_build_sport_team_stats_coverage_lists_missing_fields() -> None:
    coverage = _build_sport_team_stats_coverage(
        [
            {
                "season": 2026,
                "competition_name": "Copa Betano do Brasil",
                "competition_round": 3,
                "match_id": "jOsxMi",
                "team_name": "Sport",
                "is_home": True,
                "possession": 57,
                "expected_goals": 1.07,
                "shots_total": None,
                "shots_on_target": 4,
                "corners": 7,
                "fouls": 15,
                "passes_total": None,
                "passes_accurate": None,
                "tackles_total": None,
                "yellow_cards": 4,
                "red_cards": 0,
                "source_url": "https://example.com/match",
                "data_status": "advanced_stats_partial",
                "last_updated_at": "2026-03-23T00:00:00Z",
            }
        ]
    )

    assert coverage[0]["missing_fields_count"] == 4
    assert coverage[0]["missing_required_fields_count"] == 3
    assert coverage[0]["missing_fields"] == "shots_total|passes_total|passes_accurate|tackles_total"
    assert coverage[0]["missing_required_fields"] == "shots_total|passes_total|tackles_total"


def test_completed_sport_matches_have_result_seed_entries() -> None:
    result_urls = {item["match_url"] for item in SPORT_2026_RESULT_SEED}
    completed_urls = {
        item["match_url"]
        for item in SPORT_2026_MATCH_SEED
        if item["is_completed"] and item["match_url"]
    }
    assert completed_urls.issubset(result_urls)


def test_build_sport_results_rows_materializes_completed_results() -> None:
    rows = _build_sport_results_rows(2026)

    assert len(rows) >= 15
    desportiva = next(row for row in rows if row["match_id"] == "jOslFn")
    assert desportiva["decision_type"] == "penalties"
    assert desportiva["away_penalty_score"] == 4
    cuiaba = next(row for row in rows if row["match_id"] == "jOscJu")
    assert cuiaba["home_score"] == 0
    assert cuiaba["away_score"] == 0
