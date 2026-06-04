---
name: 2025 Season Data Extraction (May 7 Ongoing)
description: Histórical 2025 Série B extraction — sync-matches R1-R38 + sync-player-stats in progress
type: project
---

## Session Overview

**Start time:** 2026-05-07 13:10:42
**Current status:** sync-player-stats 2025 in progress
**Commands executed:**
1. `python -m src.main sync-matches --season 2025 --from-round 1 --to-round 38` — completed 13:10→14:23 (75 min)
2. `python -m src.main sync-player-stats --season 2025` — started 13:10:42, ongoing

## Progress Tracking

### sync-player-stats 2025

| Metric | Value |
|---|---|
| Matches processed | 595 matches |
| Player records extracted | 26,680+ rows |
| Start time | 13:10:42 |
| Last update | 16:24:17 |
| Elapsed time | 3h 13m 35s |
| Extraction rate | ~3.1 matches/min |
| Avg rows/match | 44.8 |

**Expected total:** 380 Série B matches (20 teams × 19 rounds for 2025 season). Current 595 suggests parallel processing of multiple datasets or prior historical run overlap in logs.

## Next Steps

1. Monitor for sync-player-stats completion
2. Verify `data/processed/2025/events/player_match_stats_2025.csv` populated
3. Run `python -m src.main transform --season 2025`
4. Verify `data/curated/serie_b_2025/player_match_stats.csv` with row count
5. Final summary: total matches, player records, file paths
