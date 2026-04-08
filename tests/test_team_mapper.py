from src.extract.cbf_competition import CBF_SERIE_B_2026_CLUBS
import pandas as pd

from src.discover.team_mapper import MANUAL_TEAM_MAPPINGS, resolve_team_mapping


def test_expected_club_count() -> None:
    assert len(CBF_SERIE_B_2026_CLUBS) == 20


def test_resolve_sport_recife_mapping() -> None:
    resolved = resolve_team_mapping("Sport Recife")
    assert resolved["canonical_name"] == "sport"
    assert resolved["sofascore_team_id"] == 1959
    assert resolved["sofascore_slug"] == "sport-recife"


def test_all_serie_b_clubs_have_confirmed_manual_mapping() -> None:
    rows = []
    for club in CBF_SERIE_B_2026_CLUBS:
        resolved = resolve_team_mapping(club)
        rows.append(resolved)

    df = pd.DataFrame(rows)
    assert len(MANUAL_TEAM_MAPPINGS) == 20
    assert (df["mapping_status"] == "confirmed").all()
    assert df["sofascore_team_id"].notna().all()
