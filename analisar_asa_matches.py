#!/usr/bin/env python3
"""Analyze ASA-AL matches collected."""

import csv
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def analyze_asa_matches():
    """Analyze all ASA matches collected."""

    matches_file = Path("data/processed/2026/opponents/asa-al/matches.csv")

    if not matches_file.exists():
        print(f"Erro: {matches_file} nao encontrado")
        return

    matches = []
    comps = defaultdict(list)
    wins = 0
    draws = 0
    losses = 0
    goals_for = 0
    goals_against = 0

    with open(matches_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            matches.append(row)

            home_team = row.get('home_team')
            away_team = row.get('away_team')
            home_score = float(row.get('home_score', 0) or 0)
            away_score = float(row.get('away_score', 0) or 0)
            comp = row.get('competition_name', 'Unknown')

            comps[comp].append(row)

            # Determine ASA result
            if home_team.upper() == 'ASA':
                goals_for += home_score
                goals_against += away_score
                if home_score > away_score:
                    wins += 1
                elif home_score == away_score:
                    draws += 1
                else:
                    losses += 1
            else:
                goals_for += away_score
                goals_against += home_score
                if away_score > home_score:
                    wins += 1
                elif away_score == home_score:
                    draws += 1
                else:
                    losses += 1

    # Print summary
    print("\n" + "="*100)
    print("ASA-AL — TEMPORADA 2026 — RESUMO")
    print("="*100)

    print(f"\nPartidas disputadas: {len(matches)}")
    print(f"\nSaldos:")
    print(f"  Vitorias: {wins}")
    print(f"  Empates: {draws}")
    print(f"  Derrotas: {losses}")
    print(f"  Aproveitamento: {100*wins/(len(matches)) if matches else 0:.1f}%")

    print(f"\nGols:")
    print(f"  Feitos: {int(goals_for)}")
    print(f"  Sofridos: {int(goals_against)}")
    print(f"  Diferenca: {int(goals_for - goals_against)}")
    print(f"  Media feita: {goals_for/len(matches):.1f} por jogo" if matches else "")
    print(f"  Media sofrida: {goals_against/len(matches):.1f} por jogo" if matches else "")

    print(f"\nPor Competicao:")
    for comp in sorted(comps.keys()):
        comp_matches = comps[comp]
        comp_wins = 0
        comp_goals_for = 0
        comp_goals_against = 0

        for match in comp_matches:
            home_team = match.get('home_team')
            home_score = float(match.get('home_score', 0) or 0)
            away_score = float(match.get('away_score', 0) or 0)

            if home_team.upper() == 'ASA':
                comp_goals_for += home_score
                comp_goals_against += away_score
                if home_score > away_score:
                    comp_wins += 1
            else:
                comp_goals_for += away_score
                comp_goals_against += home_score
                if away_score > home_score:
                    comp_wins += 1

        print(f"  {comp:35} {len(comp_matches):2}J | {comp_wins:2}V | {int(comp_goals_for)}G x {int(comp_goals_against)}C")

    print(f"\n" + "-"*100)
    print(f"{'Data':<12} {'Competicao':<35} {'Adversario':<25} {'Resultado':<12} {'Status'}")
    print("-"*100)

    for match in sorted(matches, key=lambda x: x.get('match_date_utc', '')):
        date_str = match.get('match_date_utc', '')[:10] if match.get('match_date_utc') else 'N/A'
        comp = match.get('competition_name', 'N/A')[:33]
        home = match.get('home_team', '')
        away = match.get('away_team', '')
        home_score = int(float(match.get('home_score', 0) or 0))
        away_score = int(float(match.get('away_score', 0) or 0))

        # Determine opponent and result
        if home.upper() == 'ASA':
            opponent = away
            result = f"ASA {home_score} x {away_score} {away}"
        else:
            opponent = home
            result = f"{home} {home_score} x {away_score} ASA"

        status = match.get('status', 'N/A')

        print(f"{date_str:<12} {comp:<35} {opponent:25} {result:<12} {status}")

    print("\n" + "="*100)
    print(f"Arquivo salvo em: {matches_file}")
    print("="*100)

if __name__ == "__main__":
    analyze_asa_matches()
