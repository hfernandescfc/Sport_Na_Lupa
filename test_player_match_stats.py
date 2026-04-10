"""
Teste rapido do extrator sofascore_player_match_stats.
Busca as estatisticas de Felipinho na partida Londrina x Sport (R3 2026).

Uso:
    python test_player_match_stats.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.extract.sofascore_player_match_stats import fetch_match_player_stats_batch

EVENT_ID = 15526008
PLAYER_IDS = [1048276]  # Felipinho
MATCH_URL = "https://www.sofascore.com/football/match/londrina-sport-recife/jOsxP"

MATCH_META = {
    "season": 2026,
    "competition": "serie_b",
    "round": 3,
    "home_team": "Londrina",
    "away_team": "Sport Recife",
    "match_code": "jOsxP",
}

OUTPUT = Path("data/raw/sofascore/discovery/player_stats_15526008_felipinho.json")


def main():
    print(f"Buscando estatisticas: evento={EVENT_ID}, jogadores={PLAYER_IDS}")
    rows = fetch_match_player_stats_batch(
        event_id=EVENT_ID,
        player_ids=PLAYER_IDS,
        match_url=MATCH_URL,
        match_meta=MATCH_META,
        output_path=OUTPUT,
    )

    if not rows:
        print("Nenhuma linha retornada.")
        return

    for row in rows:
        print(f"\n=== {row['player_name']} | {row['team_name']} ===")

        print("\n  PASSES:")
        print(f"    Total:            {row['accurate_pass']}/{row['total_pass']}")
        print(f"    Campo proprio:    {row['accurate_own_half_passes']}/{row['total_own_half_passes']}")
        print(f"    Campo adversario: {row['accurate_opposition_half_passes']}/{row['total_opposition_half_passes']}")
        print(f"    Bolas longas:     {row['accurate_long_balls']}/{row['total_long_balls']}")
        print(f"    Cruzamentos:      {row['accurate_cross']}/{row['total_cross']}")
        print(f"    Passes-chave:     {row['key_pass']}")

        print("\n  PROGRESSAO (metros em direcao ao gol adversario):")
        print(f"    Total progressao:         {row['total_progression']:.1f}m")
        print(f"    Progressao via conducao:  {row['total_progressive_ball_carries_distance']:.1f}m")
        print(f"    Progressao via passe:     {row['progressive_pass_distance']:.1f}m  [derivado]")
        print(f"    Conduções progressivas:   {row['progressive_ball_carries_count']}")
        print(f"    Melhor conducao:          {row['best_ball_carry_progression']:.1f}m")

        print("\n  GERAL:")
        print(f"    Minutos:     {row['minutes_played']}")
        print(f"    Nota:        {row['rating']}")
        print(f"    Toques:      {row['touches']}")
        print(f"    xA:          {row['expected_assists']}")

    print(f"\nSalvo em: {OUTPUT}")


if __name__ == "__main__":
    main()
