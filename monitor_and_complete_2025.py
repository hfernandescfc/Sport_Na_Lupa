#!/usr/bin/env python3
"""
Monitor Série B 2025 extraction and auto-complete workflow.
Polls every 30 seconds until complete, then consolidates + transforms.
"""

import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def count_matches() -> int:
    """Count matches in current file (excluding header)."""
    csv_path = Path('data/processed/2025/matches/matches.csv')
    if not csv_path.exists():
        return 0
    with open(csv_path) as f:
        return sum(1 for _ in f) - 1


def count_unique_rounds() -> int:
    """Count unique rounds in current data."""
    csv_path = Path('data/processed/2025/matches/matches.csv')
    if not csv_path.exists():
        return 0
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        return len(df['round'].unique())
    except:
        return 0


def run_command(cmd: list, description: str) -> bool:
    """Execute command and return success status."""
    print(f"\n{'='*70}")
    print(f"▶ {description}")
    print(f"{'='*70}\n")

    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    print("""
========================================================================
   Série B 2025 — Monitor & Auto-Complete Extraction Workflow
     (Waits for extraction, then consolidates & transforms)
========================================================================
    """)

    initial_count = count_matches()
    print(f"Current state: {initial_count}/380 matches, {count_unique_rounds()}/38 rounds")
    print()

    # Phase 1: Monitor extraction
    print("="*70)
    print("Phase 1: Monitoring extraction (polling every 30 seconds)")
    print("="*70)

    last_count = initial_count
    stable_iterations = 0
    max_iterations = 120  # 60 min timeout
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        time.sleep(30)

        current_count = count_matches()
        current_rounds = count_unique_rounds()

        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] Iteration {iteration:3d}: {current_count:3d}/380 matches, {current_rounds:2d}/38 rounds")

        # Check if stable
        if current_count == last_count:
            stable_iterations += 1
        else:
            stable_iterations = 0
            last_count = current_count

        # Success criteria
        if current_count >= 360:  # At least 95% (some rounds might be incomplete)
            print(f"\nOK: Reached {current_count} matches — proceeding with consolidation")
            break

        # Stability check: no changes for 3 iterations (1.5 min)
        if stable_iterations >= 3 and current_count >= 190:  # At least no regression
            print(f"\nOK: Stable at {current_count} matches (no change for 1.5 min)")
            print(f"  Proceeding with consolidation...")
            break

        # Timeout
        if iteration >= max_iterations:
            print(f"\nWARNING: Timeout after {max_iterations} iterations ({max_iterations // 2} min)")
            print(f"  Proceeding with {current_count} matches")
            break

    print()
    print("="*70)
    print("Phase 2: Consolidate data (remove duplicates, create match_ids.csv)")
    print("="*70)

    if not run_command(
        [sys.executable, 'consolidate_serie_b_2025_complete.py'],
        "Consolidate Série B 2025 data"
    ):
        print("ERROR: Consolidation failed")
        return 1

    print()
    print("="*70)
    print("Phase 3: Transform raw data to curated format")
    print("="*70)

    if not run_command(
        [sys.executable, '-m', 'src.main', 'transform', '--season', '2025'],
        "Transform matches into curated tables"
    ):
        print("ERROR: Transform failed")
        return 1

    print()
    print("="*70)
    print("Phase 4: Validate data quality")
    print("="*70)

    run_command(
        [sys.executable, '-m', 'src.main', 'validate', '--season', '2025'],
        "Run quality checks"
    )

    print()
    print("="*70)
    print("✓ COMPLETE: Série B 2025 Pipeline Finished")
    print("="*70)

    final_count = count_matches()
    final_rounds = count_unique_rounds()

    print(f"""
Final Statistics:
  • Total matches extracted: {final_count}/380 ({final_count/380*100:.1f}%)
  • Rounds covered: {final_rounds}/38
  • Data location: data/curated/serie_b_2025/matches.csv

Ready for model training! 🎉
    """)

    return 0


if __name__ == "__main__":
    sys.exit(main())
