from src.extract.sofascore_competition import ROUND_1_MATCHES, SERIE_B_2026_METADATA


def test_serie_b_tournament_id() -> None:
    assert SERIE_B_2026_METADATA["tournament_id"] == 390
    assert SERIE_B_2026_METADATA["status"] == "in_progress"


def test_round_1_match_count() -> None:
    assert len(ROUND_1_MATCHES) == 10


def test_round_1_all_rows_have_core_fields() -> None:
    for item in ROUND_1_MATCHES:
        assert item["home_team"]
        assert item["away_team"]
        assert item["venue_name"]
        assert item["match_date_utc"]


def test_round_1_rows_include_incremental_control_fields() -> None:
    for item in ROUND_1_MATCHES:
        assert item["discovery_status"] in {"scheduled", "identified"}
        assert item["data_status"] in {"fixture_only", "score_confirmed", "event_level_partial"}
        assert isinstance(item["is_completed"], bool)
