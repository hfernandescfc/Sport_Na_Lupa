"""Feature engineering para o módulo preditivo.

Duas funções centrais:
    build_training_pool(settings, current_season)
        -> DataFrame com TODAS as partidas concluídas (2025 + temporada
           corrente), incluindo as últimas rodadas que entraram no curated.
           Sempre regerado on-the-fly via src.features.match_features —
           garantindo que o modelo evolua a cada novo round.

    build_target_round_features(settings, season, round_number)
        -> DataFrame com features dos jogos da rodada-alvo, construídas via
           rolling proxies (window=3) sobre o histórico R1..R_{round-1} da
           temporada corrente. Permite previsões pré-jogo.

Convenção: o modelo de produção usa LogisticRegression + FULL features (18),
mas este módulo apenas constrói o DataFrame — quem decide o conjunto de
features é o round_predictor.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.features.match_features import build_match_features


# Feature set padrão (14 pre-match + 2 to-date strength + 2 player = 18)
#
# Frente 2: rolling_xg_diff_3 e rolling_pts_diff_3 saíram em favor das
# versões cumulativas (`ppg_diff_todate`, `xg_pm_diff_todate`). Os pares têm
# r≈0.73 entre si — manter ambos só gerava redundância. As todate têm sinal
# mais forte com o target (r=+0.114 e +0.200 vs +0.013 e +0.088 das rolling).
#
# Backtest walk-forward R3-R9 (LR C=0.1):
#   - Frente 1 (16 pre + 2 player, sem todate): 41.7%
#   - Frente 2 substituição (14 pre + 2 todate + 2 player): 40.3%
# Diferença dentro do erro amostral (~1 acerto em 72). A versão de
# substituição é conceitualmente mais sólida (força acumulada > forma curta)
# e tende a render mais com modelos não-lineares (frente 3).
PREMATCH_CORE = [
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff",
    "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
]
STRENGTH_FEATURES = [
    "ppg_diff_todate", "xg_pm_diff_todate",
]
PLAYER_FEATURES = ["prog_ratio_diff", "prog_ratio_h"]
FULL_FEATURES = PREMATCH_CORE + STRENGTH_FEATURES + PLAYER_FEATURES


def _curated_paths(base_dir: Path, season: int) -> dict[str, Path]:
    folder = base_dir / "data" / "curated" / f"serie_b_{season}"
    return {
        "matches": folder / "matches.csv",
        "stats": folder / "team_match_stats.csv",
        "players": folder / "player_match_stats.csv",
    }


def _load_season_features(base_dir: Path, season: int, rolling_window: int = 3) -> pd.DataFrame | None:
    """Carrega CSVs curados de uma temporada e roda build_match_features.
    Retorna None se a temporada não tiver dados."""
    paths = _curated_paths(base_dir, season)
    if not paths["matches"].exists() or not paths["stats"].exists():
        return None

    matches = pd.read_csv(paths["matches"])
    stats = pd.read_csv(paths["stats"])
    players = pd.read_csv(paths["players"]) if paths["players"].exists() else None

    if matches.empty or stats.empty:
        return None

    df = build_match_features(matches, stats, players=players, rolling_window=rolling_window)
    if "season" not in df.columns:
        df["season"] = season
    return df


def build_training_pool(
    base_dir: Path,
    current_season: int,
    historical_seasons: tuple[int, ...] = (2025,),
    rolling_window: int = 3,
) -> pd.DataFrame:
    """Pool de treino = histórico + TODAS as rodadas concluídas da temporada corrente.

    O ponto crítico do design: chamamos build_match_features sobre o curated
    atual, então quando o usuário sincronizar uma nova rodada (R9, R10, ...)
    ela entra automaticamente no treino na próxima execução.

    Imputação de prog_ratio: temporadas históricas sem player_match_stats
    recebem a mediana do prog_ratio observado na temporada corrente. Isso
    permite manter o pool 2025 + 2026 mesmo com features FULL.
    """
    frames: list[pd.DataFrame] = []
    for season in (*historical_seasons, current_season):
        df = _load_season_features(base_dir, season, rolling_window=rolling_window)
        if df is None:
            continue
        df["data_source"] = f"serie_b_{season}"
        frames.append(df)

    if not frames:
        raise RuntimeError("Nenhuma temporada com dados curados disponíveis.")

    pool = pd.concat(frames, ignore_index=True)

    # Imputação para colunas que podem faltar em temporadas históricas ou na
    # primeira rodada (sem prior). Usa a mediana da temporada corrente.
    current_pool = pool[pool["season"] == current_season]
    impute_cols = ("prog_ratio_h", "prog_ratio_diff",
                   "ppg_diff_todate", "xg_pm_diff_todate", "xg_conc_pm_diff_todate")
    for col in impute_cols:
        if col in pool.columns and col in current_pool.columns:
            ref = pd.to_numeric(current_pool[col], errors="coerce").median()
            if pd.notna(ref):
                pool[col] = pool[col].fillna(ref)

    # Filtra apenas partidas concluídas (têm result definido) e sem NaN nas features
    pool = pool.dropna(subset=FULL_FEATURES + ["result"])
    pool["result_encoded"] = pool["result"].map({"A": 0, "D": 1, "H": 2})
    return pool


def _team_rolling_proxies(
    stats: pd.DataFrame,
    matches: pd.DataFrame,
    target_round: int,
    window: int = 3,
) -> dict[str, dict[str, float]]:
    """Médias móveis (window) por time, a partir de R1..R_{target_round-1}.
    Retorna {team_key: {xg, shots, sot, poss, passes_acc_pct, corners, pts, xg_conc}}.
    """
    df = stats[stats["round"] < target_round].copy()
    if df.empty:
        return {}
    df = df.sort_values(["team_key", "round"])

    # Mapa de scores para calcular pontos
    m_prior = matches[matches["round"] < target_round]
    scores = {
        row["match_code"]: (row.get("home_score"), row.get("away_score"))
        for _, row in m_prior.iterrows()
    }

    def _pts(row) -> float:
        sc = scores.get(row["match_code"])
        if sc is None or pd.isna(sc[0]) or pd.isna(sc[1]):
            return np.nan
        h, a = sc
        if row.get("is_home") in (True, "True"):
            return 3.0 if h > a else (1.0 if h == a else 0.0)
        return 3.0 if a > h else (1.0 if a == h else 0.0)

    df["pts"] = df.apply(_pts, axis=1)

    out: dict[str, dict[str, float]] = {}
    NUMERIC_COLS = {
        "xg": "expected_goals",
        "shots": "shots_total",
        "sot": "shots_on_target",
        "poss": "possession",
        "passes_acc_pct": "passes_accuracy_pct",
        "corners": "corners",
    }

    for team_key, grp in df.groupby("team_key"):
        grp = grp.sort_values("round")
        agg: dict[str, float] = {}
        for short, col in NUMERIC_COLS.items():
            if col in grp.columns:
                rolled = pd.to_numeric(grp[col], errors="coerce").rolling(window=window, min_periods=1).mean()
                agg[short] = float(rolled.iloc[-1]) if len(rolled) else np.nan
            else:
                agg[short] = np.nan
        # pontos
        agg["pts"] = float(grp["pts"].rolling(window=window, min_periods=1).mean().iloc[-1])

        # xG concedido: olhar partidas do time, somar xG do adversário
        team_matches = grp["match_code"].unique()
        opp = df[(df["match_code"].isin(team_matches)) & (df["team_key"] != team_key)]
        if not opp.empty:
            xg_conc_series = pd.to_numeric(opp["expected_goals"], errors="coerce").tolist()
            agg["xg_conc"] = float(np.mean(xg_conc_series[-window:])) if xg_conc_series else 1.0
        else:
            agg["xg_conc"] = 1.0

        out[team_key] = agg
    return out


def _team_todate_strength(
    matches: pd.DataFrame,
    stats: pd.DataFrame,
    target_round: int,
) -> dict[str, dict[str, float]]:
    """PPG/xG/xGA acumulativo por time, usando SOMENTE partidas com round
    estritamente menor que target_round. Espelha a semântica do treino
    (`_build_todate_strength_lookup` em match_features.py).
    Returns: {team_key: {ppg, xg_pm, xg_conc_pm}}
    """
    completed = matches[
        (matches["status"] == "completed") & (matches["round"] < target_round)
    ].copy()
    if completed.empty:
        return {}
    completed["home_score"] = pd.to_numeric(completed["home_score"], errors="coerce")
    completed["away_score"] = pd.to_numeric(completed["away_score"], errors="coerce")
    completed = completed.dropna(subset=["home_score", "away_score"])

    s = stats[stats["match_code"].isin(completed["match_code"])].copy()
    s["is_home"] = s["is_home"].map(
        {"True": True, "False": False, True: True, False: False}
    )
    s["expected_goals"] = pd.to_numeric(s["expected_goals"], errors="coerce")
    s_idx = s.set_index(["match_code", "is_home"])["expected_goals"].to_dict()

    rows = []
    for _, m in completed.iterrows():
        mc = m["match_code"]
        h_score, a_score = m["home_score"], m["away_score"]
        h_pts = 3.0 if h_score > a_score else (1.0 if h_score == a_score else 0.0)
        a_pts = 3.0 if a_score > h_score else (1.0 if a_score == h_score else 0.0)
        h_xg = s_idx.get((mc, True), np.nan)
        a_xg = s_idx.get((mc, False), np.nan)
        rows.append({"team_key": m["home_team_key"], "pts": h_pts,
                     "xg_prod": h_xg, "xg_conc": a_xg})
        rows.append({"team_key": m["away_team_key"], "pts": a_pts,
                     "xg_prod": a_xg, "xg_conc": h_xg})

    long = pd.DataFrame(rows)
    if long.empty:
        return {}
    agg = long.groupby("team_key").agg(
        ppg=("pts", "mean"),
        xg_pm=("xg_prod", "mean"),
        xg_conc_pm=("xg_conc", "mean"),
    ).to_dict("index")
    return agg


def _prog_ratio_rolling(
    players: pd.DataFrame | None,
    matches: pd.DataFrame,
    target_round: int,
    window: int = 3,
) -> dict[str, float]:
    """Rolling mean (window) do prog_ratio (progressive carries / total carries) por team_key."""
    if players is None or players.empty:
        return {}
    cols = {"progressive_ball_carries_count", "ball_carries_count", "match_code", "team_key"}
    if not cols.issubset(players.columns):
        return {}

    m_prior = matches[matches["round"] < target_round][["match_code", "round"]]
    df = players.merge(m_prior, on="match_code", how="inner")
    if df.empty:
        return {}

    rows = []
    for (mc, tk), grp in df.groupby(["match_code", "team_key"]):
        total = pd.to_numeric(grp["ball_carries_count"], errors="coerce").sum()
        prog = pd.to_numeric(grp["progressive_ball_carries_count"], errors="coerce").sum()
        ratio = float(prog / total) if total > 0 else np.nan
        rows.append({"match_code": mc, "team_key": tk, "prog_ratio": ratio})

    pr = pd.DataFrame(rows).merge(m_prior, on="match_code").sort_values(["team_key", "round"])
    out: dict[str, float] = {}
    for tk, grp in pr.groupby("team_key"):
        rolled = grp["prog_ratio"].rolling(window=window, min_periods=1).mean()
        out[tk] = float(rolled.iloc[-1]) if len(rolled) else np.nan
    return out


def build_target_round_features(
    base_dir: Path,
    season: int,
    round_number: int,
    rolling_window: int = 3,
) -> pd.DataFrame:
    """Features para a rodada-alvo via rolling proxies de R1..R_{round-1}.

    Aceita partidas com status != completed (fixtures).
    """
    paths = _curated_paths(base_dir, season)
    if not paths["matches"].exists():
        raise FileNotFoundError(paths["matches"])

    matches = pd.read_csv(paths["matches"])
    fixtures = matches[matches["round"] == round_number].copy()
    if fixtures.empty:
        raise ValueError(f"Nenhum jogo encontrado para R{round_number} ({season}).")

    stats = pd.read_csv(paths["stats"]) if paths["stats"].exists() else pd.DataFrame()
    players = pd.read_csv(paths["players"]) if paths["players"].exists() else None

    team_roll = _team_rolling_proxies(stats, matches, round_number, window=rolling_window) if not stats.empty else {}
    prog_roll = _prog_ratio_rolling(players, matches, round_number, window=rolling_window)
    todate = _team_todate_strength(matches, stats, round_number) if not stats.empty else {}

    rows = []
    for _, fix in fixtures.iterrows():
        hk, ak = fix["home_team_key"], fix["away_team_key"]
        hs = team_roll.get(hk, {})
        as_ = team_roll.get(ak, {})

        h_xg = hs.get("xg", 0.9) if not pd.isna(hs.get("xg", np.nan)) else 0.9
        a_xg = as_.get("xg", 0.9) if not pd.isna(as_.get("xg", np.nan)) else 0.9
        h_shots = hs.get("shots", 10.0) or 10.0
        a_shots = as_.get("shots", 10.0) or 10.0
        h_sot = hs.get("sot", 3.5) or 3.5
        a_sot = as_.get("sot", 3.5) or 3.5
        h_poss = hs.get("poss", 50.0) or 50.0
        a_poss = as_.get("poss", 50.0) or 50.0
        h_pa = hs.get("passes_acc_pct", 75.0) or 75.0
        a_pa = as_.get("passes_acc_pct", 75.0) or 75.0
        h_co = hs.get("corners", 4.0) or 4.0
        a_co = as_.get("corners", 4.0) or 4.0
        h_pts = hs.get("pts", 1.0) or 1.0
        a_pts = as_.get("pts", 1.0) or 1.0
        h_xgc = hs.get("xg_conc", 1.0) or 1.0
        a_xgc = as_.get("xg_conc", 1.0) or 1.0

        # guards
        h_shots = max(h_shots, 0.1)
        a_shots = max(a_shots, 0.1)
        h_sot = max(h_sot, 0.1)
        a_sot = max(a_sot, 0.1)
        h_xgc = max(h_xgc, 0.1)
        a_xgc = max(a_xgc, 0.1)
        sum_xg = (h_xg + a_xg) or 1.0
        sum_sot = (h_sot + a_sot) or 1.0

        h_prog = prog_roll.get(hk, 0.30)
        a_prog = prog_roll.get(ak, 0.30)
        if pd.isna(h_prog):
            h_prog = 0.30
        if pd.isna(a_prog):
            a_prog = 0.30

        h_td = todate.get(hk, {})
        a_td = todate.get(ak, {})
        h_ppg = float(h_td.get("ppg", 1.0)) if pd.notna(h_td.get("ppg", np.nan)) else 1.0
        a_ppg = float(a_td.get("ppg", 1.0)) if pd.notna(a_td.get("ppg", np.nan)) else 1.0
        h_xg_pm = float(h_td.get("xg_pm", 1.0)) if pd.notna(h_td.get("xg_pm", np.nan)) else 1.0
        a_xg_pm = float(a_td.get("xg_pm", 1.0)) if pd.notna(a_td.get("xg_pm", np.nan)) else 1.0
        h_xgc_pm = float(h_td.get("xg_conc_pm", 1.0)) if pd.notna(h_td.get("xg_conc_pm", np.nan)) else 1.0
        a_xgc_pm = float(a_td.get("xg_conc_pm", 1.0)) if pd.notna(a_td.get("xg_conc_pm", np.nan)) else 1.0

        rows.append({
            "season": season,
            "round": round_number,
            "match_code": fix.get("match_code"),
            "match_date_utc": fix.get("match_date_utc"),
            "home_team": fix["home_team"],
            "away_team": fix["away_team"],
            "home_team_key": hk,
            "away_team_key": ak,
            "xg_h": h_xg,
            "xg_a": a_xg,
            "xg_diff": h_xg - a_xg,
            "xg_per_shot_diff": (h_xg / h_shots) - (a_xg / a_shots),
            "xg_tilt_h": h_xg / sum_xg,
            "xg_tilt_diff": (h_xg / sum_xg) - 0.5,
            "field_tilt_sot_h": h_sot / sum_sot,
            "field_tilt_sot_diff": (h_sot / sum_sot) - 0.5,
            "sot_diff": h_sot - a_sot,
            "shots_diff": h_shots - a_shots,
            "poss_diff": h_poss - a_poss,
            "rolling_xg_diff_3": h_xg - a_xg,
            "rolling_pts_diff_3": h_pts - a_pts,
            "xg_ctx_diff": (h_xg / a_xgc) - (a_xg / h_xgc),
            "passes_acc_pct_diff": h_pa - a_pa,
            "corners_diff": h_co - a_co,
            "prog_ratio_h": h_prog,
            "prog_ratio_diff": h_prog - a_prog,
            "ppg_diff_todate": h_ppg - a_ppg,
            "xg_pm_diff_todate": h_xg_pm - a_xg_pm,
            "xg_conc_pm_diff_todate": h_xgc_pm - a_xgc_pm,
        })

    return pd.DataFrame(rows)
