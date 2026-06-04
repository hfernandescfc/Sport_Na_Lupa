#!/bin/bash
# Auto-complete workflow for Série B 2025 extraction
# Waits for matches extraction, then consolidates and transforms

set -e

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MATCHES_FILE="$BASE_DIR/data/processed/2025/matches/matches.csv"

echo "========================================================================"
echo "Série B 2025 — Auto-Complete Workflow"
echo "========================================================================"
echo ""

# Function to count matches
count_matches() {
    wc -l < "$MATCHES_FILE" 2>/dev/null || echo "0"
}

# Step 1: Wait for extraction to complete (target: 380 matches)
echo "Step 1: Waiting for rounds 21-38 extraction..."
echo "Target: 380 matches (38 rounds × 10 matches per round)"
echo ""

last_count=0
stable_count=0

while true; do
    current=$(count_matches)
    match_count=$(($current - 1))  # subtract header

    if [ $current -eq $last_count ]; then
        stable_count=$(($stable_count + 1))
    else
        stable_count=0
        last_count=$current
    fi

    echo "[$(date +'%H:%M:%S')] Matches: $match_count/380"

    # If no changes for 5 iterations (2.5 min), assume complete
    if [ $stable_count -ge 5 ]; then
        echo ""
        echo "✓ Extraction appears complete (no changes for 2.5 min)"
        break
    fi

    # Safety check: if matches >= 360, likely done (some rounds might be incomplete)
    if [ $match_count -ge 360 ]; then
        echo ""
        echo "✓ Reached 360+ matches, proceeding with consolidation"
        break
    fi

    sleep 30
done

echo ""
echo "========================================================================"
echo "Step 2: Consolidate data"
echo "========================================================================"
cd "$BASE_DIR"
python consolidate_serie_b_2025_complete.py

echo ""
echo "========================================================================"
echo "Step 3: Transform to curated format"
echo "========================================================================"
python -m src.main transform --season 2025

echo ""
echo "========================================================================"
echo "Step 4: Validation"
echo "========================================================================"
python -m src.main validate --season 2025

echo ""
echo "========================================================================"
echo "✓ COMPLETE: Série B 2025 extraction finished"
echo "========================================================================"
echo ""
echo "Data files ready:"
echo "  - data/curated/serie_b_2025/matches.csv"
echo "  - data/processed/2025/matches/match_ids.csv"
echo ""
echo "Next: Use for model training!"
