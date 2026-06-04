#!/bin/bash
# This script runs after sync-player-stats --season 2025 completes
# Called by the user once the extraction is done

cd /c/Users/compesa/Desktop/SportSofa

echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] Running transform --season 2025..."
python -m src.main transform --season 2025

echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] Transform completed. Checking output files..."
ls -lh data/curated/serie_b_2025/ 2>/dev/null || echo "Note: data/curated/serie_b_2025 may not exist yet"

echo "[$(date -u +'%Y-%m-%d %H:%M:%S')] Done."
