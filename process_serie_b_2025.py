#!/usr/bin/env python3
"""
Complete processing pipeline for Série B 2025 historical data.
Runs: extraction → transform → validate → quality report
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

def run_command(cmd: list, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*70}")
    print(f"▶ {description}")
    print(f"{'='*70}")
    print(f"$ {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    if result.returncode == 0:
        print(f"\n✅ {description} completed successfully")
        return True
    else:
        print(f"\n❌ {description} failed with exit code {result.returncode}")
        return False


def main():
    base_dir = Path(__file__).parent

    print("""
╔════════════════════════════════════════════════════════════════════════╗
║          Série B 2025 — Complete Historical Data Pipeline             ║
║                  (Extraction → Transform → Validate)                   ║
╚════════════════════════════════════════════════════════════════════════╝
    """)

    steps = [
        # Phase 2: Transform
        (
            [sys.executable, "-m", "src.main", "transform", "--season", "2025"],
            "Transform raw data into curated tables (matches, team_stats, player_stats, incidents)"
        ),
        # Generate standings with xPts
        (
            [sys.executable, "-m", "src.main", "transform-standings", "--season", "2025"],
            "Generate expected points table (xPts, SOS, expected results)"
        ),
        # Phase 3: Validation
        (
            [sys.executable, "-m", "src.main", "validate", "--season", "2025"],
            "Run quality checks and generate validation report"
        ),
    ]

    results = {}
    for cmd, desc in steps:
        success = run_command(cmd, desc)
        results[desc] = success
        if not success and "quality checks" not in desc.lower():
            print("\n⚠️  Continuing despite error...")

    print(f"\n{'='*70}")
    print("PIPELINE SUMMARY")
    print(f"{'='*70}")

    all_passed = all(results.values())

    for desc, success in results.items():
        status = "✅" if success else "❌"
        print(f"{status} {desc}")

    print(f"\n{'='*70}")
    if all_passed:
        print("🎉 All pipeline steps completed successfully!")
        print("\n📊 Série B 2025 data is ready for analysis:")
        print("   - data/curated/serie_b_2025/matches.csv")
        print("   - data/curated/serie_b_2025/team_match_stats.csv")
        print("   - data/curated/serie_b_2025/player_match_stats.csv")
        print("   - data/curated/serie_b_2025/expected_points_table.csv")
        print("   - data/curated/serie_b_2025/validation_report.json")
        return 0
    else:
        print("⚠️  Some steps failed. Check logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
