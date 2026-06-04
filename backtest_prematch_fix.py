"""Backtest walk-forward para validar o fix de pré-jogo.

Para cada R em [3..9] de 2026:
  pool_treino = 2025 completo + 2026[R<target]
  treina LR (mesmo C, mesmas features que producao)
  prediz R usando build_target_round_features
  compara vs resultado real

Sem leak temporal — cada R é predita apenas com info anterior a ela.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.features.match_features import build_match_features
from src.predict.feature_builder import (
    FULL_FEATURES,
    build_target_round_features,
)

BASE_DIR = Path(__file__).parent
CURATED = BASE_DIR / "data" / "curated"


def _load_season(season: int):
    folder = CURATED / f"serie_b_{season}"
    matches = pd.read_csv(folder / "matches.csv")
    stats = pd.read_csv(folder / "team_match_stats.csv")
    p_path = folder / "player_match_stats.csv"
    players = pd.read_csv(p_path) if p_path.exists() else None
    return matches, stats, players


def _result_from_score(h, a):
    if pd.isna(h) or pd.isna(a):
        return None
    if h > a:
        return "H"
    if h < a:
        return "A"
    return "D"


def _train_pool_up_to(round_cap: int) -> pd.DataFrame:
    """Pool = 2025 inteiro + 2026 com round < round_cap."""
    frames = []
    for season in (2025, 2026):
        matches, stats, players = _load_season(season)
        if season == 2026:
            matches = matches[matches["round"].astype(float) < round_cap]
            stats = stats[stats["match_code"].isin(matches["match_code"])]
            if players is not None:
                players = players[players["match_code"].isin(matches["match_code"])]
        df = build_match_features(matches, stats, players=players, rolling_window=3)
        if df is None or df.empty:
            continue
        df["season"] = season
        frames.append(df)
    pool = pd.concat(frames, ignore_index=True)
    # imputação de prog_ratio + to-date strength histórico → mediana de 2026 atual
    current = pool[pool["season"] == 2026]
    impute_cols = (
        "prog_ratio_h", "prog_ratio_diff",
        "ppg_diff_todate", "xg_pm_diff_todate", "xg_conc_pm_diff_todate",
    )
    for col in impute_cols:
        if col in pool.columns:
            med = pd.to_numeric(current[col], errors="coerce").median()
            if pd.notna(med):
                pool[col] = pool[col].fillna(med)
    pool = pool.dropna(subset=FULL_FEATURES + ["result"])
    pool["result_encoded"] = pool["result"].map({"A": 0, "D": 1, "H": 2})
    return pool


def main():
    matches_2026, _, _ = _load_season(2026)
    completed_rounds = sorted(
        matches_2026[matches_2026["status"] == "completed"]["round"].astype(int).unique()
    )
    target_rounds = [r for r in completed_rounds if r >= 3]
    print(f"Backtest cross-season — rodadas testadas: {target_rounds}")
    print(f"Features ({len(FULL_FEATURES)}): {FULL_FEATURES}\n")

    rows = []
    cumulative_correct = 0
    cumulative_total = 0

    for R in target_rounds:
        pool = _train_pool_up_to(R)
        n_train = len(pool)
        n_2025 = int((pool["season"] == 2025).sum())
        n_2026 = int((pool["season"] == 2026).sum())

        X = pool[FULL_FEATURES].values
        y = pool["result_encoded"].values
        pipe = Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(C=0.1, max_iter=500, random_state=42)),
        ])
        pipe.fit(X, y)
        train_acc = float(np.mean(pipe.predict(X) == y))

        target_df = build_target_round_features(BASE_DIR, 2026, R)
        Xp = target_df[FULL_FEATURES].values
        proba = pipe.predict_proba(Xp)
        pred_class = np.argmax(proba, axis=1)
        label_map = {0: "A", 1: "D", 2: "H"}
        target_df["pred"] = [label_map[c] for c in pred_class]
        target_df["max_prob"] = np.max(proba, axis=1)

        # Real outcome via matches.csv
        real_map = {}
        for _, m in matches_2026[matches_2026["round"] == R].iterrows():
            real_map[m["match_code"]] = _result_from_score(
                m.get("home_score"), m.get("away_score")
            )
        target_df["real"] = target_df["match_code"].map(real_map)
        valid = target_df.dropna(subset=["real"])
        correct = int((valid["pred"] == valid["real"]).sum())
        total = len(valid)
        acc = correct / total if total else 0.0
        cumulative_correct += correct
        cumulative_total += total
        cum_acc = cumulative_correct / cumulative_total if cumulative_total else 0.0

        # Brier multiclass
        y_real_enc = valid["real"].map({"A": 0, "D": 1, "H": 2}).values
        proba_valid = proba[: len(valid)]
        oh = np.zeros_like(proba_valid)
        oh[np.arange(len(y_real_enc)), y_real_enc] = 1.0
        brier = float(np.mean(np.sum((proba_valid - oh) ** 2, axis=1)))

        # Probabilidade média na classe real
        mean_prob_real = float(np.mean(proba_valid[np.arange(len(y_real_enc)), y_real_enc]))

        rows.append({
            "round": R,
            "n_train": n_train,
            "n_train_2025": n_2025,
            "n_train_2026": n_2026,
            "train_acc": train_acc,
            "n_predicted": total,
            "correct": correct,
            "round_acc": acc,
            "cumulative_acc": cum_acc,
            "mean_prob_real": mean_prob_real,
            "brier": brier,
        })

        print(
            f"R{R}: train n={n_train} (2025={n_2025}, 2026={n_2026}) "
            f"train_acc={train_acc:.1%}  →  R{R} acc={acc:.1%} "
            f"({correct}/{total})  cum={cum_acc:.1%}  "
            f"mean_p_real={mean_prob_real:.3f}  brier={brier:.3f}"
        )

    df = pd.DataFrame(rows)
    out = BASE_DIR / "data" / "predictions" / "serie_b_2026" / "backtest_walk_forward.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"\nSalvo: {out}")
    print(f"\nResumo final: cum_acc = {df['cumulative_acc'].iloc[-1]:.1%} "
          f"({cumulative_correct}/{cumulative_total})")
    print(f"Baseline 'sempre H': {_baseline_always_home(matches_2026, target_rounds):.1%}")
    print(f"Baseline aleatório: 33.3%")


def _baseline_always_home(matches, rounds) -> float:
    sub = matches[matches["round"].astype(int).isin(rounds)]
    sub = sub[sub["status"] == "completed"].copy()
    sub["real"] = sub.apply(
        lambda r: _result_from_score(r.get("home_score"), r.get("away_score")), axis=1
    )
    sub = sub.dropna(subset=["real"])
    return float((sub["real"] == "H").mean())


if __name__ == "__main__":
    main()
