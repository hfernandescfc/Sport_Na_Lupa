# Série B 2025 — Live Status Dashboard

**Last Updated**: 2026-05-07 13:20 UTC  
**Status**: 🔄 **EXTRACTION IN PROGRESS** (Rounds 21-38)

## Current Progress

| Metric | Value | Target | % |
|---|---|---|---|
| **Matches Extracted** | 190 | 380 | 50% |
| **Rounds Extracted** | 1-20 | 1-38 | 52% |
| **Extraction Time** | ~20 min | ~60 min | 33% |

## Background Jobs

| Job ID | Task | Status | Started | Duration |
|---|---|---|---|---|
| `by3gqmmty` | sync-matches R21-38 | 🔄 Running | 13:10 | 10 min |
| `br3ehnzs2` | monitor + auto-complete | 🔄 Running | 13:18 | 2 min |

## Workflow

1. ✅ **Rounds 1-20**: Extracted (190 matches)
2. 🔄 **Rounds 21-38**: Extracting via `sync-matches --season 2025 --from-round 21 --to-round 38`
3. ⏳ **Consolidate**: Auto-run once extraction stable (remove duplicates)
4. ⏳ **Transform**: Auto-run (normalize to curated format)
5. ⏳ **Validate**: Auto-run (quality checks)

## What's Happening Right Now

The monitor script (`monitor_and_complete_2025.py`) is:
- Polling the matches.csv file every 30 seconds
- Counting current matches and rounds
- **Waiting for extraction to reach 360+ matches or stabilize**
- Once complete, it will automatically:
  1. Run `consolidate_serie_b_2025_complete.py`
  2. Run `python -m src.main transform --season 2025`
  3. Run `python -m src.main validate --season 2025`

## Expected Timeline

| Phase | Duration | ETA |
|---|---|---|
| Rounds 21-38 extraction | 30-40 min | ~13:50 |
| Consolidation | 1 min | ~13:51 |
| Transform | 2 min | ~13:53 |
| Validate | 1 min | ~13:54 |
| **TOTAL** | **~1 hour** | **~14:00** |

## Files to Monitor

- `data/processed/2025/matches/matches.csv` — Raw extracted data (growing)
- `logs/monitor_2025.log` — Live output from monitor script
- `data/curated/serie_b_2025/matches.csv` — Final curated data (created after transform)

## What to Do While Waiting

1. **Monitor progress** (real-time):
   ```bash
   watch -n 30 'wc -l data/processed/2025/matches/matches.csv'
   ```

2. **Check monitor output**:
   ```bash
   tail -f logs/monitor_2025.log
   ```

3. **Check extraction job**:
   ```bash
   # In background task manager (if available)
   jobs
   ```

4. **Prepare for next steps** (in parallel):
   - Review model features you want to extract
   - Prepare training/test split strategy
   - Set up your ML pipeline

## FAQ

**Q: Why started with rounds 21-38 but still showing 190 matches?**  
A: Selenium extraction takes time (~5-10 min per round). If extraction just started (10 min ago), hasn't reached round 21 yet.

**Q: What if extraction fails mid-way?**  
A: Monitor will detect stable state (no changes for 1.5 min) and proceed with consolidation. 190 matches is still 50% coverage!

**Q: Can I manually check progress?**  
A: Yes! Run: `wc -l data/processed/2025/matches/matches.csv`

**Q: What if monitor times out after 60 min?**  
A: Monitor will consolidate whatever matches were extracted. You can then manually re-run extraction for remaining rounds.

## Troubleshooting

| Issue | Solution |
|---|---|
| Monitor seems stuck | Check `tail logs/monitor_2025.log` for errors |
| Extraction not starting | Verify `by3gqmmty` job status — may need manual restart |
| Need immediate results | Use current 190 matches for model baseline |

## Next Steps (After Completion)

Once this workflow completes:

```bash
# 1. Load complete dataset
python << 'EOF'
import pandas as pd
df = pd.read_csv('data/curated/serie_b_2025/matches.csv')
print(f"Loaded {len(df)} matches from {len(df['round'].unique())} rounds")
print(f"Teams: {len(set(df['home_team'].unique()) | set(df['away_team'].unique()))}")
EOF

# 2. Start model development
jupyter notebook
# Use examples from SERIE_B_2025_FINAL_REPORT.md
```

---

**Auto-refresh this page in 30 seconds to see latest status** ↻

*Monitor script will send notification when complete*
