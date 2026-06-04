"""Backtest GBM v2 — tuning de hiperparâmetros + ensemble LR+GBM.

Modelos:
  - lr_baseline           — referência
  - gbm_small             — num_leaves=7, n_est=150 (menos capacidade)
  - gbm_small_sig         — small + sigmoid
  - gbm_tiny              — num_leaves=5, n_est=100, lr=0.03
  - gbm_tiny_sig
  - xgb_small             — XGBoost equivalente
  - xgb_small_sig
  - ensemble_lr_gbm_sig   — média de probs LR + gbm_sigmoid
  - ensemble_lr_gbm_small — média de probs LR + gbm_small_sig
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from lightgbm import LGBMClassifier
from xgboost import XGBClassifier

from src.features.match_features import build_match_features
from src.predict.feature_builder import (
    FULL_FEATURES,
    build_target_round_features,
)

BASE_DIR = Path(__file__).parent
CURATED = BASE_DIR / "data" / "curated"


def _make_lr():
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=0.1, max_iter=500, random_state=42)),
    ])


def _lgbm(num_leaves=15, n_estimators=200, learning_rate=0.05, min_data_in_leaf=20,
          reg_alpha=0.1, reg_lambda=0.1):
    return LGBMClassifier(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        num_leaves=num_leaves,
        min_data_in_leaf=min_data_in_leaf,
        feature_fraction=0.85,
        bagging_fraction=0.85,
        bagging_freq=5,
        reg_alpha=reg_alpha,
        reg_lambda=reg_lambda,
        objective="multiclass",
        num_class=3,
        random_state=42,
        verbose=-1,
        n_jobs=1,
    )


def _xgb(max_depth=4, n_estimators=200, learning_rate=0.05):
    return XGBClassifier(
        n_estimators=n_estimators,
        learning_rate=learning_rate,
        max_depth=max_depth,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=0.5,
        objective="multi:softprob",
        num_class=3,
        random_state=42,
        verbosity=0,
        n_jobs=1,
        eval_metric="mlogloss",
    )


class EnsembleAvg(BaseEstimator, ClassifierMixin):
    """Ensemble por média simples de predict_proba."""

    def __init__(self, models):
        self.models = models

    def fit(self, X, y):
        self.fitted_ = [m for m in self.models]
        for m in self.fitted_:
            m.fit(X, y)
        self.classes_ = self.fitted_[0].classes_
        return self

    def predict_proba(self, X):
        probas = [m.predict_proba(X) for m in self.fitted_]
        return np.mean(probas, axis=0)

    def predict(self, X):
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


MODELS = {
    "lr_baseline":
        lambda: _make_lr(),
    "gbm_small":
        lambda: _lgbm(num_leaves=7, n_estimators=150, min_data_in_leaf=15),
    "gbm_small_sig":
        lambda: CalibratedClassifierCV(
            _lgbm(num_leaves=7, n_estimators=150, min_data_in_leaf=15),
            method="sigmoid", cv=3),
    "gbm_tiny":
        lambda: _lgbm(num_leaves=5, n_estimators=100, learning_rate=0.03,
                      min_data_in_leaf=10, reg_alpha=0.2, reg_lambda=0.5),
    "gbm_tiny_sig":
        lambda: CalibratedClassifierCV(
            _lgbm(num_leaves=5, n_estimators=100, learning_rate=0.03,
                  min_data_in_leaf=10, reg_alpha=0.2, reg_lambda=0.5),
            method="sigmoid", cv=3),
    "xgb_small":
        lambda: _xgb(max_depth=3, n_estimators=150),
    "xgb_small_sig":
        lambda: CalibratedClassifierCV(
            _xgb(max_depth=3, n_estimators=150),
            method="sigmoid", cv=3),
    "ensemble_lr+gbm_small_sig":
        lambda: EnsembleAvg([
            _make_lr(),
            CalibratedClassifierCV(
                _lgbm(num_leaves=7, n_estimators=150, min_data_in_leaf=15),
                method="sigmoid", cv=3),
        ]),
    "ensemble_lr+gbm_tiny_sig":
        lambda: EnsembleAvg([
            _make_lr(),
            CalibratedClassifierCV(
                _lgbm(num_leaves=5, n_estimators=100, learning_rate=0.03,
                      min_data_in_leaf=10, reg_alpha=0.2, reg_lambda=0.5),
                method="sigmoid", cv=3),
        ]),
    "ensemble_lr+xgb_sig":
        lambda: EnsembleAvg([
            _make_lr(),
            CalibratedClassifierCV(
                _xgb(max_depth=3, n_estimators=150),
                method="sigmoid", cv=3),
        ]),
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


def _eval_model(name: str, model_factory, target_rounds, matches_2026):
    cum_correct = 0
    cum_total = 0
    brier_sum = 0.0
    prob_real_sum = 0.0
    n_d_pred = 0
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
                m.get("home_score"), m.get("away_score"))
        target_df["real"] = target_df["match_code"].map(real_map)
        valid = target_df.dropna(subset=["real"])
        cum_correct += int((valid["pred"] == valid["real"]).sum())
        cum_total += len(valid)
        n_d_pred += int((valid["pred"] == "D").sum())
        y_real_enc = valid["real"].map({"A": 0, "D": 1, "H": 2}).values
        proba_v = proba[:len(valid)]
        oh = np.zeros_like(proba_v)
        oh[np.arange(len(y_real_enc)), y_real_enc] = 1.0
        brier_sum += float(np.sum(np.sum((proba_v - oh) ** 2, axis=1)))
        prob_real_sum += float(np.sum(proba_v[np.arange(len(y_real_enc)), y_real_enc]))
    return {
        "model": name,
        "cum_acc": cum_correct / cum_total if cum_total else 0.0,
        "cum_correct": cum_correct,
        "cum_total": cum_total,
        "brier": brier_sum / cum_total if cum_total else 0.0,
        "mean_prob_real": prob_real_sum / cum_total if cum_total else 0.0,
        "n_draws": n_d_pred,
    }


def main():
    matches_2026, _, _ = _load_season(2026)
    completed_rounds = sorted(
        matches_2026[matches_2026["status"] == "completed"]["round"].astype(int).unique()
    )
    target_rounds = [r for r in completed_rounds if r >= 3]
    print(f"Backtest GBM v2 — rodadas: {target_rounds}")
    print(f"Modelos: {list(MODELS.keys())}\n")
    rows = []
    for name, factory in MODELS.items():
        res = _eval_model(name, factory, target_rounds, matches_2026)
        print(
            f"{name:30s}  cum_acc={res['cum_acc']:.1%} "
            f"({res['cum_correct']}/{res['cum_total']})  "
            f"brier={res['brier']:.3f}  p_real={res['mean_prob_real']:.3f}  "
            f"emp={res['n_draws']}"
        )
        rows.append(res)
    out = BASE_DIR / "data" / "predictions" / "serie_b_2026" / "backtest_gbm_v2.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\nSalvo: {out}")
    print("\nBaseline 'sempre H': 40.0%  ·  aleatório: 33.3%")


if __name__ == "__main__":
    main()
