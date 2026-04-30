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

Opponent strength
-----------------
The table is always enriched with a SOS column derived from each team's live
Série B PPG (Pts / MP from this very table), optionally combined with squad
market value from data/processed/{season}/matches/serie_b_{season}_team_strength.csv.

  strength_score = 0.60 × mv_score + 0.40 × perf_score   (when MV available)
  strength_score = perf_score                              (fallback)

  mv_score   = (mv - min) / (max - min)             [frozen until sync-serie-b-strength re-runs]
  perf_score = (Pts/MP) / max(Pts/MP)               [live — recomputed every transform-standings]

This keeps the time-sensitive part of SOS in sync with the current round even
if MV has not been refreshed, while preserving market value as a stable
top-of-table signal between transfer windows.

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

_STRENGTH_KEY_ALIASES = {
    "america-mg":  "america-mineiro",
    "vila-nova":   "vila-nova-fc",
}


def _load_market_values(settings: Settings, season: int) -> dict[str, float]:
    """Return {team_key: mv_score in [0,1]}. Empty dict if file missing/incomplete.

    MV evolves slowly (transfer windows) and is sourced from
    sync-serie-b-strength. The performance component is computed live in
    `_compute_strength_scores` from the curated standings table — so a stale
    MV CSV degrades to a frozen 60% weight, but the live 40% always reflects
    the latest round.
    """
    path = (
        settings.processed_dir / str(season) / "matches"
        / f"serie_b_{season}_team_strength.csv"
    )
    if not path.exists():
        logger.info("Team strength file not found (%s) — MV component disabled", path)
        return {}

    df = pd.read_csv(path)
    df["team_key"] = df["team_key"].replace(_STRENGTH_KEY_ALIASES)
    df["squad_market_value_eur"] = pd.to_numeric(
        df["squad_market_value_eur"], errors="coerce"
    )
    df = df.dropna(subset=["squad_market_value_eur"])

    if len(df) < 20:
        logger.warning(
            "Strength CSV covers %d/20 Série B teams — MV missing for the rest. "
            "Run `sync-serie-b-strength` (or `update-round --refresh-strength`) to refresh.",
            len(df),
        )

    mv = df["squad_market_value_eur"]
    mv_min, mv_max = mv.min(), mv.max()
    if mv_max <= mv_min:
        return {}
    df["mv_score"] = (mv - mv_min) / (mv_max - mv_min)
    return dict(zip(df["team_key"], df["mv_score"]))


def _compute_strength_scores(
    table: pd.DataFrame, mv_scores: dict[str, float]
) -> dict[str, float]:
    """Combine frozen MV (60%) with live PPG from the curated Série B table (40%).

    Live PPG ensures SOS reflects each opponent's latest form even if
    sync-serie-b-strength has not been re-run. Falls back to PPG-only when
    MV is unavailable for a team (graceful degradation; matches the previous
    behaviour for partial coverage)."""
    if table.empty or "Pts" not in table.columns or "MP" not in table.columns:
        return {}

    ppg = (table["Pts"] / table["MP"]).where(table["MP"] > 0, 0.0)
    ppg_max = ppg.max()
    if ppg_max <= 0:
        return {}
    perf_scores = dict(zip(table["team_key"], ppg / ppg_max))

    strength: dict[str, float] = {}
    for team_key, perf in perf_scores.items():
        mv = mv_scores.get(team_key)
        if mv is not None:
            strength[team_key] = 0.60 * mv + 0.40 * float(perf)
        else:
            strength[team_key] = float(perf)
    return strength


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

    # ── Opponent strength ─────────────────────────────────────────────────────
    # MV from CSV (frozen, slow-changing); PPG from this very table (live).
    mv_scores = _load_market_values(settings, season)
    strength_scores = _compute_strength_scores(table, mv_scores)
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
