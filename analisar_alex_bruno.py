#!/usr/bin/env python3
"""Analyze Alex Bruno from collected data."""

import csv
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def analyze_alex_bruno():
    """Extract and analyze all Alex Bruno stats from collected data."""

    # Read player stats
    player_stats_file = Path("data/processed/2026/players/player_match_stats_2026.csv")

    if not player_stats_file.exists():
        print(f"Error: {player_stats_file} not found")
        return

    # Filter for Alex Bruno
    alex_bruno_matches = []
    team_stats = defaultdict(list)

    with open(player_stats_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Case-insensitive search
            if 'alex bruno' in row.get('player_name', '').lower():
                alex_bruno_matches.append(row)
                team = row.get('team', 'Unknown')
                team_stats[team].append(row)

    if not alex_bruno_matches:
        print("Alex Bruno not found in collected data")
        return

    # Create output directory
    output_dir = Path("data/processed/2026/players/alex_bruno")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save raw data
    with open(output_dir / "matches_collected.csv", 'w', newline='', encoding='utf-8') as f:
        if alex_bruno_matches:
            writer = csv.DictWriter(f, fieldnames=alex_bruno_matches[0].keys())
            writer.writeheader()
            writer.writerows(alex_bruno_matches)

    # Summary statistics
    print("\n" + "="*80)
    print("ALEX BRUNO - ESTATISTICAS 2026")
    print("="*80)

    print(f"\nTotal de partidas coletadas: {len(alex_bruno_matches)}")

    # By team
    print("\nPor Time:")
    for team, matches in team_stats.items():
        print(f"  {team}: {len(matches)} partidas")

    # By competition
    comps = defaultdict(int)
    for match in alex_bruno_matches:
        comp = match.get('tournament', 'Unknown')
        comps[comp] += 1

    print("\nPor Competicao:")
    for comp, count in sorted(comps.items(), key=lambda x: x[1], reverse=True):
        print(f"  {comp}: {count} partidas")

    # Individual match stats
    print("\nDetalhes das Partidas:")
    print("-" * 120)
    print(f"{'Data':<15} {'Competicao':<35} {'Time':<15} {'Adv.':<15} {'Min':<4} {'Gols':<3} {'Assists':<3} {'Rating':<6} {'Passes':<7}")
    print("-" * 120)

    for match in sorted(alex_bruno_matches, key=lambda x: x.get('date', '')):
        date_str = match.get('date', '')[:10] if match.get('date') else 'N/A'
        comp = match.get('tournament', 'N/A')[:33]
        team = match.get('team', 'N/A')[:13]
        opp = match.get('opponent', 'N/A')[:13]
        minutes = match.get('minutes_played', 'N/A')
        goals = match.get('goals', '0') or '0'
        assists = match.get('goal_assist', '0') or '0'
        rating = match.get('rating', 'N/A')
        passes = match.get('total_pass', '0') or '0'

        print(f"{date_str:<15} {comp:<35} {team:<15} {opp:<15} {minutes:>3} {goals:>3} {assists:>3} {rating:>6} {passes:>7}")

    # Aggregate stats
    print("\n" + "="*80)
    print("ESTATISTICAS AGREGADAS")
    print("="*80)

    total_minutes = sum(int(m.get('minutes_played', 0) or 0) for m in alex_bruno_matches)
    total_goals = sum(int(m.get('goals', 0) or 0) for m in alex_bruno_matches)
    total_assists = sum(int(m.get('goal_assist', 0) or 0) for m in alex_bruno_matches)
    total_passes = sum(int(m.get('total_pass', 0) or 0) for m in alex_bruno_matches)
    accurate_passes = sum(int(m.get('accurate_pass', 0) or 0) for m in alex_bruno_matches)
    total_shots = sum(int(m.get('total_shots', 0) or 0) for m in alex_bruno_matches)
    ratings = [float(m.get('rating', 0) or 0) for m in alex_bruno_matches if m.get('rating')]

    print(f"\nPartidas disputadas: {len(alex_bruno_matches)}")
    print(f"Minutos acumulados: {total_minutes}")
    print(f"Gols marcados: {total_goals}")
    print(f"Assistencias: {total_assists}")
    print(f"Passes: {total_passes} (Acurados: {accurate_passes} - {100*accurate_passes//max(1,total_passes):.1f}%)")
    print(f"Chutes: {total_shots}")
    print(f"Rating medio: {sum(ratings)/len(ratings):.2f}" if ratings else "Rating medio: N/A")

    # Save summary
    summary = {
        "player": "Alex Bruno",
        "player_id": 1468444,
        "position": "F (Forward/Atacante)",
        "current_team": "ASA-AL",
        "year": 2026,
        "matches_collected": len(alex_bruno_matches),
        "total_minutes": total_minutes,
        "total_goals": total_goals,
        "total_assists": total_assists,
        "total_passes": total_passes,
        "accurate_passes": accurate_passes,
        "pass_accuracy_pct": 100*accurate_passes//max(1,total_passes),
        "total_shots": total_shots,
        "avg_rating": round(sum(ratings)/len(ratings), 2) if ratings else None,
        "competitions": list(comps.keys()),
        "teams": list(team_stats.keys()),
        "data_source": "SofaScore (via SportSofa pipeline)",
        "last_updated": datetime.now().isoformat(),
    }

    with open(output_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nDados salvos em: {output_dir}/")
    print("  - matches_collected.csv (dados completos de cada partida)")
    print("  - summary.json (resumo agregado)")
    print("\n" + "="*80)

if __name__ == "__main__":
    analyze_alex_bruno()
