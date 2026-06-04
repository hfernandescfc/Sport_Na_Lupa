#!/usr/bin/env python3
"""
Consolidate complete Série B 2025 data (rounds 1-38).
Merges partial extractions into unified dataset.
"""

import pandas as pd
from pathlib import Path
import sys

def consolidate_matches():
    """Merge rounds 1-20 and 21-38 into complete matches.csv"""

    matches_csv = Path('data/processed/2025/matches/matches.csv')

    if not matches_csv.exists():
        print("ERROR: matches.csv not found")
        return False

    # Load current matches
    df = pd.read_csv(matches_csv, dtype=str)
    initial_count = len(df)

    print(f"Loaded {initial_count} matches from matches.csv")

    # Remove duplicates (by match_code + match_date_utc)
    df_dedup = df.drop_duplicates(subset=['match_id', 'match_date_utc'], keep='last')
    dedup_count = len(df_dedup)

    if dedup_count < initial_count:
        print(f"Removed {initial_count - dedup_count} duplicates")
        df_dedup.to_csv(matches_csv, index=False)
        print(f"Saved {dedup_count} unique matches")

    # Update match_ids.csv
    match_ids = df_dedup[[
        'season', 'competition', 'round', 'match_id', 'match_date_utc',
        'home_team_name', 'away_team_name', 'home_score', 'away_score',
        'status', 'venue_name', 'source', 'source_detail', 'source_url',
        'data_status', 'last_updated_at'
    ]].copy()

    match_ids = match_ids.rename(columns={'match_id': 'match_code'})

    match_ids_path = Path('data/processed/2025/matches/match_ids.csv')
    match_ids.to_csv(match_ids_path, index=False)

    print(f"Updated match_ids.csv with {len(match_ids)} rows")

    # Summary stats
    print("\n" + "="*70)
    print("CONSOLIDATION SUMMARY")
    print("="*70)
    print(f"Total matches: {len(df_dedup)}")
    print(f"Completed: {(df_dedup['status'] == 'completed').sum()}")
    print(f"Scheduled/Pending: {(df_dedup['status'] != 'completed').sum()}")
    print(f"Rounds covered: {df_dedup['round'].min()}-{df_dedup['round'].max()}")

    # Team coverage
    all_teams = set(df_dedup['home_team_name'].unique()) | set(df_dedup['away_team_name'].unique())
    print(f"Teams: {len(all_teams)}/20")

    return True


def main():
    print("="*70)
    print("Consolidate Série B 2025 Complete Dataset")
    print("="*70)
    print()

    success = consolidate_matches()

    if success:
        print("\nOK: Consolidation complete")
        print("\nNext step: Run transform")
        print("  python -m src.main transform --season 2025")
        return 0
    else:
        print("\nERROR: Consolidation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
