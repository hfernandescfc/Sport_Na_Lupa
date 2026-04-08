"""Build the expected-points table for Série B from curated xG data.

Algorithm
---------
For each completed match that has xG for both teams:
  1. Model goals as independent Poisson variables with λ = xG.
  2. Sum P(home_goals=i, away_goals=j) over all (i, j) pairs until the
     remaining probability mass is negligible (< 1e-10 per side).
  3. xPts_home = 3·P(home wins) + 1·P(draw)
     xPts_away = 3·P(away wins) + 1·P(draw)

Aggregate per team and compare against actual points.

Opponent strength (optional)
----------------------------
If  data/processed/{season}/matches/serie_b_{season}_team_strength.csv  exists,
the table is enriched with:
  - sos        : average strength_score of opponents faced  (0-1 scale)
  - sos_xpts   : xPts weighted by opponents' strength (higher = harder schedule)

Strength score mirrors generate_temporada_cards.py:
    strength_score = 0.60 × mv_score + 0.40 × perf_score   (when MV available)
    strength_score = perf_score                              (fallback)

Output
------
  data/curated/serie_b_2026/expected_points_table.csv
"""
from __future__ import annotations

import datetime
import math

import pandas as pd

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger


logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Poisson helpers
# ---------------------------------------------------------------------------

def _poisson_pmf(k: int, lam: float) -> float:
    """P(X = k) for X ~ Poisson(lam). Numerically stable via log-space."""
    if lam <= 0.0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))


def _max_k(lam: float, tol: float = 1e-10) -> int:
    """Smallest k such that P(X > k) < tol for X ~ Poisson(lam)."""
    if lam <= 0.0:
        return 0
    k, cdf = 0, 0.0
    while True:
        cdf += _poisson_pmf(k, lam)
        if 1.0 - cdf < tol:
            return k
        k += 1


def _match_probabilities(xg_home: float, xg_away: float) -> tuple[float, float, float]:
    """Return (p_home_win, p_draw, p_away_win) for a single match."""
    n_home = _max_k(xg_home)
    n_away = _max_k(xg_away)

    home_pmf = [_poisson_pmf(i, xg_home) for i in range(n_home + 1)]
    away_pmf = [_poisson_pmf(j, xg_away) for j in range(n_away + 1)]

    p_home_win = p_draw = p_away_win = 0.0
    for i, ph in enumerate(home_pmf):
        for j, pa in enumerate(away_pmf):
            p = ph * pa
            if i > j:
                p_home_win += p
            elif i == j:
                p_draw += p
            else:
                p_away_win += p

    return p_home_win, p_draw, p_away_win


# ---------------------------------------------------------------------------
# Opponent strength
# ---------------------------------------------------------------------------

def _load_strength_scores(settings: Settings, season: int) -> dict[str, float] | None:
    """Return {team_key: strength_score} or None if the strength file is absent."""
    path = settings.processed_dir / str(season) / "matches" / f"serie_b_{season}_team_strength.csv"
    if not path.exists():
        logger.info("Team strength file not found (%s) — SOS columns will be omitted", path)
        return None

    df = pd.read_csv(path)

    # Corrige divergências entre chaves do MANUAL_TEAM_MAPPINGS e o
    # resultado de normalize_team_name nos dados curados
    KEY_ALIASES = {
        "america-mg":  "america-mineiro",
        "vila-nova":   "vila-nova-fc",
    }
    df["team_key"] = df["team_key"].replace(KEY_ALIASES)

    df["squad_market_value_eur"] = pd.to_numeric(df["squad_market_value_eur"], errors="coerce")
    df["perf_points_per_game"] = pd.to_numeric(df["perf_points_per_game"], errors="coerce")

    # Normalise market value to [0, 1]
    mv = df["squad_market_value_eur"]
    mv_min, mv_max = mv.min(), mv.max()
    if mv_max > mv_min:
        df["mv_score"] = (mv - mv_min) / (mv_max - mv_min)
    else:
        df["mv_score"] = None

    # Normalise PPG to [0, 1]
    ppg = df["perf_points_per_game"].fillna(0.0)
    ppg_max = ppg.max()
    df["perf_score"] = ppg / ppg_max if ppg_max > 0 else 0.0

    # Combined strength score — same formula as generate_temporada_cards.py
    def _strength(row: pd.Series) -> float:
        if pd.notna(row["mv_score"]):
            return 0.60 * row["mv_score"] + 0.40 * row["perf_score"]
        return float(row["perf_score"])

    df["strength_score"] = df.apply(_strength, axis=1)

    return dict(zip(df["team_key"], df["strength_score"]))


# ---------------------------------------------------------------------------
# Main transform
# ---------------------------------------------------------------------------

def transform_standings(settings: Settings, season: int) -> None:
    curated = settings.curated_dir / "serie_b_2026"

    matches_path = curated / "matches.csv"
    stats_path = curated / "team_match_stats.csv"

    if not matches_path.exists() or not stats_path.exists():
        logger.warning("Required curated files missing — run `transform` first")
        return

    matches_df = pd.read_csv(matches_path, dtype=str)
    stats_df = pd.read_csv(stats_path, dtype=str)

    # Keep only completed matches
    matches_df = matches_df[matches_df["status"] == "completed"].copy()
    matches_df["home_score"] = pd.to_numeric(matches_df["home_score"], errors="coerce")
    matches_df["away_score"] = pd.to_numeric(matches_df["away_score"], errors="coerce")
    matches_df = matches_df.dropna(subset=["home_score", "away_score"])

    # Pivot stats to one row per match: xg_home, xg_away
    stats_df["expected_goals"] = pd.to_numeric(stats_df["expected_goals"], errors="coerce")
    stats_df["is_home"] = stats_df["is_home"].map(
        {"True": True, "False": False, True: True, False: False}
    )

    home_xg = (
        stats_df[stats_df["is_home"] == True][["match_code", "expected_goals"]]
        .rename(columns={"expected_goals": "xg_home"})
    )
    away_xg = (
        stats_df[stats_df["is_home"] == False][["match_code", "expected_goals"]]
        .rename(columns={"expected_goals": "xg_away"})
    )

    match_xg = home_xg.merge(away_xg, on="match_code", how="inner").dropna(
        subset=["xg_home", "xg_away"]
    )

    merged = matches_df.merge(match_xg, on="match_code", how="inner")

    if merged.empty:
        logger.warning("No completed matches with xG data found — table not generated")
        return

    # Compute per-match probabilities and expected points
    probs = merged.apply(
        lambda r: pd.Series(
            _match_probabilities(r["xg_home"], r["xg_away"]),
            index=["p_home_win", "p_draw", "p_away_win"],
        ),
        axis=1,
    )
    merged = pd.concat([merged, probs], axis=1)
    merged["xpts_home"] = 3.0 * merged["p_home_win"] + merged["p_draw"]
    merged["xpts_away"] = 3.0 * merged["p_away_win"] + merged["p_draw"]

    merged["home_outcome"] = merged.apply(
        lambda r: "W" if r["home_score"] > r["away_score"]
        else ("D" if r["home_score"] == r["away_score"] else "L"),
        axis=1,
    )
    merged["away_outcome"] = merged["home_outcome"].map({"W": "L", "D": "D", "L": "W"})
    merged["pts_home"] = merged["home_outcome"].map({"W": 3, "D": 1, "L": 0})
    merged["pts_away"] = merged["away_outcome"].map({"W": 3, "D": 1, "L": 0})

    # Build per-team rows
    home_rows = merged[[
        "home_team", "home_team_key", "away_team_key",
        "home_score", "away_score",
        "home_outcome", "pts_home",
        "xpts_home", "p_home_win", "p_draw", "p_away_win",
    ]].rename(columns={
        "home_team": "team_name",
        "home_team_key": "team_key",
        "away_team_key": "opp_key",
        "home_score": "gf",
        "away_score": "ga",
        "home_outcome": "outcome",
        "pts_home": "pts",
        "xpts_home": "xpts",
        "p_home_win": "xw",
        "p_away_win": "xl",
    })

    away_rows = merged[[
        "away_team", "away_team_key", "home_team_key",
        "away_score", "home_score",
        "away_outcome", "pts_away",
        "xpts_away", "p_away_win", "p_draw", "p_home_win",
    ]].rename(columns={
        "away_team": "team_name",
        "away_team_key": "team_key",
        "home_team_key": "opp_key",
        "away_score": "gf",
        "home_score": "ga",
        "away_outcome": "outcome",
        "pts_away": "pts",
        "xpts_away": "xpts",
        "p_away_win": "xw",
        "p_home_win": "xl",
    })

    all_rows = pd.concat([home_rows, away_rows], ignore_index=True)

    # Aggregate per team
    table = (
        all_rows.groupby(["team_name", "team_key"], as_index=False)
        .agg(
            MP=("pts", "count"),
            xPts=("xpts", "sum"),
            xW=("xw", "sum"),
            xD=("p_draw", "sum"),
            xL=("xl", "sum"),
            Pts=("pts", "sum"),
            W=("outcome", lambda s: (s == "W").sum()),
            D=("outcome", lambda s: (s == "D").sum()),
            L=("outcome", lambda s: (s == "L").sum()),
            GF=("gf", "sum"),
            GA=("ga", "sum"),
        )
    )

    table["GD"] = table["GF"] - table["GA"]
    table["xPts"] = table["xPts"].round(2)
    table["xW"] = table["xW"].round(2)
    table["xD"] = table["xD"].round(2)
    table["xL"] = table["xL"].round(2)
    table["pts_diff"] = (table["Pts"] - table["xPts"]).round(2)

    # ── Opponent strength (optional) ──────────────────────────────────────────
    strength_scores = _load_strength_scores(settings, season)
    if strength_scores:
        table = _enrich_with_sos(table, all_rows, strength_scores)

    table = table.sort_values(
        ["xPts", "Pts", "GD", "GF"], ascending=False
    ).reset_index(drop=True)
    table.insert(0, "rank_xpts", range(1, len(table) + 1))
    table["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    base_cols = [
        "rank_xpts", "team_name", "team_key", "MP",
        "xPts", "xW", "xD", "xL",
        "Pts", "W", "D", "L",
        "GF", "GA", "GD", "pts_diff",
    ]
    strength_cols = ["sos", "sos_rank"] if "sos" in table.columns else []
    table = table[base_cols + strength_cols + ["generated_at"]]

    out_path = curated / "expected_points_table.csv"
    write_csv(out_path, table.to_dict("records"))
    logger.info(
        "Expected points table: %s teams, %s matches%s -> %s",
        len(table),
        len(merged),
        " (with SOS)" if strength_cols else "",
        out_path,
    )


# ---------------------------------------------------------------------------
# SOS enrichment
# ---------------------------------------------------------------------------

def _enrich_with_sos(
    table: pd.DataFrame,
    all_rows: pd.DataFrame,
    strength_scores: dict[str, float],
) -> pd.DataFrame:
    """Add sos (avg opponent strength) and sos_rank columns to the table."""
    # Average opponent strength per team
    all_rows = all_rows.copy()
    all_rows["opp_strength"] = all_rows["opp_key"].map(strength_scores)

    missing = all_rows["opp_strength"].isna().sum()
    if missing:
        logger.warning(
            "%s opponent-match rows have no strength score — SOS will be partial", missing
        )

    sos_df = (
        all_rows.dropna(subset=["opp_strength"])
        .groupby("team_key", as_index=False)["opp_strength"]
        .mean()
        .rename(columns={"opp_strength": "sos"})
    )
    sos_df["sos"] = sos_df["sos"].round(3)

    table = table.merge(sos_df, on="team_key", how="left")

    # Rank: 1 = toughest schedule
    table["sos_rank"] = table["sos"].rank(ascending=False, method="min").astype("Int64")

    return table
