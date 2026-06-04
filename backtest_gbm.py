"""Backtest walk-forward — Frente 3: LightGBM + isotonic calibration vs LR.

Para cada R em [3..9] de 2026:
  pool_treino = 2025 completo + 2026[R<target]
  treina vários modelos com mesma feature set (FULL_FEATURES de frente 2)
  prediz R usando build_target_round_features
  compara vs resultado real

Modelos testados:
  - lr_baseline       — LR C=0.1 (frente 2 atual)
  - gbm_raw           — LGBMClassifier sem calibração
  - gbm_balanced      — LGBM + class_weight='balanced' (boost no D)
  - gbm_isotonic      — LGBM + CalibratedClassifierCV(method='isotonic', cv=3)
  - gbm_sigmoid       — LGBM + CalibratedClassifierCV(method='sigmoid', cv=3)
  - gbm_balanced_iso  — LGBM balanced + isotonic
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from lightgbm import LGBMClassifier
except ImportError:
    print("ERROR: lightgbm não instalado. pip install lightgbm")
    sys.exit(1)

from src.features.match_features import build_match_features
from src.predict.feature_builder import (
    FULL_FEATURES,
    build_target_round_features,
)

BASE_DIR = Path(__file__).parent
CURATED = BASE_DIR / "data" / "curated"


# --- LGBM hyperparams: conservadores para ~230 partidas ----------------------
LGBM_PARAMS = dict(
    n_estimators=200,
    learning_rate=0.05,
    num_leaves=15,
    min_data_in_leaf=20,
    feature_fraction=0.85,
    bagging_fraction=0.85,
    bagging_freq=5,
    reg_alpha=0.1,
    reg_lambda=0.1,
    objective="multiclass",
    num_class=3,
    random_state=42,
    verbose=-1,
    n_jobs=1,
)


def _make_lr():
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=0.1, max_iter=500, random_state=42)),
    ])


def _make_gbm(balanced: bool = False, calibration: str | None = None):
    """Cria pipeline GBM com opção de class_weight e calibração."""
    params = dict(LGBM_PARAMS)
    if balanced:
        params["class_weight"] = "balanced"
    base = LGBMClassifier(**params)
    if calibration is None:
        return base
    return CalibratedClassifierCV(base, method=calibration, cv=3)


MODELS = {
    "lr_baseline":       _make_lr,
    "gbm_raw":           lambda: _make_gbm(balanced=False, calibration=None),
    "gbm_balanced":      lambda: _make_gbm(balanced=True,  calibration=None),
    "gbm_isotonic":      lambda: _make_gbm(balanced=False, calibration="isotonic"),
    "gbm_sigmoid":       lambda: _make_gbm(balanced=False, calibration="sigmoid"),
    "gbm_balanced_iso":  lambda: _make_gbm(balanced=True,  calibration="isotonic"),
    "gbm_balanced_sig":  lambda: _make_gbm(balanced=True,  calibration="sigmoid"),
}


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


def _eval_model(name: str, model_factory, target_rounds: list[int], matches_2026):
    """Roda walk-forward para um modelo. Retorna dict com métricas agregadas."""
    cum_correct = 0
    cum_total = 0
    brier_sum = 0.0
    prob_real_sum = 0.0
    n_d_predicted = 0  # quantas vezes previu empate
    per_round = []

    for R in target_rounds:
        pool = _train_pool_up_to(R)
        X = pool[FULL_FEATURES].values
        y = pool["result_encoded"].values

        model = model_factory()
        model.fit(X, y)

        target_df = build_target_round_features(BASE_DIR, 2026, R)
        Xp = target_df[FULL_FEATURES].values
        proba = model.predict_proba(Xp)
        pred_class = np.argmax(proba, axis=1)
        label_map = {0: "A", 1: "D", 2: "H"}
        target_df = target_df.copy()
        target_df["pred"] = [label_map[c] for c in pred_class]

        real_map = {}
        for _, m in matches_2026[matches_2026["round"] == R].iterrows():
            real_map[m["match_code"]] = _result_from_score(
                m.get("home_score"), m.get("away_score")
            )
        target_df["real"] = target_df["match_code"].map(real_map)
        valid = target_df.dropna(subset=["real"])
        correct = int((valid["pred"] == valid["real"]).sum())
        total = len(valid)
        n_d_predicted += int((valid["pred"] == "D").sum())

        # Brier + prob média na classe real
        y_real_enc = valid["real"].map({"A": 0, "D": 1, "H": 2}).values
        proba_valid = proba[: len(valid)]
        oh = np.zeros_like(proba_valid)
        oh[np.arange(len(y_real_enc)), y_real_enc] = 1.0
        brier_round = float(np.sum(np.sum((proba_valid - oh) ** 2, axis=1)))
        mp_round = float(np.sum(proba_valid[np.arange(len(y_real_enc)), y_real_enc]))

        cum_correct += correct
        cum_total += total
        brier_sum += brier_round
        prob_real_sum += mp_round

        per_round.append({
            "round": R,
            "n": total,
            "correct": correct,
            "acc": correct / total if total else 0.0,
            "mean_prob_real": mp_round / total if total else 0.0,
            "brier": brier_round / total if total else 0.0,
        })

    return {
        "model": name,
        "cum_acc": cum_correct / cum_total if cum_total else 0.0,
        "cum_correct": cum_correct,
        "cum_total": cum_total,
        "mean_prob_real": prob_real_sum / cum_total if cum_total else 0.0,
        "brier": brier_sum / cum_total if cum_total else 0.0,
        "n_d_predicted": n_d_predicted,
        "per_round": per_round,
    }


def main():
    matches_2026, _, _ = _load_season(2026)
    completed_rounds = sorted(
        matches_2026[matches_2026["status"] == "completed"]["round"].astype(int).unique()
    )
    target_rounds = [r for r in completed_rounds if r >= 3]
    print(f"Backtest GBM — rodadas testadas: {target_rounds}")
    print(f"Features ({len(FULL_FEATURES)}): {FULL_FEATURES}\n")
    print(f"Modelos comparados: {list(MODELS.keys())}\n")

    summary_rows = []
    for name, factory in MODELS.items():
        res = _eval_model(name, factory, target_rounds, matches_2026)
        print(
            f"{name:22s}  cum_acc={res['cum_acc']:.1%} ({res['cum_correct']}/{res['cum_total']})  "
            f"brier={res['brier']:.3f}  p_real={res['mean_prob_real']:.3f}  "
            f"empates_preditos={res['n_d_predicted']}"
        )
        summary_rows.append({
            "model": name,
            "cum_acc": res["cum_acc"],
            "cum_correct": res["cum_correct"],
            "cum_total": res["cum_total"],
            "mean_prob_real": res["mean_prob_real"],
            "brier": res["brier"],
            "n_draws_predicted": res["n_d_predicted"],
        })

    out = BASE_DIR / "data" / "predictions" / "serie_b_2026" / "backtest_gbm_comparison.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(summary_rows).to_csv(out, index=False)
    print(f"\nSalvo: {out}")

    print(f"\nBaseline 'sempre H': "
          f"{_baseline_always_home(matches_2026, target_rounds):.1%}")
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
