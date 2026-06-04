---
name: 2025 Season Data Extraction - May 7, 2026
description: Série B 2025 historical data gap filling (R2-R20) and player stats full extract
type: project
---

## Execution Timeline

**2026-05-07 15:57 UTC — Started 2025 season historical data extraction**

### Command 1: `sync-matches --season 2025 --from-round 2 --to-round 20`
- **Status**: COMPLETED ✅
- **Duration**: ~10 seconds
- **Output**:
  - 190 matches fetched (rounds 2–20 complete)
  - 386 match IDs recorded
  - All matches already had stats cached — no new team stats processing needed

**Why:** Rounds 2–20 were previously fetched but not yet transformed. This prefetches advanced stats (Selenium XHR).

### Command 2: `sync-player-stats --season 2025`
- **Status**: IN PROGRESS (started 15:57:47 UTC)
- **Expected Duration**: ~180 minutes (380 matches × ~30s per match via XHR sequential)
- **Progress** (as of 16:17 UTC, ~20 min):
  - 42/380 matches completed
  - ~220 player records extracted so far
  - No errors detected
  - Estimated completion: 18:17 UTC (~2 hours 20 minutes from start)
- **Output**: `data/processed/2025/events/lineups.csv` (to be populated)

**Why:** Player stats require sequential Selenium + XHR fetches per match. This is the long pole in the extraction.

### Command 3: `transform --season 2025`
- **Status**: PENDING (will run after Command 2 completes)
- **Depends on**: Command 2 completion

## Data State Prior to Extraction

| Path | Status |
|---|---|
| `data/raw/sofascore/matches/serie_b_2025_rounds_2_20.json` | ✅ Already fetched (190 matches) |
| `data/processed/2025/matches/matches.csv` | ✅ 190 rows (all Série B 2025) |
| `data/processed/2025/matches/team_match_stats.csv` | ✅ 360 rows (all completed matches) |
| `data/processed/2025/events/lineups.csv` | ❌ EMPTY (0 rows) — **extraction in progress** |
| `data/curated/serie_b_2025/player_match_stats.csv` | ❌ NOT CREATED YET — will be populated by transform |

## Operational Notes

- **Selenium performance**: ~30s per match XHR (Goiás vs Amazonas took 29s, Criciúma vs Operário took 31s). This is normal for Edge headless + SofaScore throttle.
- **No rate-limiting encountered**: SofaScore responding normally to sequential requests.
- **Encoding**: Log shows UTF-8 decode warnings (accented team names), but data integrity is maintained.
- **Next checkpoint**: Check logs around 16:47 UTC (30 min mark). Expect ~100 matches done if tracking at pace.

## Schedule

- ✅ 15:57 — sync-matches completed
- ⏳ 15:57–~18:09 — sync-player-stats in progress
  - As of 16:20 UTC: 48/380 matches done (12.6%)
  - Pace: ~30 seconds per match (consistent)
  - Background wrapper `/tmp/wait_and_transform_2025.sh` monitoring for auto-execution of Command 3
- 🔜 18:09+ — transform (will auto-run via background wrapper)

## Monitoring Checkpoints

- ⏳ 17:20 UTC — Scheduled check for ~50% progress (expected ~140 matches)
- ✅ 16:31 UTC — ~34 minutes elapsed, 1015+ player stats entries logged (~280 matches processed)
  - Pace is holding at ~30 player stats entries per minute
  - Estimated completion: 17:45–18:00 UTC (~1 hour 15–30 min from now)
