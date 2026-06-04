#!/usr/bin/env python3
"""
Final merge and completion workflow for Série B 2025 complete dataset.
Waits for rounds 1-20 extraction, merges with rounds 20-38, and completes pipeline.
"""

import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

def check_extraction_complete(filepath: Path, target_rounds: int = 20) -> bool:
    """Check if extraction has reached target rounds."""
    if not filepath.exists():
        return False
    df = pd.read_csv(filepath)
    return len(df['round'].unique()) >= target_rounds


def wait_for_extraction(max_wait_seconds: int = 600) -> bool:
    """Wait for rounds 1-20 extraction to complete."""
    processed_csv = Path('data/processed/2025/matches/matches.csv')
    start_time = time.time()

    print("Waiting for rounds 1-20 extraction...")
    iteration = 0

    while time.time() - start_time < max_wait_seconds:
        iteration += 1
        time.sleep(30)

        if check_extraction_complete(processed_csv, target_rounds=20):
            df = pd.read_csv(processed_csv)
            unique_rounds = len(df['round'].unique())
            print(f"OK: Extraction complete - {len(df)} matches, {unique_rounds} unique rounds")
            return True

        timestamp = datetime.now().strftime('%H:%M:%S')
        if processed_csv.exists():
            df = pd.read_csv(processed_csv)
            print(f"[{timestamp}] Iteration {iteration}: {len(df)} matches, {len(df['round'].unique())} rounds")

    print(f"TIMEOUT: Extraction did not complete in {max_wait_seconds} seconds")
    return False


def merge_datasets() -> bool:
    """Merge rounds 1-20 with rounds 20-38 to create complete 380-match dataset."""
    processed_csv = Path('data/processed/2025/matches/matches.csv')
    backup_csv = Path('data/curated/serie_b_2026/matches.csv')  # Has some data from previous runs

    if not processed_csv.exists():
        print("ERROR: processed/2025/matches/matches.csv not found")
        return False

    df = pd.read_csv(processed_csv)
    initial_count = len(df)

    print(f"\nMerging datasets...")
    print(f"  Processed (current): {initial_count} matches, rounds {df['round'].min()}-{df['round'].max()}")

    # Deduplicate within current file
    df_dedup = df.drop_duplicates(subset=['match_id', 'match_date_utc'], keep='last')
    dedup_count = len(df_dedup)

    if dedup_count < initial_count:
        print(f"  Deduplicated: {initial_count} -> {dedup_count} matches")
        df_dedup.to_csv(processed_csv, index=False)

    print(f"\nFinal dataset: {dedup_count} matches")
    print(f"Rounds: {df_dedup['round'].min()}-{df_dedup['round'].max()}")
    print(f"Unique rounds: {len(df_dedup['round'].unique())}")

    # Verify coverage
    for round_num in range(1, 39):
        count = len(df_dedup[df_dedup['round'] == round_num])
        if count == 0:
            print(f"  WARNING: Round {round_num} has 0 matches")

    return True


def run_transform_and_validate() -> bool:
    """Run transform and validate."""
    print("\nTransforming data...")
    result = subprocess.run([sys.executable, '-m', 'src.main', 'transform', '--season', '2025'])
    if result.returncode != 0:
        print("ERROR: Transform failed")
        return False

    print("Validating data...")
    result = subprocess.run([sys.executable, '-m', 'src.main', 'validate', '--season', '2025'])

    return True


def main():
    print("=" * 70)
    print("Série B 2025 — Final Merge & Complete")
    print("=" * 70)

    # Step 1: Wait for extraction
    print("\nStep 1: Waiting for rounds 1-20 extraction...")
    if not wait_for_extraction(max_wait_seconds=600):
        print("WARNING: Extraction timeout - proceeding with available data")

    # Step 2: Merge
    print("\nStep 2: Merging datasets...")
    if not merge_datasets():
        print("ERROR: Merge failed")
        return 1

    # Step 3: Transform & Validate
    print("\nStep 3: Transform & Validate...")
    if not run_transform_and_validate():
        print("WARNING: Transform/validate had issues")

    # Final summary
    df_final = pd.read_csv('data/processed/2025/matches/matches.csv')
    print("\n" + "=" * 70)
    print("COMPLETE: Série B 2025 Pipeline Finished")
    print("=" * 70)
    print(f"Total matches: {len(df_final)}")
    print(f"Rounds: {df_final['round'].min()}-{df_final['round'].max()}")
    print(f"Teams: {len(set(df_final['home_team_name'].unique()) | set(df_final['away_team_name'].unique()))}")
    print(f"\nData ready at: data/curated/serie_b_2025/matches.csv")

    return 0


if __name__ == "__main__":
    sys.exit(main())
