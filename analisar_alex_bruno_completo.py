#!/usr/bin/env python3
"""Análise completa de Alex Bruno — ASA-AL 2026."""

import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def analyze_alex_bruno_complete():
    """Extract and analyze all Alex Bruno stats from ASA-AL data."""

    # Read player stats from ASA-AL extraction
    player_stats_file = Path("data/processed/2026/opponents/asa-al/player_match_stats.csv")

    if not player_stats_file.exists():
        print(f"Erro: {player_stats_file} nao encontrado")
        print("Execute primeiro: python -m src.main sync-opponent --team-key asa-al --team-id 2019 --season 2026")
        return

    # Filter for Alex Bruno
    alex_bruno_matches = []

    with open(player_stats_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Case-insensitive search
            if 'alex bruno' in row.get('player_name', '').lower():
                alex_bruno_matches.append(row)

    if not alex_bruno_matches:
        print("Alex Bruno nao encontrado nos dados")
        return

    # Create output directory
    output_dir = Path("data/processed/2026/players/alex_bruno")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    with open(output_dir / "todas_as_partidas.csv", 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=alex_bruno_matches[0].keys())
        writer.writeheader()
        writer.writerows(alex_bruno_matches)

    # Print summary
    print("\n" + "="*100)
    print("ALEX BRUNO — ASA-AL | ANALISE COMPLETA 2026")
    print("="*100)

    print(f"\nTotal de partidas: {len(alex_bruno_matches)}")

    # By tournament
    comps = defaultdict(int)
    for match in alex_bruno_matches:
        comp = match.get('tournament', 'Unknown')
        comps[comp] += 1

    print("\nPartidas por Competicao:")
    for comp, count in sorted(comps.items(), key=lambda x: x[1], reverse=True):
        print(f"  {comp}: {count}")

    # Print detailed stats
    print("\n" + "-"*100)
    print(f"{'Data':<12} {'Competicao':<30} {'Time':<12} {'Adversario':<12} {'Min':<4} {'G':<2} {'A':<2} {'Pass':<6} {'Rating':<7}")
    print("-"*100)

    for match in sorted(alex_bruno_matches, key=lambda x: x.get('date', '')):
        date_str = match.get('date', '')[:10] if match.get('date') else 'N/A'
        comp = match.get('tournament', 'N/A')[:28]
        team = match.get('team', 'N/A')[:10]
        opp = match.get('opponent', 'N/A')[:10]
        minutes = match.get('minutes_played', 'N/A')
        goals = match.get('goals', '0') or '0'
        assists = match.get('goal_assist', '0') or '0'

        # Pass accuracy
        total_pass = int(match.get('total_pass', 0) or 0)
        accurate_pass = int(match.get('accurate_pass', 0) or 0)
        pass_acc = f"{100*accurate_pass//max(1,total_pass)}%" if total_pass > 0 else "0%"

        rating = match.get('rating', 'N/A')

        print(f"{date_str:<12} {comp:<30} {team:<12} {opp:<12} {minutes:>3} {goals:>2} {assists:>2} {pass_acc:>6} {rating:>7}")

    # Aggregate statistics
    print("\n" + "="*100)
    print("ESTATISTICAS AGREGADAS")
    print("="*100)

    total_minutes = sum(int(m.get('minutes_played', 0) or 0) for m in alex_bruno_matches)
    total_goals = sum(int(m.get('goals', 0) or 0) for m in alex_bruno_matches)
    total_assists = sum(int(m.get('goal_assist', 0) or 0) for m in alex_bruno_matches)
    total_passes = sum(int(m.get('total_pass', 0) or 0) for m in alex_bruno_matches)
    accurate_passes = sum(int(m.get('accurate_pass', 0) or 0) for m in alex_bruno_matches)
    total_shots = sum(int(m.get('total_shots', 0) or 0) for m in alex_bruno_matches)
    total_duels_won = sum(int(m.get('duel_won', 0) or 0) for m in alex_bruno_matches)
    total_tackles = sum(int(m.get('tackles_total', 0) or 0) for m in alex_bruno_matches)

    ratings = [float(m.get('rating', 0) or 0) for m in alex_bruno_matches if m.get('rating')]
    xg_total = sum(float(m.get('expected_goals', 0) or 0) for m in alex_bruno_matches)

    print(f"\nPartidas disputadas: {len(alex_bruno_matches)}")
    print(f"Minutos acumulados: {total_minutes}")
    print(f"Minuto medio: {total_minutes // len(alex_bruno_matches)}")
    print(f"\nOFENSIVA:")
    print(f"  Gols: {total_goals}")
    print(f"  Assistencias: {total_assists}")
    print(f"  Chutes: {total_shots}")
    print(f"  Chutes esperados (xG): {xg_total:.2f}")
    print(f"\nPASSES:")
    print(f"  Total: {total_passes}")
    print(f"  Acurados: {accurate_passes}")
    print(f"  Precisao: {100*accurate_passes//max(1,total_passes)}%")
    print(f"\nDEFESA:")
    print(f"  Duelos vencidos: {total_duels_won}")
    print(f"  Tackles: {total_tackles}")
    print(f"\nDESEMPENHO:")
    print(f"  Rating medio: {sum(ratings)/len(ratings):.2f}" if ratings else "  Rating medio: N/A")

    # Save summary JSON
    summary = {
        "player": "Alex Bruno",
        "player_id": 1468444,
        "position": "F (Forward/Atacante)",
        "team": "ASA-AL",
        "year": 2026,
        "matches_played": len(alex_bruno_matches),
        "competitions": list(comps.keys()),
        "aggregate_stats": {
            "minutes_played": total_minutes,
            "goals": total_goals,
            "assists": total_assists,
            "shots": total_shots,
            "expected_goals": round(xg_total, 2),
            "passes": total_passes,
            "accurate_passes": accurate_passes,
            "pass_accuracy_pct": 100*accurate_passes//max(1,total_passes),
            "duels_won": total_duels_won,
            "tackles": total_tackles,
            "avg_rating": round(sum(ratings)/len(ratings), 2) if ratings else None,
        },
        "data_source": "SofaScore (via SportSofa pipeline)",
        "last_updated": datetime.now().isoformat(),
    }

    with open(output_dir / "analise_completa.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n" + "="*100)
    print(f"Arquivos salvos em: {output_dir}/")
    print(f"  - todas_as_partidas.csv (dados completos de cada partida)")
    print(f"  - analise_completa.json (resumo agregado)")
    print("="*100)

if __name__ == "__main__":
    analyze_alex_bruno_complete()
