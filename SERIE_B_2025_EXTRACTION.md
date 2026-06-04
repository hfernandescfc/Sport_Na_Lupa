# Série B 2025 Historical Data Extraction

## Status

- **Season ID**: 72603 ✅
- **Tournament ID**: 390 (same for all years)
- **Rounds**: 38 (complete historical season)
- **Resolved**: 2026-05-07

## Extraction Pipeline In Progress

### Phase 1: Raw Data Extraction (3 parallel jobs)

| Job | Command | Status | Expected Output |
|---|---|---|---|
| Matches | `sync-matches --season 2025 --from-round 1 --to-round 38` | 🔄 Running | `data/processed/2025/matches/serie_b_2025_matches.json` (380 matches) |
| Player Stats | `sync-player-stats --season 2025` | 🔄 Running | `data/processed/2025/players/player_match_stats_2025.json` |
| Incidents | `sync-incidents --season 2025` | 🔄 Running | `data/processed/2025/incidents/serie_b_incidents.json` + `sport_incidents.json` |

### Phase 2: Data Transformation (after Phase 1)

Once raw data is extracted:

```bash
# Normalize and curate data
python -m src.main transform --season 2025

# Generate standings with xPts and SOS
python -m src.main transform-standings --season 2025
```

**Expected Output:**
- `data/curated/serie_b_2025/matches.csv` (380 rows)
- `data/curated/serie_b_2025/team_match_stats.csv` (760 rows — both teams per match)
- `data/curated/serie_b_2025/player_match_stats.csv` (~15k rows)
- `data/curated/serie_b_2025/expected_points_table.csv` (20 teams with xPts, SOS, xW/D/L)
- `data/curated/serie_b_2025/goal_sequences.csv`
- `data/curated/serie_b_2025/match_incidents.csv`

### Phase 3: Validation & Quality Checks

```bash
python -m src.main validate --season 2025
```

**Output**: `data/curated/serie_b_2025/validation_report.json`

## Data Structure

### Raw Data Location
```
data/processed/2025/
  matches/
    serie_b_2025_matches.json       ← all 380 matches with XHR advanced_stats
  players/
    player_match_stats_2025.json    ← scouts for all players across all matches
  incidents/
    serie_b_incidents.json          ← goals, cards, subs, substitutions
    sport_incidents.json            ← Sport player stats if applicable
```

### Curated Data Location
```
data/curated/serie_b_2025/
  matches.csv                   ← normalized match data
  team_match_stats.csv          ← team statistics per match
  player_match_stats.csv        ← player-by-player stats
  expected_points_table.csv     ← final standings with xPts and SOS
  goal_sequences.csv            ← goal-by-goal timeline
  match_incidents.csv           ← detailed incident log
  validation_report.json        ← quality checks
```

## Usage for Predictive Models

### Example: Historical Baseline Comparison

```python
import pandas as pd

# Load 2025 data (complete season)
df_2025 = pd.read_csv('data/curated/serie_b_2025/expected_points_table.csv')

# Load 2026 data (in progress)
df_2026 = pd.read_csv('data/curated/serie_b_2026/expected_points_table.csv')

# Compare: which teams are performing better/worse in 2026?
print(df_2025.head())
print(df_2026.head())
```

### Example: Model Training Dataset

```python
import pandas as pd

# Combine historical match data
matches_2025 = pd.read_csv('data/curated/serie_b_2025/matches.csv')
team_stats_2025 = pd.read_csv('data/curated/serie_b_2025/team_match_stats.csv')

# Create training dataset: (home_team_stats, away_team_stats) -> outcome
# This allows model to learn historical patterns
```

### Example: xPts & Luck Analysis

```python
# Load expected points table with SOS
df_2025 = pd.read_csv('data/curated/serie_b_2025/expected_points_table.csv')

# Columns available:
# - xpts (expected points from Poisson model)
# - pts (actual points)
# - pts_diff (luck factor: pts - xpts)
# - sos (strength of schedule score)
# - sos_rank (1-20, 1=easiest)

# Analyze: teams that overperformed vs underperformed luck
df_2025['luck'] = df_2025['pts_diff']
print(df_2025[['team_key', 'pts', 'xpts', 'luck']].sort_values('luck', ascending=False))
```

## Key Metrics Available

### Team-Level (per match)
- Goals, xG, shots, shots on target
- Passes, pass accuracy, tackles, fouls
- Corners, yellow/red cards
- Possession (if available)

### Player-Level (per match)
- Minutes played, rating
- Passes (total, accurate, long balls)
- Shots, expected assists, expected goals
- Touches, ball recovery, possession lost
- Defensive actions, dribbles

### Season-Level (final standings)
- Expected Points (xPts) via Poisson distribution
- Strength of Schedule (SOS) — average opponent strength
- Expected W/D/L distribution
- Goal differential (actual vs expected)

## Notes

1. **2025 is complete** — all 38 rounds finished, no ongoing matches
2. **Time series analysis** — suitable for trend analysis and baseline comparison
3. **Player transfers** — some 2025 players may have moved to other clubs by 2026
4. **Methodology consistency** — same extraction methods as 2026 ensure consistency

## Timeline

- **Phase 1 (Extraction)**: ~30-60 min (parallel jobs)
- **Phase 2 (Transform)**: ~5-10 min
- **Phase 3 (Validate)**: ~1 min
- **Total ETA**: ~1 hour from now

---

*Generated: 2026-05-07*
*Season ID Resolved: 72603*
