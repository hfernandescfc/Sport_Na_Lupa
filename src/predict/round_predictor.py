"""Treina ensemble (LR + LGBM-sigmoid) sobre todo o histórico disponível e prediz uma rodada.

Output em data/predictions/serie_b_{season}/:
    round_{N}.csv               — previsões (probabilidades por classe)
    round_{N}.json              — metadata da execução (n_train, train_acc, features, timestamp)
    round_{N}.md                — relatório textual

O pool de treino é sempre regerado on-the-fly via feature_builder.build_training_pool,
então qualquer rodada recém-sincronizada já entra no treino da próxima execução.

Arquitetura do modelo (Frente 3 — definida pelo backtest walk-forward R3-R9):
    base_lr  = StandardScaler + LogisticRegression(C=0.1)
    base_gbm = LGBMClassifier(num_leaves=7, n_est=150, min_data_in_leaf=15)
               + CalibratedClassifierCV(method="sigmoid", cv=3)
    ensemble = média simples de predict_proba das duas bases

Resultados walk-forward (R3-R9, 2026 — 72 partidas, vs LR puro):
    LR sozinho       → acc 40.3% · brier 0.747
    LGBM+sigmoid     → acc 38.9% · brier 0.673
    Ensemble LR+GBM  → acc 40.3% · brier 0.689   ← produção
Mesma acurácia, ~8% menos erro de calibração. Os "empates previstos" caem de
23 → 18, mais alinhados com a base real (~30% de empates históricos).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

try:
    from lightgbm import LGBMClassifier
    _LGBM_AVAILABLE = True
except ImportError:  # pragma: no cover
    _LGBM_AVAILABLE = False

from src.predict.feature_builder import (
    FULL_FEATURES,
    build_target_round_features,
    build_training_pool,
)


MODEL_VERSION = "ens_lr_gbm_v1"
LR_PARAMS = {"C": 0.1, "max_iter": 500, "random_state": 42}
GBM_PARAMS = {
    "n_estimators": 150,
    "learning_rate": 0.05,
    "num_leaves": 7,
    "min_data_in_leaf": 15,
    "feature_fraction": 0.85,
    "bagging_fraction": 0.85,
    "bagging_freq": 5,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "objective": "multiclass",
    "num_class": 3,
    "random_state": 42,
    "verbose": -1,
    "n_jobs": 1,
}
CALIB_METHOD = "sigmoid"
CALIB_CV = 3


class _ProbaEnsemble(BaseEstimator, ClassifierMixin):
    """Ensemble por média simples de predict_proba.

    Não é um stacking — só promedia. Robusto para datasets pequenos onde
    stacking facilmente overfita.
    """

    def __init__(self, models):
        self.models = models

    def fit(self, X, y):
        self.fitted_ = list(self.models)
        for m in self.fitted_:
            m.fit(X, y)
        self.classes_ = self.fitted_[0].classes_
        return self

    def predict_proba(self, X):
        return np.mean([m.predict_proba(X) for m in self.fitted_], axis=0)

    def predict(self, X):
        return self.classes_[np.argmax(self.predict_proba(X), axis=1)]


def _build_lr() -> Pipeline:
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(**LR_PARAMS)),
    ])


def _build_gbm():
    if not _LGBM_AVAILABLE:
        raise ImportError(
            "lightgbm não está instalado — "
            "pip install lightgbm para usar o ensemble v1"
        )
    base = LGBMClassifier(**GBM_PARAMS)
    return CalibratedClassifierCV(base, method=CALIB_METHOD, cv=CALIB_CV)


def _build_model():
    """Retorna o modelo de produção. Fallback para LR se lgbm indisponível."""
    if not _LGBM_AVAILABLE:
        return _build_lr()
    return _ProbaEnsemble([_build_lr(), _build_gbm()])


def _detect_next_round(base_dir: Path, season: int) -> int | None:
    """Próxima rodada a prever = menor rodada com pelo menos um jogo NÃO concluído."""
    p = base_dir / "data" / "curated" / f"serie_b_{season}" / "matches.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p)
    if df.empty:
        return None
    for r in sorted(df["round"].dropna().unique().astype(int)):
        sub = df[df["round"] == r]
        if (sub["status"] != "completed").any():
            return int(r)
    return None


def predict_round(
    base_dir: Path,
    season: int,
    round_number: int | None = None,
    historical_seasons: tuple[int, ...] = (2025,),
    output_dir: Path | None = None,
    logger=None,
) -> dict:
    """Treina ensemble no pool completo (histórico + rodadas concluídas) e prediz round_number.

    Retorna dict com paths dos artefatos gerados + métricas.
    """
    def _log(msg: str):
        if logger is not None:
            logger.info(msg)

    target = round_number or _detect_next_round(base_dir, season)
    if target is None:
        raise RuntimeError(f"Não foi possível detectar rodada-alvo para {season}.")
    _log(f"[predict-round] rodada-alvo: R{target} ({season})")

    # 1. Pool de treino — TODAS as rodadas concluídas até agora
    pool = build_training_pool(base_dir, season, historical_seasons=historical_seasons)
    pool_current = pool[pool["season"] == season]
    rounds_in_pool = sorted(pool_current["round"].dropna().unique().astype(int).tolist())
    _log(
        f"[predict-round] pool de treino: {len(pool)} partidas — "
        f"{historical_seasons} ({len(pool) - len(pool_current)}) + "
        f"R{rounds_in_pool[0]}-R{rounds_in_pool[-1]} de {season} ({len(pool_current)})"
        if rounds_in_pool
        else f"[predict-round] pool de treino: {len(pool)} partidas"
    )

    X_train = pool[FULL_FEATURES].values
    y_train = pool["result_encoded"].values

    model = _build_model()
    model.fit(X_train, y_train)
    train_acc = float(np.mean(model.predict(X_train) == y_train))
    _log(f"[predict-round] modelo treinado — train_acc={train_acc:.1%}")

    # 2. Features da rodada-alvo
    target_df = build_target_round_features(base_dir, season, target)
    _log(f"[predict-round] {len(target_df)} jogos em R{target}")

    X_pred = target_df[FULL_FEATURES].values
    proba = model.predict_proba(X_pred)

    results = pd.DataFrame({
        "match_code": target_df.get("match_code"),
        "match_date_utc": target_df.get("match_date_utc"),
        "home_team": target_df["home_team"].values,
        "away_team": target_df["away_team"].values,
        "home_team_key": target_df["home_team_key"].values,
        "away_team_key": target_df["away_team_key"].values,
        "prob_away": proba[:, 0],
        "prob_draw": proba[:, 1],
        "prob_home": proba[:, 2],
    })
    pred_classes = np.argmax(proba, axis=1)
    label_map = {0: "A", 1: "D", 2: "H"}
    results["predicted_result"] = [label_map[c] for c in pred_classes]
    results["max_probability"] = np.max(proba, axis=1)

    # 3. Persistir
    out_dir = output_dir or (base_dir / "data" / "predictions" / f"serie_b_{season}")
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"round_{target}.csv"
    json_path = out_dir / f"round_{target}.json"
    md_path = out_dir / f"round_{target}.md"

    results.to_csv(csv_path, index=False)

    n_prematch = 14
    n_strength = 2
    n_player = 2

    metadata = {
        "season": season,
        "round": target,
        "model_version": MODEL_VERSION,
        "model_architecture": (
            "ensemble: LR(C=0.1) + LGBM(num_leaves=7, n_est=150) "
            "sigmoid-calibrated, mean of predict_proba"
            if _LGBM_AVAILABLE
            else "fallback: LR only (lightgbm não disponível)"
        ),
        "lr_params": LR_PARAMS,
        "gbm_params": GBM_PARAMS if _LGBM_AVAILABLE else None,
        "calibration": {"method": CALIB_METHOD, "cv": CALIB_CV} if _LGBM_AVAILABLE else None,
        "features": FULL_FEATURES,
        "n_features": len(FULL_FEATURES),
        "n_features_breakdown": {
            "prematch": n_prematch,
            "strength_todate": n_strength,
            "player": n_player,
        },
        "n_train": len(pool),
        "n_train_historical": int(len(pool) - len(pool_current)),
        "n_train_current_season": int(len(pool_current)),
        "current_season_rounds_in_training": rounds_in_pool,
        "train_accuracy": train_acc,
        "n_predicted": len(results),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    _write_report(md_path, results, metadata)
    _log(f"[predict-round] previsões salvas em {csv_path.relative_to(base_dir)}")

    return {
        "csv": csv_path,
        "json": json_path,
        "md": md_path,
        "metadata": metadata,
        "predictions": results,
    }


def _write_report(path: Path, results: pd.DataFrame, meta: dict) -> None:
    rounds = meta["current_season_rounds_in_training"]
    train_line = (
        f"**Treino:** {meta['n_train']} partidas — "
        f"{meta['n_train_historical']} histórico + "
        f"{meta['n_train_current_season']} de {meta['season']} "
        f"(R{rounds[0]}–R{rounds[-1]})"
        if rounds
        else f"**Treino:** {meta['n_train']} partidas"
    )
    nb = meta["n_features_breakdown"]
    lines = [
        f"# Previsões Rodada {meta['round']} — Série B {meta['season']}",
        "",
        f"**Gerado em:** {meta['generated_at']}",
        f"**Modelo:** {meta['model_version']} — {meta['model_architecture']}",
        train_line,
        f"**Acurácia de treino:** {meta['train_accuracy']:.1%}",
        f"**Features:** {meta['n_features']} "
        f"({nb['prematch']} pré-match + {nb['strength_todate']} força + {nb['player']} jogadores)",
        "",
        "---",
        "",
        "## Previsões",
        "",
        "| # | Partida | P(Mandante) | P(Empate) | P(Visitante) | Previsão |",
        "|---|---|---|---|---|---|",
    ]
    label_full = {"H": "Mandante", "D": "Empate", "A": "Visitante"}
    for i, row in results.iterrows():
        lines.append(
            f"| {i + 1} | {row['home_team']} × {row['away_team']} | "
            f"{row['prob_home']:.1%} | {row['prob_draw']:.1%} | {row['prob_away']:.1%} | "
            f"**{label_full[row['predicted_result']]}** ({row['max_probability']:.1%}) |"
        )
    path.write_text("\n".join(lines), encoding="utf-8")
