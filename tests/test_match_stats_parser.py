from src.extract import sofascore_match
from src.extract.sofascore_match import (
    _build_missing_match_rows,
    _classify_statistics_status,
    _extract_event_id_from_match_url,
    _extract_match_team_stats,
    _parse_statistics_json,
    _parse_statistics_text,
)


def test_parse_statistics_json_extracts_core_team_metrics() -> None:
    sample = {
        "statistics": [
            {
                "period": "ALL",
                "groups": [
                    {
                        "groupName": "Match overview",
                        "statisticsItems": [
                            {"name": "Ball possession", "homeValue": 42, "awayValue": 58},
                            {"name": "Expected goals", "homeValue": 1.27, "awayValue": 0.75},
                            {"name": "Total shots", "homeValue": 13, "awayValue": 10},
                            {"name": "Corner kicks", "homeValue": 0, "awayValue": 1},
                            {"name": "Fouls", "homeValue": 20, "awayValue": 21},
                            {"name": "Passes", "homeValue": 361, "awayValue": 504},
                            {"name": "Accurate passes", "homeValue": 288, "awayValue": 429},
                            {"name": "Total tackles", "homeValue": 11, "awayValue": 6},
                            {"name": "Yellow cards", "homeValue": 1, "awayValue": 2},
                        ],
                    }
                ],
            }
        ]
    }
    parsed = _parse_statistics_json(sample)
    assert parsed["possession"]["home"] == 42
    assert parsed["expected_goals"]["away"] == 0.75
    assert parsed["shots_total"]["home"] == 13
    assert parsed["corners"]["away"] == 1
    assert parsed["passes_total"]["away"] == 504
    assert parsed["passes_accurate"]["home"] == 288
    assert parsed["tackles_total"]["home"] == 11
    assert parsed["yellow_cards"]["away"] == 2
    assert parsed["red_cards"]["home"] == 0


def test_parse_statistics_text_extracts_metrics_from_statistics_tab_snapshot() -> None:
    body_text = "\n".join(
        [
            "Match overview",
            "52%",
            "Ball possession",
            "48%",
            "1.77",
            "Expected goals (xG)",
            "0.24",
            "21",
            "Total shots",
            "4",
            "3",
            "Corner kicks",
            "8",
            "18",
            "Fouls",
            "14",
            "407",
            "Passes",
            "382",
            "14",
            "Tackles",
            "17",
            "2",
            "Yellow cards",
            "0",
        ]
    )
    parsed = _parse_statistics_text(body_text)
    assert parsed["possession"] == {"home": 52, "away": 48}
    assert parsed["expected_goals"] == {"home": 1.77, "away": 0.24}
    assert parsed["shots_total"] == {"home": 21, "away": 4}
    assert parsed["corners"] == {"home": 3, "away": 8}
    assert parsed["fouls"] == {"home": 18, "away": 14}
    assert parsed["passes_total"] == {"home": 407, "away": 382}
    assert parsed["yellow_cards"] == {"home": 2, "away": 0}


def test_classify_statistics_status_distinguishes_confirmed_partial_and_missing() -> None:
    confirmed = {
        field: {"home": 1, "away": 1}
        for field in sofascore_match.STAT_FIELDS
    }
    partial = {
        field: {"home": None, "away": None}
        for field in sofascore_match.STAT_FIELDS
    }
    partial["expected_goals"] = {"home": 1.1, "away": None}
    missing = {
        field: {"home": None, "away": None}
        for field in sofascore_match.STAT_FIELDS
    }

    assert _classify_statistics_status(confirmed) == "advanced_stats_confirmed"
    assert _classify_statistics_status(partial) == "advanced_stats_partial"
    assert _classify_statistics_status(missing) == "advanced_stats_missing"


def test_extract_match_team_stats_marks_missing_when_both_extractors_fail(monkeypatch) -> None:
    class DummyDriver:
        def get(self, _url: str) -> None:
            return None

    match_row = {
        "season": 2026,
        "competition": "serie_b",
        "round": 1,
        "match_code": "abc123",
        "home_team": "Sport",
        "away_team": "Cuiaba",
        "match_url": "https://example.com/match",
        "last_updated_at": "2026-03-23T00:00:00Z",
    }

    monkeypatch.setattr(sofascore_match, "_fetch_statistics_json", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        sofascore_match,
        "_extract_statistics_from_dom",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("dom failed")),
    )

    result = _extract_match_team_stats(DummyDriver(), match_row)

    assert result.status == "advanced_stats_missing"
    assert result.error == "dom failed"
    assert result.rows == _build_missing_match_rows(match_row)


def test_extract_event_id_from_match_url_reads_hash_suffix() -> None:
    assert _extract_event_id_from_match_url(
        "https://www.sofascore.com/football/match/ad-jaguar-sport-recife/jOswXWd#id:15204423"
    ) == 15204423
    assert _extract_event_id_from_match_url("https://www.sofascore.com/football/match/x/y") is None
