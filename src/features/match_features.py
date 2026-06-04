"""
Feature engineering for Série B 2026 match prediction.

Public API:
    build_match_features(matches, stats, players=None, rolling_window=3) -> pd.DataFrame

Feature groups:
    A. Diferenciais (home - away)
    B. Eficiência de finalização
    C. Rolling form (últimas N partidas ANTES da rodada)
    D. xG contextual (relativo à qualidade defensiva do adversário)
    E. Field Tilt e domínio territorial
    F. Posicionamento médio de jogadores (proxy via player_match_stats)

PRÉ-JOGO INVARIANT (frente 1 — fix do gap treino × inferência):
    Todas as features computadas a partir de `xg_h/xg_a/sot_h/sot_a/poss_h/poss_a/
    passes_acc_pct_h/passes_acc_pct_a/corners_h/corners_a/shots_h/shots_a` e do
    `prog_ratio_h/prog_ratio_a` derivam de **rolling lag-1** sobre as partidas
    anteriores de cada time — exatamente o que `build_target_round_features`
    monta na inferência. Os valores ATUAIS da partida só são preservados para
    o target (`result`, `goals_h`, `goals_a`) e para a feature interna
    `rolling_xg_diff_3` (computada antes do swap em `_add_rolling_form`).
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ── Position encoding ─────────────────────────────────────────────────────────
_POS_NUM: dict[str, int] = {
    "G": 0, "GK": 0,
    "D": 1, "CB": 1, "LB": 1, "RB": 1, "LWB": 1, "RWB": 1, "WB": 1,
    "M": 2, "CM": 2, "DM": 2, "AM": 2, "CDM": 2, "CAM": 2,
    "LM": 2, "RM": 2, "WM": 2,
    "F": 3, "FW": 3, "ST": 3, "LW": 3, "RW": 3, "CF": 3, "SS": 3,
}


def _n(col: pd.Series) -> pd.Series:
    return pd.to_numeric(col, errors="coerce")


def _safe_div(a: pd.Series, b: pd.Series) -> pd.Series:
    with np.errstate(divide="ignore", invalid="ignore"):
        result = np.where(b != 0, a / b, np.nan)
    return pd.Series(result, index=a.index)


# ── Step 0: build match-level dataset ────────────────────────────────────────

def _build_match_level(matches: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    completed = matches[matches["status"] == "completed"].copy()
    s = stats[stats["match_code"].isin(completed["match_code"])].copy()
    s["is_home"] = s["is_home"].map(
        {"True": True, "False": False, True: True, False: False}
    )

    NUMERIC = [
        "expected_goals", "shots_total", "shots_on_target", "shots_on_target_pct",
        "possession", "passes_total", "passes_accurate", "passes_accuracy_pct",
        "corners", "fouls", "tackles_total", "yellow_cards", "red_cards",
    ]
    for c in NUMERIC:
        if c in s.columns:
            s[c] = _n(s[c])

    RENAME_H = {
        "team_key": "home_team_key", "team_name": "home_team_name",
        "expected_goals": "xg_h", "shots_total": "shots_h",
        "shots_on_target": "sot_h", "shots_on_target_pct": "sot_pct_h",
        "possession": "poss_h", "passes_accuracy_pct": "passes_acc_pct_h",
        "corners": "corners_h", "fouls": "fouls_h",
        "tackles_total": "tackles_h", "yellow_cards": "yellow_h",
        "red_cards": "red_h",
    }
    RENAME_A = {k: v.replace("_h", "_a") for k, v in RENAME_H.items()}

    def _side(is_home_val, rename):
        sub = s[s["is_home"] == is_home_val].copy()
        cols = {src: dst for src, dst in rename.items() if src in sub.columns}
        sub = sub.rename(columns=cols)[[c for c in cols.values()]]
        return sub.set_index(sub.index)  # index will be reset after join

    home_side = s[s["is_home"] == True].copy()
    away_side = s[s["is_home"] == False].copy()

    def _extract(side, rename):
        cols_avail = {src: dst for src, dst in rename.items() if src in side.columns}
        return side.rename(columns=cols_avail)[[*cols_avail.values()]].set_index(
            side["match_code"].values
        )

    df_h = _extract(home_side, RENAME_H)
    df_a = _extract(away_side, RENAME_A)

    season_col = ["season"] if "season" in completed.columns else []
    base = completed[[
        "match_code", "round", *season_col, "home_team", "away_team",
        "home_team_key", "away_team_key", "home_score", "away_score",
    ]].copy()
    base["round"]      = _n(base["round"])
    base["home_score"] = _n(base["home_score"])
    base["away_score"] = _n(base["away_score"])

    df = base.set_index("match_code").join(df_h, rsuffix="_dup_h").join(
        df_a, rsuffix="_dup_a"
    ).reset_index()

    # Target
    def _result(r):
        if r["home_score"] > r["away_score"]:  return "H"
        if r["home_score"] == r["away_score"]: return "D"
        return "A"

    df["result"]     = df.apply(_result, axis=1)
    df["result_num"] = df["result"].map({"H": 1, "D": 0, "A": -1})
    df["goals_h"]    = df["home_score"]
    df["goals_a"]    = df["away_score"]
    df["pts_h"]      = df["result"].map({"H": 3, "D": 1, "A": 0})
    df["pts_a"]      = df["result"].map({"H": 0, "D": 1, "A": 3})

    return df.sort_values("round").reset_index(drop=True)


# ── Group A: Diferenciais ─────────────────────────────────────────────────────

def _add_differentials(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    pairs = [
        ("xg",            "xg_h",           "xg_a"),
        ("shots",         "shots_h",         "shots_a"),
        ("sot",           "sot_h",           "sot_a"),
        ("poss",          "poss_h",          "poss_a"),
        ("passes_acc_pct","passes_acc_pct_h","passes_acc_pct_a"),
        ("corners",       "corners_h",       "corners_a"),
        ("tackles",       "tackles_h",       "tackles_a"),
        ("yellow",        "yellow_h",        "yellow_a"),
    ]
    for name, h, a in pairs:
        if h in df.columns and a in df.columns:
            df[f"{name}_diff"] = df[h] - df[a]
    return df


# ── Group B: Eficiência de finalização ────────────────────────────────────────

def _add_shot_efficiency(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for side, goals in [("h", "goals_h"), ("a", "goals_a")]:
        xg    = df[f"xg_{side}"]
        shots = df[f"shots_{side}"]
        sot   = df[f"sot_{side}"]
        g     = df[goals]
        df[f"xg_per_shot_{side}"]        = _safe_div(xg, shots)
        df[f"xg_per_sot_{side}"]         = _safe_div(xg, sot)
        df[f"sot_conversion_{side}"]     = _safe_div(g,  sot)
        df[f"xg_overperformance_{side}"] = g - xg  # >0: marcou mais que esperado
    df["xg_per_shot_diff"]        = df["xg_per_shot_h"]        - df["xg_per_shot_a"]
    df["xg_overperformance_diff"] = df["xg_overperformance_h"] - df["xg_overperformance_a"]
    return df


# ── Group C: Rolling form ─────────────────────────────────────────────────────

def _add_rolling_form(df: pd.DataFrame, window: int = 3) -> pd.DataFrame:
    df = df.copy()

    home_rows = df[["match_code", "round", "home_team_key",
                    "xg_h", "xg_a", "sot_h", "pts_h"]].rename(columns={
        "home_team_key": "team_key",
        "xg_h": "xg_prod", "xg_a": "xg_conc", "sot_h": "sot", "pts_h": "pts",
    })
    away_rows = df[["match_code", "round", "away_team_key",
                    "xg_a", "xg_h", "sot_a", "pts_a"]].rename(columns={
        "away_team_key": "team_key",
        "xg_a": "xg_prod", "xg_h": "xg_conc", "sot_a": "sot", "pts_a": "pts",
    })
    long = pd.concat([home_rows, away_rows], ignore_index=True).sort_values(
        ["team_key", "round"]
    )

    # shift(1) before rolling ensures current match is excluded
    rolling_lookup: dict[str, dict[str, float]] = {}
    for team_key, grp in long.groupby("team_key"):
        grp = grp.sort_values("round")
        for col in ("xg_prod", "xg_conc", "sot", "pts"):
            rolled = grp[col].shift(1).rolling(window, min_periods=1).mean()
            for mc, val in zip(grp["match_code"], rolled.values):
                key = f"{col}__{team_key}"
                rolling_lookup.setdefault(key, {})[mc] = float(val) if not np.isnan(val) else np.nan

    for col in ("xg_prod", "xg_conc", "sot", "pts"):
        for side, team_col in (("h", "home_team_key"), ("a", "away_team_key")):
            feat = f"rolling_{col}_{window}_{side}"
            df[feat] = [
                rolling_lookup.get(f"{col}__{row[team_col]}", {}).get(row["match_code"], np.nan)
                for _, row in df.iterrows()
            ]

    w = window
    df[f"rolling_xg_diff_{w}"]     = df[f"rolling_xg_prod_{w}_h"]  - df[f"rolling_xg_prod_{w}_a"]
    df[f"rolling_xgconc_diff_{w}"] = df[f"rolling_xg_conc_{w}_h"]  - df[f"rolling_xg_conc_{w}_a"]
    df[f"rolling_pts_diff_{w}"]    = df[f"rolling_pts_{w}_h"]       - df[f"rolling_pts_{w}_a"]
    return df


# ── Group D: xG contextual (relativo à defesa do adversário) ──────────────────

def _add_opponent_context(df: pd.DataFrame) -> pd.DataFrame:
    """xG de cada time relativo ao xG médio que o adversário concedia antes da rodada."""
    df = df.copy()

    # Montar tabela de duelos ataque×defesa
    duel_rows = []
    for _, r in df.iterrows():
        duel_rows.extend([
            {"round": r["round"], "attacker": r["home_team_key"],
             "defender": r["away_team_key"], "xg": r["xg_h"]},
            {"round": r["round"], "attacker": r["away_team_key"],
             "defender": r["home_team_key"], "xg": r["xg_a"]},
        ])
    duels = pd.DataFrame(duel_rows)

    def avg_xga_before(defender: str, before_round: int) -> float:
        prior = duels[(duels["defender"] == defender) & (duels["round"] < before_round)]
        return float(prior["xg"].mean()) if not prior.empty else np.nan

    xg_ctx_h, xg_ctx_a = [], []
    for _, row in df.iterrows():
        avg_def_a = avg_xga_before(row["away_team_key"], row["round"])
        avg_def_h = avg_xga_before(row["home_team_key"], row["round"])
        # xG do time / xGA médio do adversário: >1 = gerou mais que o usual
        xg_ctx_h.append(row["xg_h"] / avg_def_a if avg_def_a and avg_def_a > 0 else np.nan)
        xg_ctx_a.append(row["xg_a"] / avg_def_h if avg_def_h and avg_def_h > 0 else np.nan)

    df["xg_ctx_h"] = xg_ctx_h
    df["xg_ctx_a"] = xg_ctx_a
    df["xg_ctx_diff"] = np.where(
        pd.notna(df["xg_ctx_h"]) & pd.notna(df["xg_ctx_a"]),
        df["xg_ctx_h"] - df["xg_ctx_a"],
        np.nan,
    )
    return df


# ── Group E: Field Tilt ───────────────────────────────────────────────────────

def _add_field_tilt(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    total_shots = df["shots_h"] + df["shots_a"]
    total_sot   = df["sot_h"]   + df["sot_a"]
    total_xg    = df["xg_h"]    + df["xg_a"]

    df["field_tilt_h"]     = _safe_div(df["shots_h"], total_shots)
    df["field_tilt_sot_h"] = _safe_div(df["sot_h"],   total_sot)
    df["xg_tilt_h"]        = _safe_div(df["xg_h"],    total_xg)

    # Centrado em 0.5 → positivo = domínio do mandante
    df["field_tilt_diff"]     = df["field_tilt_h"]     - 0.5
    df["field_tilt_sot_diff"] = df["field_tilt_sot_h"] - 0.5
    df["xg_tilt_diff"]        = df["xg_tilt_h"]        - 0.5
    return df


# ── Group F: Posicionamento médio de jogadores ────────────────────────────────

def _add_line_height(df: pd.DataFrame, players: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    p = players.copy()
    p["is_home"] = p["is_home"].map(
        {"True": True, "False": False, True: True, False: False}
    )
    p["pos_num"]         = p["position"].str.upper().map(_POS_NUM)
    p["minutes_played"]  = _n(p["minutes_played"])
    prog_col  = "progressive_ball_carries_count"
    carry_col = "ball_carries_count"
    if prog_col in p.columns:
        p[prog_col]  = _n(p[prog_col])
    if carry_col in p.columns:
        p[carry_col] = _n(p[carry_col])

    # Line Height Index: média de posição ponderada por minutos jogados
    lh_rows = []
    for (mc, is_home), grp in p.groupby(["match_code", "is_home"]):
        valid = grp.dropna(subset=["pos_num", "minutes_played"])
        total_min = valid["minutes_played"].sum()
        lh = float(np.average(valid["pos_num"], weights=valid["minutes_played"])) \
             if (not valid.empty and total_min > 0) else np.nan
        lh_rows.append({"match_code": mc, "is_home": is_home, "line_height": lh})
    lh_df = pd.DataFrame(lh_rows)

    # Progressive Pressure Ratio: carries progressivos / total carries
    pr_rows = []
    for (mc, is_home), grp in p.groupby(["match_code", "is_home"]):
        if prog_col in p.columns and carry_col in p.columns:
            total_prog  = grp[prog_col].sum()
            total_carry = grp[carry_col].sum()
            pr = float(total_prog / total_carry) if total_carry > 0 else np.nan
        else:
            pr = np.nan
        pr_rows.append({"match_code": mc, "is_home": is_home, "prog_ratio": pr})
    pr_df = pd.DataFrame(pr_rows)

    def _merge_side(feat_df, value_col, suffix):
        sub_h = feat_df[feat_df["is_home"] == True].set_index("match_code")[value_col].rename(f"{value_col}_{suffix}h")
        sub_a = feat_df[feat_df["is_home"] == False].set_index("match_code")[value_col].rename(f"{value_col}_{suffix}a")
        return sub_h, sub_a

    lh_h, lh_a = _merge_side(lh_df, "line_height", "")
    pr_h, pr_a = _merge_side(pr_df, "prog_ratio",   "")

    df = df.set_index("match_code")
    df = df.join(lh_h.rename("line_height_h")).join(lh_a.rename("line_height_a"))
    df = df.join(pr_h.rename("prog_ratio_h")).join(pr_a.rename("prog_ratio_a"))
    df["line_height_diff"] = df["line_height_h"] - df["line_height_a"]
    df["prog_ratio_diff"]  = df["prog_ratio_h"]  - df["prog_ratio_a"]
    df = df.reset_index()
    return df


# ── Pre-match swap helpers (frente 1 fix) ────────────────────────────────────

_TEAM_METRIC_MAP = {
    "xg": "expected_goals",
    "shots": "shots_total",
    "sot": "shots_on_target",
    "poss": "possession",
    "passes_acc_pct": "passes_accuracy_pct",
    "corners": "corners",
}


def _team_lag1_rolling_lookup(
    matches: pd.DataFrame, stats: pd.DataFrame, window: int = 3
) -> dict:
    """Para cada (team_key, match_code), rolling lag-1 das métricas do time
    nas partidas anteriores (mesma definição usada em inferência).

    shift(1).rolling(window, min_periods=1).mean() → primeira aparição do time
    fica NaN; segunda já tem 1 amostra, e assim por diante.

    Returns: {(team_key, match_code): {xg, shots, sot, poss, passes_acc_pct, corners}}
    """
    completed_codes = set(matches[matches["status"] == "completed"]["match_code"])
    s = stats[stats["match_code"].isin(completed_codes)].copy()
    if "round" not in s.columns:
        s = s.merge(
            matches[["match_code", "round"]].drop_duplicates(),
            on="match_code", how="left",
        )
    s["round"] = _n(s["round"])
    for col in _TEAM_METRIC_MAP.values():
        if col in s.columns:
            s[col] = _n(s[col])

    lookup: dict = {}
    for team_key, grp in s.groupby("team_key"):
        grp = grp.sort_values("round")
        rolled = {}
        for short, col in _TEAM_METRIC_MAP.items():
            if col in grp.columns:
                rolled[short] = grp[col].shift(1).rolling(window, min_periods=1).mean().values
            else:
                rolled[short] = np.full(len(grp), np.nan)
        for i, mc in enumerate(grp["match_code"].values):
            lookup[(team_key, mc)] = {
                short: float(rolled[short][i]) if not np.isnan(rolled[short][i]) else np.nan
                for short in _TEAM_METRIC_MAP
            }
    return lookup


def _swap_to_prematch(
    df: pd.DataFrame, matches: pd.DataFrame, stats: pd.DataFrame, window: int = 3
) -> pd.DataFrame:
    """Substitui valores ATUAIS da partida por rolling lag-1 — alinha treino
    com inferência. Mantém `goals_h/goals_a/result*` intactos (target)."""
    df = df.copy()
    lookup = _team_lag1_rolling_lookup(matches, stats, window=window)
    swap_pairs = [
        ("xg", "xg_h", "xg_a"),
        ("shots", "shots_h", "shots_a"),
        ("sot", "sot_h", "sot_a"),
        ("poss", "poss_h", "poss_a"),
        ("passes_acc_pct", "passes_acc_pct_h", "passes_acc_pct_a"),
        ("corners", "corners_h", "corners_a"),
    ]
    home_keys = df["home_team_key"].values
    away_keys = df["away_team_key"].values
    match_codes = df["match_code"].values
    for short, h_col, a_col in swap_pairs:
        df[h_col] = [
            lookup.get((hk, mc), {}).get(short, np.nan)
            for hk, mc in zip(home_keys, match_codes)
        ]
        df[a_col] = [
            lookup.get((ak, mc), {}).get(short, np.nan)
            for ak, mc in zip(away_keys, match_codes)
        ]
    return df


def _player_prog_ratio_lag1_lookup(
    matches: pd.DataFrame, players: pd.DataFrame, window: int = 3
) -> dict:
    """Rolling lag-1 do prog_ratio (sum(prog_carries)/sum(carries)) por team_key.
    Returns: {(team_key, match_code): float}"""
    if players is None or players.empty:
        return {}
    prog_col, carry_col = "progressive_ball_carries_count", "ball_carries_count"
    if prog_col not in players.columns or carry_col not in players.columns:
        return {}

    p = players.copy()
    p[prog_col] = _n(p[prog_col])
    p[carry_col] = _n(p[carry_col])

    rows = []
    for (mc, tk), grp in p.groupby(["match_code", "team_key"]):
        total = grp[carry_col].sum()
        prog = grp[prog_col].sum()
        rows.append({
            "match_code": mc,
            "team_key": tk,
            "prog_ratio": float(prog / total) if total > 0 else np.nan,
        })
    pr = pd.DataFrame(rows)

    m_round = matches[["match_code", "round"]].copy()
    m_round["round"] = _n(m_round["round"])
    pr = pr.merge(m_round, on="match_code", how="inner").sort_values(["team_key", "round"])

    lookup: dict = {}
    for tk, grp in pr.groupby("team_key"):
        grp = grp.sort_values("round")
        rolled = grp["prog_ratio"].shift(1).rolling(window, min_periods=1).mean()
        for mc, v in zip(grp["match_code"], rolled.values):
            lookup[(tk, mc)] = float(v) if not np.isnan(v) else np.nan
    return lookup


def _swap_player_to_prematch(
    df: pd.DataFrame, matches: pd.DataFrame, players: pd.DataFrame, window: int = 3
) -> pd.DataFrame:
    """Sobrescreve prog_ratio_h/prog_ratio_a/prog_ratio_diff com rolling lag-1."""
    df = df.copy()
    lookup = _player_prog_ratio_lag1_lookup(matches, players, window=window)
    if not lookup:
        return df
    h_vals, a_vals = [], []
    for hk, ak, mc in zip(df["home_team_key"], df["away_team_key"], df["match_code"]):
        h_vals.append(lookup.get((hk, mc), np.nan))
        a_vals.append(lookup.get((ak, mc), np.nan))
    df["prog_ratio_h"] = h_vals
    df["prog_ratio_a"] = a_vals
    df["prog_ratio_diff"] = df["prog_ratio_h"] - df["prog_ratio_a"]
    return df


# ── To-date strength (frente 2) ──────────────────────────────────────────────

def _build_todate_strength_lookup(
    matches: pd.DataFrame, stats: pd.DataFrame
) -> dict:
    """Para cada (team_key, match_code) em partidas concluídas, métricas
    cumulativas calculadas SOMENTE com as partidas anteriores do time na
    mesma temporada — PPG, xG produzido/jogo, xG concedido/jogo.

    Usa expanding().mean() com shift(1) → primeira partida do time fica NaN,
    segunda já tem 1 amostra, etc. Sinal de força estável que complementa o
    rolling-3 (forma recente).

    Returns: {(team_key, match_code): {ppg, xg_pm, xg_conc_pm}}
    """
    completed = matches[matches["status"] == "completed"].copy()
    if completed.empty:
        return {}
    completed["round"] = _n(completed["round"])
    completed["home_score"] = _n(completed["home_score"])
    completed["away_score"] = _n(completed["away_score"])
    completed = completed.dropna(subset=["home_score", "away_score", "round"])

    s = stats[stats["match_code"].isin(completed["match_code"])].copy()
    s["is_home"] = s["is_home"].map(
        {"True": True, "False": False, True: True, False: False}
    )
    s["expected_goals"] = _n(s["expected_goals"])
    # Mapeamento rápido de xG por match_code+is_home
    s_idx = s.set_index(["match_code", "is_home"])["expected_goals"].to_dict()

    rows = []
    for _, m in completed.iterrows():
        mc = m["match_code"]
        h_score, a_score = m["home_score"], m["away_score"]
        h_pts = 3.0 if h_score > a_score else (1.0 if h_score == a_score else 0.0)
        a_pts = 3.0 if a_score > h_score else (1.0 if a_score == h_score else 0.0)
        h_xg = s_idx.get((mc, True), np.nan)
        a_xg = s_idx.get((mc, False), np.nan)
        rows.append({
            "team_key": m["home_team_key"], "match_code": mc,
            "round": m["round"], "pts": h_pts,
            "xg_prod": h_xg, "xg_conc": a_xg,
        })
        rows.append({
            "team_key": m["away_team_key"], "match_code": mc,
            "round": m["round"], "pts": a_pts,
            "xg_prod": a_xg, "xg_conc": h_xg,
        })

    long = pd.DataFrame(rows)
    if long.empty:
        return {}
    long = long.sort_values(["team_key", "round"]).reset_index(drop=True)

    lookup: dict = {}
    for tk, grp in long.groupby("team_key"):
        grp = grp.sort_values("round").reset_index(drop=True)
        ppg_td = grp["pts"].shift(1).expanding().mean()
        xgp_td = grp["xg_prod"].shift(1).expanding().mean()
        xgc_td = grp["xg_conc"].shift(1).expanding().mean()
        for i, mc in enumerate(grp["match_code"].values):
            lookup[(tk, mc)] = {
                "ppg": float(ppg_td.iloc[i]) if pd.notna(ppg_td.iloc[i]) else np.nan,
                "xg_pm": float(xgp_td.iloc[i]) if pd.notna(xgp_td.iloc[i]) else np.nan,
                "xg_conc_pm": float(xgc_td.iloc[i]) if pd.notna(xgc_td.iloc[i]) else np.nan,
            }
    return lookup


def _attach_todate_strength(
    df: pd.DataFrame, matches: pd.DataFrame, stats: pd.DataFrame
) -> pd.DataFrame:
    """Adiciona ppg_diff_todate / xg_pm_diff_todate / xg_conc_pm_diff_todate."""
    df = df.copy()
    lookup = _build_todate_strength_lookup(matches, stats)
    if not lookup:
        for col in ("ppg_diff_todate", "xg_pm_diff_todate", "xg_conc_pm_diff_todate"):
            df[col] = np.nan
        return df

    home_keys = df["home_team_key"].values
    away_keys = df["away_team_key"].values
    match_codes = df["match_code"].values

    def _diff(metric: str) -> list:
        out = []
        for hk, ak, mc in zip(home_keys, away_keys, match_codes):
            hv = lookup.get((hk, mc), {}).get(metric, np.nan)
            av = lookup.get((ak, mc), {}).get(metric, np.nan)
            out.append(hv - av if pd.notna(hv) and pd.notna(av) else np.nan)
        return out

    df["ppg_diff_todate"] = _diff("ppg")
    df["xg_pm_diff_todate"] = _diff("xg_pm")
    df["xg_conc_pm_diff_todate"] = _diff("xg_conc_pm")
    return df


# ── Public API ────────────────────────────────────────────────────────────────

def build_match_features(
    matches: pd.DataFrame,
    stats: pd.DataFrame,
    players: pd.DataFrame | None = None,
    rolling_window: int = 3,
) -> pd.DataFrame:
    """
    Retorna DataFrame match-level com todas as features preditivas + target.

    Args:
        matches:        data/curated/serie_b_2026/matches.csv
        stats:          data/curated/serie_b_2026/team_match_stats.csv
        players:        data/curated/serie_b_2026/player_match_stats.csv (opcional)
        rolling_window: janela de rolling form (partidas anteriores)

    Returns:
        DataFrame com uma linha por partida concluída.
        Colunas-alvo: result ("H"/"D"/"A"), result_num (1/0/-1).
        Feature groups A-E sempre presentes; F exige players != None.

    Ordem importa: `_add_rolling_form` roda ANTES do swap pois precisa dos
    valores atuais para construir o lookup; depois substituímos `xg_h/xg_a/...`
    pelos rolling lag-1 e só então rodamos differentials/efficiency/ctx/tilt.
    """
    df = _build_match_level(matches, stats)
    df = _add_rolling_form(df, window=rolling_window)
    df = _swap_to_prematch(df, matches, stats, window=rolling_window)
    df = _add_differentials(df)
    df = _add_shot_efficiency(df)
    df = _add_opponent_context(df)
    df = _add_field_tilt(df)
    df = _attach_todate_strength(df, matches, stats)
    if players is not None:
        df = _add_line_height(df, players)
        df = _swap_player_to_prematch(df, matches, players, window=rolling_window)
    return df
