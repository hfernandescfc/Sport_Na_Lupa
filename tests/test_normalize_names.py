from src.utils.normalize import normalize_team_name


def test_normalize_known_aliases() -> None:
    assert normalize_team_name("Botafogo-SP") == "botafogo-sp"
    assert normalize_team_name("Sport Recife") == "sport"
    assert normalize_team_name("Gremio Novorizontino - Saf") == "novorizontino"

