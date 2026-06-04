#!/usr/bin/env python3
"""
Wait for sync-matches to complete (which extracts advanced stats),
then transform and consolidate into curated tables.
"""

import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

def wait_for_team_stats(max_wait_seconds: int = 600) -> bool:
    """Wait for team_match_stats.csv to be populated."""
    stats_csv = Path('data/processed/2025/matches/team_match_stats.csv')
    start_time = time.time()
    iteration = 0

    print("Waiting for advanced stats extraction (via sync-matches)...")

    while time.time() - start_time < max_wait_seconds:
        iteration += 1
        time.sleep(20)

        if stats_csv.exists():
            try:
                df = pd.read_csv(stats_csv)
                if len(df) > 0:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    print(f"[{timestamp}] Extracted {len(df)} team-match stats")

                    if len(df) >= 30:  # At least some data
                        print(f"\nOK: Advanced stats extraction complete")
                        return True
            except Exception as e:
                print(f"Error reading CSV: {e}")
                continue

    print(f"WARNING: Timeout after {max_wait_seconds} seconds")
    return False


def run_transform():
    """Run transform to normalize stats."""
    print("\nNormalizing advanced stats via transform...")
    result = subprocess.run([sys.executable, '-m', 'src.main', 'transform', '--season', '2025'])
    return result.returncode == 0


def main():
    print("=" * 70)
    print("Série B 2025 — Advanced Statistics Finalization")
    print("=" * 70)
    print()

    # Wait for stats
    if not wait_for_team_stats(max_wait_seconds=900):
        print("WARNING: Stats extraction timeout or no data")

    # Check what we have
    stats_csv = Path('data/processed/2025/matches/team_match_stats.csv')
    if stats_csv.exists():
        try:
            df = pd.read_csv(stats_csv)
            print(f"\nAdvanced stats summary:")
            print(f"  Records: {len(df)}")
            print(f"  Columns: {len(df.columns)}")

            # Show available metrics
            metric_cols = [c for c in df.columns if c not in ['match_id', 'match_code', 'event_id', 'team_id', 'team_name']]
            print(f"  Available metrics: {metric_cols[:15]}")

            if len(df) > 0:
                print(f"\nSample data:")
                print(df[[c for c in df.columns if c in ['team_name', 'expected_goals', 'shots_total', 'passes_accurate']]].head(3))
        except Exception as e:
            print(f"Error: {e}")

    # Run transform
    print("\n" + "=" * 70)
    if run_transform():
        print("OK: Transform completed")
    else:
        print("WARNING: Transform had issues")

    # Final summary
    print("\n" + "=" * 70)
    print("Advanced Statistics Ready!")
    print("=" * 70)

    curated_csv = Path('data/curated/serie_b_2025/team_match_stats.csv')
    if curated_csv.exists():
        df = pd.read_csv(curated_csv)
        print(f"\nFinal dataset:")
        print(f"  Location: {curated_csv}")
        print(f"  Records: {len(df)}")
        print(f"  Columns: {len(df.columns)}")
        print(f"  Ready for: predictive modeling with advanced features")

    return 0


if __name__ == "__main__":
    sys.exit(main())
