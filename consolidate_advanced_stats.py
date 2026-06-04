#!/usr/bin/env python3
"""
Wait for advanced stats extraction and then normalize via transform.
"""

import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

def wait_for_team_stats_extraction(max_wait_seconds: int = 900) -> bool:
    """Wait for team_match_stats.csv to be created with data."""
    stats_csv = Path('data/processed/2025/matches/team_match_stats.csv')
    start_time = time.time()
    iteration = 0

    print("Waiting for team statistics extraction...")

    while time.time() - start_time < max_wait_seconds:
        iteration += 1
        time.sleep(30)

        if stats_csv.exists():
            try:
                df = pd.read_csv(stats_csv)
                if len(df) > 0:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] Extracted {len(df)} team-match records")

                    if len(df) >= 300:  # Expect ~350 records (2 teams per match)
                        print(f"\nOK: Advanced stats extraction complete")
                        return True
            except Exception as e:
                print(f"Error reading CSV: {e}")
                continue

    print(f"WARNING: Timeout after {max_wait_seconds} seconds")
    return False


def run_transform():
    """Run transform to normalize advanced stats."""
    print("\nRunning transform to normalize advanced stats...")
    result = subprocess.run([sys.executable, '-m', 'src.main', 'transform', '--season', '2025'])
    return result.returncode == 0


def main():
    print("=" * 70)
    print("Série B 2025 — Advanced Stats Consolidation")
    print("=" * 70)
    print()

    # Wait for extraction
    if not wait_for_team_stats_extraction(max_wait_seconds=900):
        print("WARNING: Extraction timeout")
        # Continue anyway

    # Check what we got
    stats_csv = Path('data/processed/2025/matches/team_match_stats.csv')
    if stats_csv.exists():
        df = pd.read_csv(stats_csv)
        print(f"\nExtraction summary:")
        print(f"  Records: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Sample stats: {[c for c in df.columns if c not in ['match_code', 'event_id', 'team_id', 'team_name']][:10]}")

    # Run transform
    if run_transform():
        print("\nOK: Transform completed")
    else:
        print("\nWARNING: Transform had issues")

    print("\n" + "=" * 70)
    print("Advanced statistics ready for analysis!")
    print("=" * 70)
    print("\nFiles:")
    print("  - data/processed/2025/matches/team_match_stats.csv (raw)")
    print("  - data/curated/serie_b_2025/team_match_stats.csv (normalized)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
