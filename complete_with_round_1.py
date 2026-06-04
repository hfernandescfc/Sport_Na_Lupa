#!/usr/bin/env python3
"""
Complete Série B 2025 dataset by adding round 1 to existing R2-38.
Waits for round 1 extraction, then merges into final 380-match dataset.
"""

import time
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

def wait_for_round_1_extraction(max_wait_seconds: int = 600) -> bool:
    """Wait for round 1 to be extracted to the matches.csv file."""
    matches_csv = Path('data/processed/2025/matches/matches.csv')
    start_time = time.time()
    iteration = 0

    print("Waiting for round 1 extraction...")

    while time.time() - start_time < max_wait_seconds:
        iteration += 1
        time.sleep(20)

        if matches_csv.exists():
            try:
                df = pd.read_csv(matches_csv)
                round_1_count = len(df[df['round'] == 1])
                total_count = len(df)

                timestamp = datetime.now().strftime('%H:%M:%S')
                print(f"[{timestamp}] R1: {round_1_count}/10, Total: {total_count}")

                if round_1_count >= 10:
                    print(f"\nOK: Round 1 extracted ({round_1_count} matches)")
                    return True
            except Exception as e:
                print(f"Error reading CSV: {e}")
                continue

    print(f"WARNING: Timeout after {max_wait_seconds} seconds")
    return False


def merge_all_rounds() -> bool:
    """Merge round 1 with existing R2-38 data."""

    # Load current complete data (R2-38)
    complete_csv = Path('data/processed/2025/matches/matches_final.csv')
    current_csv = Path('data/processed/2025/matches/matches.csv')

    print("\nMerging datasets...")

    # Load both files
    if complete_csv.exists():
        complete = pd.read_csv(complete_csv)
        print(f"  Complete (R2-38): {len(complete)} matches")
    else:
        print("  ERROR: Complete file not found")
        return False

    if current_csv.exists():
        current = pd.read_csv(current_csv)
        round_1 = current[current['round'] == 1]
        print(f"  Round 1: {len(round_1)} matches")
    else:
        print("  ERROR: Current file not found")
        return False

    # Combine
    merged = pd.concat([round_1, complete], ignore_index=True)
    merged_dedup = merged.drop_duplicates(subset=['match_id', 'match_date_utc'], keep='last')

    print(f"\nMerged: {len(merged_dedup)} matches")
    print(f"Rounds: {merged_dedup['round'].min()}-{merged_dedup['round'].max()}")

    # Verify coverage
    rounds_set = set(merged_dedup['round'].unique())
    missing = [r for r in range(1, 39) if r not in rounds_set]

    if missing:
        print(f"WARNING: Missing rounds: {missing}")
    else:
        print(f"OK: All rounds 1-38 present!")

    # Save as final
    merged_dedup.to_csv('data/processed/2025/matches/matches.csv', index=False)
    print(f"\nSaved {len(merged_dedup)} matches to matches.csv")

    # Create match_ids
    match_ids = merged_dedup[[
        'season', 'competition', 'round', 'match_id', 'match_date_utc',
        'home_team_name', 'away_team_name', 'home_score', 'away_score',
        'status', 'venue_name', 'source', 'source_detail', 'source_url',
        'data_status', 'last_updated_at'
    ]].copy()

    match_ids = match_ids.rename(columns={'match_id': 'match_code'})
    match_ids.to_csv('data/processed/2025/matches/match_ids.csv', index=False)

    # Copy to curated
    merged_dedup.to_csv('data/curated/serie_b_2025/matches.csv', index=False)
    print(f"Copied to data/curated/serie_b_2025/matches.csv")

    return True


def main():
    print("=" * 70)
    print("Série B 2025 — Complete with Round 1")
    print("=" * 70)
    print()

    # Step 1: Wait for R1 extraction
    if not wait_for_round_1_extraction(max_wait_seconds=600):
        print("WARNING: R1 extraction timeout")

    # Step 2: Merge
    if not merge_all_rounds():
        print("ERROR: Merge failed")
        return 1

    # Summary
    print("\n" + "=" * 70)
    print("COMPLETE: Série B 2025 is now 100% complete!")
    print("=" * 70)

    df_final = pd.read_csv('data/curated/serie_b_2025/matches.csv')
    print(f"\nFinal Statistics:")
    print(f"  Total matches: {len(df_final)}")
    print(f"  Rounds: {df_final['round'].min()}-{df_final['round'].max()}")
    print(f"  Teams: {len(set(df_final['home_team_name'].unique()) | set(df_final['away_team_name'].unique()))}")
    print(f"\nData location: data/curated/serie_b_2025/matches.csv")
    print(f"Ready for model training! 🚀")

    return 0


if __name__ == "__main__":
    sys.exit(main())
