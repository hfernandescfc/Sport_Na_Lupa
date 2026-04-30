"""
Composite Power Ranking para a Série B 2026.

Componentes (pesos fixos):
  1. xPts/MP          (35%) — baseline de performance esperada via Poisson
  2. Net xG/MP        (30%) — dominância: xG produzido − xGA por partida
  3. SOS-adj xPts     (25%) — xPts/MP × (1 + sos_rolling) — premia calendário difícil
  4. Recent form      (10%) — Pts/MP nas últimas K partidas

SOS Rolling: média do perf_score dos últimos K adversários (PPG normalizado).
Força do adversário = Pts/MP / max(Pts/MP) ao vivo na própria tabela.

Output: data/curated/serie_b_2026/power_ranking.csv
"""
from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

WEIGHTS = {
    "xpts_mp":   0.30,
    "net_xg_mp": 0.25,
    "sos_adj":   0.30,
    "form":      0.15,
}


def _norm(s: pd.Series) -> pd.Series:
    """Min-max normalisation → [0, 1]. Returns 0.5 for constant series."""
    lo, hi = s.min(), s.max()
    if hi <= lo:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def _build_all_rows(
    matches: pd.DataFrame,
    stats: pd.DataFrame,
) -> pd.DataFrame:
    """One row per (team, match) with round, outcome, xG produced/conceded."""
    completed = matches[matches["status"] == "completed"].copy()
    completed["round"] = completed["round"].astype(int)
    completed["home_score"] = pd.to_numeric(completed["home_score"], errors="coerce")
    completed["away_score"] = pd.to_numeric(completed["away_score"], errors="coerce")
    completed = completed.dropna(subset=["home_score", "away_score"])

    stats["expected_goals"] = pd.to_numeric(stats["expected_goals"], errors="coerce")
    stats["is_home"] = stats["is_home"].map(
        {"True": True, "False": False, True: True, False: False}
    )

    home_xg = (
        stats[stats["is_home"] == True][["match_code", "expected_goals"]]
        .rename(columns={"expected_goals": "xg_home"})
    )
    away_xg = (
        stats[stats["is_home"] == False][["match_code", "expected_goals"]]
        .rename(columns={"expected_goals": "xg_away"})
    )
    xg_per_match = home_xg.merge(away_xg, on="match_code", how="inner")
    merged = completed.merge(xg_per_match, on="match_code", how="inner").dropna(
        subset=["xg_home", "xg_away"]
    )

    def _outcome(gf, ga):
        return "W" if gf > ga else ("D" if gf == ga else "L")

    def _pts(outcome):
        return {"W": 3, "D": 1, "L": 0}[outcome]

    home_rows = merged.assign(
        team_key=merged["home_team_key"],
        team_name=merged["home_team"],
        opp_key=merged["away_team_key"],
        xg_prod=merged["xg_home"],
        xg_conc=merged["xg_away"],
        outcome=merged.apply(
            lambda r: _outcome(r["home_score"], r["away_score"]), axis=1
        ),
    )[["team_key", "team_name", "opp_key", "round", "match_code",
       "xg_prod", "xg_conc", "outcome"]]

    away_rows = merged.assign(
        team_key=merged["away_team_key"],
        team_name=merged["away_team"],
        opp_key=merged["home_team_key"],
        xg_prod=merged["xg_away"],
        xg_conc=merged["xg_home"],
        outcome=merged.apply(
            lambda r: _outcome(r["away_score"], r["home_score"]), axis=1
        ),
    )[["team_key", "team_name", "opp_key", "round", "match_code",
       "xg_prod", "xg_conc", "outcome"]]

    all_rows = pd.concat([home_rows, away_rows], ignore_index=True)
    all_rows["pts"] = all_rows["outcome"].map({"W": 3, "D": 1, "L": 0})
    return all_rows


def _compute_sos_rolling(
    all_rows: pd.DataFrame,
    perf_scores: dict[str, float],
    window: int,
) -> dict[str, float]:
    """Rolling SOS: avg perf_score of last `window` opponents per team."""
    sos: dict[str, float] = {}
    for team_key, grp in all_rows.groupby("team_key"):
        # Sort by round (ascending), take last `window`
        recent = grp.sort_values("round").tail(window)
        strengths = [perf_scores.get(k, 0.0) for k in recent["opp_key"]]
        sos[team_key] = sum(strengths) / len(strengths) if strengths else 0.0
    return sos


def transform_power_ranking(
    settings: Settings,
    season: int,
    sos_window: int = 4,
) -> None:
    """Build power_ranking.csv in data/curated/serie_b_2026/."""
    curated = settings.curated_dir / f"serie_b_{season}"

    xpts_path   = curated / "expected_points_table.csv"
    matches_path = curated / "matches.csv"
    stats_path   = curated / "team_match_stats.csv"

    for p in (xpts_path, matches_path, stats_path):
        if not p.exists():
            logger.warning("Required file missing: %s — run transform + transform-standings first", p)
            return

    xpts_df  = pd.read_csv(xpts_path)
    matches  = pd.read_csv(matches_path, dtype=str)
    stats    = pd.read_csv(stats_path, dtype=str)

    # ── Live perf_score: PPG normalised from the xPts table ──────────────────
    xpts_df["MP"] = pd.to_numeric(xpts_df["MP"], errors="coerce")
    xpts_df["Pts"] = pd.to_numeric(xpts_df["Pts"], errors="coerce")
    ppg = (xpts_df["Pts"] / xpts_df["MP"]).where(xpts_df["MP"] > 0, 0.0)
    ppg_max = ppg.max()
    perf_scores: dict[str, float] = dict(
        zip(xpts_df["team_key"], ppg / ppg_max if ppg_max > 0 else ppg)
    )

    # ── Build match-level rows ────────────────────────────────────────────────
    all_rows = _build_all_rows(matches, stats)
    if all_rows.empty:
        logger.warning("No completed matches with xG data — power ranking not generated")
        return

    # ── Component 1: xPts/MP ─────────────────────────────────────────────────
    xpts_df["xPts"] = pd.to_numeric(xpts_df["xPts"], errors="coerce")
    c1 = dict(zip(xpts_df["team_key"], xpts_df["xPts"] / xpts_df["MP"]))

    # ── Component 2: Net xG/MP ────────────────────────────────────────────────
    net_xg = (
        all_rows.groupby("team_key")
        .agg(xg_prod=("xg_prod", "sum"), xg_conc=("xg_conc", "sum"), mp=("pts", "count"))
        .assign(net_xg_mp=lambda d: (d["xg_prod"] - d["xg_conc"]) / d["mp"])
        .reset_index()
    )
    c2 = dict(zip(net_xg["team_key"], net_xg["net_xg_mp"]))

    # ── Component 3: SOS-rolling-adjusted xPts ───────────────────────────────
    sos_rolling = _compute_sos_rolling(all_rows, perf_scores, window=sos_window)
    # SOS in [0,1] → multiply: xPts/MP × (1 + sos_rolling)
    c3 = {tk: c1.get(tk, 0.0) * (1.0 + sos_rolling.get(tk, 0.0)) for tk in perf_scores}

    # ── Component 4: Recent form — Pts/MP in last `sos_window` rounds ────────
    max_round = all_rows["round"].max()
    recent_rounds = range(max(1, max_round - sos_window + 1), max_round + 1)
    recent = all_rows[all_rows["round"].isin(recent_rounds)]
    form = (
        recent.groupby("team_key")
        .agg(pts_sum=("pts", "sum"), mp_recent=("pts", "count"))
        .assign(form_ppg=lambda d: d["pts_sum"] / d["mp_recent"])
        .reset_index()
    )
    c4 = dict(zip(form["team_key"], form["form_ppg"]))

    # ── Assemble into table ───────────────────────────────────────────────────
    teams = xpts_df[["team_key", "team_name", "MP", "xPts", "Pts", "pts_diff"]].copy()
    if "sos" in xpts_df.columns:
        teams["sos_global"] = xpts_df["sos"].values

    teams["c_xpts_mp"]   = teams["team_key"].map(c1).fillna(0.0)
    teams["c_net_xg_mp"] = teams["team_key"].map(c2).fillna(0.0)
    teams["c_sos_adj"]   = teams["team_key"].map(c3).fillna(0.0)
    teams["c_form"]      = teams["team_key"].map(c4).fillna(0.0)
    teams["sos_rolling"] = teams["team_key"].map(sos_rolling).round(3)

    # Normalise each component to [0,1]
    teams["n_xpts_mp"]   = _norm(teams["c_xpts_mp"])
    teams["n_net_xg_mp"] = _norm(teams["c_net_xg_mp"])
    teams["n_sos_adj"]   = _norm(teams["c_sos_adj"])
    teams["n_form"]      = _norm(teams["c_form"])

    # Weighted composite — scale to 0-100 for readability
    teams["power_score"] = (
        WEIGHTS["xpts_mp"]   * teams["n_xpts_mp"]
        + WEIGHTS["net_xg_mp"] * teams["n_net_xg_mp"]
        + WEIGHTS["sos_adj"]   * teams["n_sos_adj"]
        + WEIGHTS["form"]      * teams["n_form"]
    ) * 100

    teams["power_score"] = teams["power_score"].round(1)
    teams = teams.sort_values("power_score", ascending=False).reset_index(drop=True)
    teams.insert(0, "rank_power", range(1, len(teams) + 1))

    teams["sos_window"] = sos_window
    teams["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"

    out_cols = [
        "rank_power", "team_key", "team_name", "MP",
        "power_score",
        "n_xpts_mp", "n_net_xg_mp", "n_sos_adj", "n_form",
        "c_xpts_mp", "c_net_xg_mp", "c_sos_adj", "c_form",
        "xPts", "Pts", "pts_diff",
        "sos_rolling", "sos_window",
        "generated_at",
    ]
    if "sos_global" in teams.columns:
        out_cols.insert(out_cols.index("sos_rolling"), "sos_global")

    out_path = curated / "power_ranking.csv"
    write_csv(out_path, teams[out_cols].to_dict("records"))
    logger.info(
        "Power ranking: %d teams, SOS window=%d, top=%s (%.1f) → %s",
        len(teams),
        sos_window,
        teams.iloc[0]["team_name"],
        teams.iloc[0]["power_score"],
        out_path,
    )
