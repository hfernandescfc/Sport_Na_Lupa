# Série B 2025 — Extraction Recovery In Progress

**Status**: 🔄 RECOVERING & MERGING DATA

## What Happened

1. ✅ Extracted rodadas 1-20: **190 matches**
2. ✅ Extracted rodadas 20-38: **190 matches** 
3. ⚠️ File was overwritten (lost rodadas 1-19)
4. 🔄 **Now recovering**: Re-extracting rodadas 1-20

## Current Jobs

| Job | Task | Status | Progress |
|---|---|---|---|
| `bfmp2u2es` | Extract R1-20 | 🔄 Running | ~10-15 min elapsed |
| `bj31sud6k` | Merge + Transform | ⏳ Queued (waiting for R1-20) | Pending |

## Expected Final Dataset

- **Rounds**: 1-38 (complete)
- **Matches**: ~380 (some may be incomplete/pending)
- **Teams**: 20 (all teams in Série B)

## Timeline

| Phase | Duration | Status |
|---|---|---|
| Extract R1-20 | ~30 min | 🔄 Running (10+ min done) |
| Merge R1-20 + R20-38 | ~1 min | ⏳ Queued |
| Transform | ~2 min | ⏳ Queued |
| Validate | ~1 min | ⏳ Queued |
| **TOTAL** | **~35 min** | **In progress** |

## Files Being Created

- `data/processed/2025/matches/matches.csv` — Updating with R1-20
- `data/processed/2025/matches/match_ids.csv` — To be created
- `data/curated/serie_b_2025/matches.csv` — Final curated (after transform)

## What To Do While Waiting

1. **Monitor extraction**:
   ```bash
   tail -f logs/extraction_r1_20.log
   ```

2. **Check current progress**:
   ```bash
   wc -l data/processed/2025/matches/matches.csv
   ```

3. **Next steps ready**: Once complete, you can immediately start model training!

---

**You will receive a notification when complete** 🔔
