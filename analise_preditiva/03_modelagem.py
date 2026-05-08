#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Modelagem Preditiva — Série B 2026
Resultado de Partida (H/D/A) com validação temporal

Estratégias:
1. Cross-Season: Train 2025 → Test 2026 (produção real)
2. Walk-Forward: Expanding window por rodada 2026 (intra-temporada, sem leakage)
3. K-Fold Estratificado: 5-fold aleatório (comparação apenas)

Modelos: Baseline + Logistic Regression + Random Forest + XGBoost
"""

import os
import sys
import json
import warnings
from pathlib import Path
import datetime
import numpy as np
import pandas as pd
from collections import Counter

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, f1_score, log_loss, confusion_matrix,
    classification_report, roc_auc_score
)
from xgboost import XGBClassifier

import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

CORE_FEATURES = [
    "xg_overperformance_diff",
    "xg_overperformance_a",
    "xg_per_shot_diff",
    "xg_tilt_h",
    "xg_diff",
    "xg_overperformance_h",
    "field_tilt_sot_diff",
    "sot_diff",
    "poss_diff",
    "xg_ctx_diff",
]

FULL_FEATURES = CORE_FEATURES + ["prog_ratio_diff", "prog_ratio_h"]

OUTPUT_DIR = Path(__file__).parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_data(feature_set="core"):
    """Carrega match_features.csv e retorna X, y, feature_names."""
    csv_path = OUTPUT_DIR / "match_features.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset não encontrado: {csv_path}")

    df = pd.read_csv(csv_path)

    # Mapear target de string para números
    target_map = {"A": 0, "D": 1, "H": 2}
    df["result_encoded"] = df["result"].map(target_map)

    # Selecionar features
    features = CORE_FEATURES if feature_set == "core" else FULL_FEATURES

    # Dropna nas features + target
    df_clean = df[features + ["result_encoded", "season", "round"]].dropna()

    X = df_clean[features].values.astype(np.float32)
    y = df_clean["result_encoded"].values.astype(int)
    season_round = df_clean[["season", "round"]].values

    return X, y, features, season_round

# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_pipelines():
    """Cria 4 pipelines de modelagem."""
    return {
        "Baseline": Pipeline([
            ("scaler", StandardScaler()),
            ("model", DummyClassifier(strategy="most_frequent", random_state=42))
        ]),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(C=0.1, multi_class="multinomial",
                                        solver="lbfgs", max_iter=500, random_state=42))
        ]),
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("model", RandomForestClassifier(n_estimators=200, max_depth=5,
                                           min_samples_leaf=8, random_state=42, n_jobs=-1))
        ]),
        "XGBoost": Pipeline([
            ("scaler", StandardScaler()),
            ("model", XGBClassifier(objective="multi:softprob", max_depth=3,
                                   n_estimators=100, learning_rate=0.05,
                                   min_child_weight=5, subsample=0.8,
                                   colsample_bytree=0.8, reg_lambda=2.0,
                                   random_state=42, n_jobs=-1, verbosity=0))
        ])
    }

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════════

def run_cross_season(pipelines, X, y, season_round, feature_set="core"):
    """Split A: Train=2025 → Test=2026 (temporal realstico)."""
    mask_train = season_round[:, 0] == 2025
    mask_test = season_round[:, 0] == 2026

    X_train, y_train = X[mask_train], y[mask_train]
    X_test, y_test = X[mask_test], y[mask_test]

    results = []
    for name, pipeline in pipelines.items():
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)
        y_pred_proba = pipeline.predict_proba(X_test)

        acc = accuracy_score(y_test, y_pred)
        f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)
        f1_weighted = f1_score(y_test, y_pred, average="weighted", zero_division=0)
        ll = log_loss(y_test, y_pred_proba)

        results.append({
            "split": "Cross-Season (2025→2026)",
            "feature_set": feature_set,
            "model": name,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "accuracy": acc,
            "f1_macro": f1_macro,
            "f1_weighted": f1_weighted,
            "log_loss": ll,
        })

    return pd.DataFrame(results)

def run_walk_forward(pipelines, X, y, season_round, feature_set="core", min_rounds=3):
    """Split B: Walk-forward expanding window em 2026."""
    mask_2025 = season_round[:, 0] == 2025
    mask_2026 = season_round[:, 0] == 2026

    X_2025, y_2025 = X[mask_2025], y[mask_2025]

    df_2026 = pd.DataFrame({
        "X_idx": np.where(mask_2026)[0],
        "round": season_round[mask_2026, 1]
    })

    rounds_2026 = sorted(df_2026["round"].unique())
    test_rounds = rounds_2026[min_rounds:]  # R4 onwards (com 3+ rounds no treino)

    fold_results = []
    for test_round in test_rounds:
        mask_train_2026 = season_round[mask_2026, 1] < test_round
        mask_test_2026 = season_round[mask_2026, 1] == test_round

        X_train_2026 = X[mask_2026][mask_train_2026]
        y_train_2026 = y[mask_2026][mask_train_2026]
        X_test_2026 = X[mask_2026][mask_test_2026]
        y_test_2026 = y[mask_2026][mask_test_2026]

        X_train = np.vstack([X_2025, X_train_2026])
        y_train = np.hstack([y_2025, y_train_2026])
        X_test = X_test_2026
        y_test = y_test_2026

        for name, pipeline in pipelines.items():
            pipeline.fit(X_train, y_train)
            y_pred = pipeline.predict(X_test)
            y_pred_proba = pipeline.predict_proba(X_test)

            acc = accuracy_score(y_test, y_pred) if len(y_test) > 0 else np.nan
            f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0) if len(y_test) > 0 else np.nan

            fold_results.append({
                "split": f"Walk-Forward R{test_round}",
                "feature_set": feature_set,
                "model": name,
                "n_train": len(X_train),
                "n_test": len(X_test),
                "accuracy": acc,
                "f1_macro": f1_macro,
            })

    return pd.DataFrame(fold_results)

def run_kfold(pipelines, X, y, n_splits=5):
    """Split C: K-Fold estratificado (comparação, ignora temporal)."""
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)

    results = []
    for name, pipeline in pipelines.items():
        scores = cross_validate(
            pipeline, X, y, cv=skf,
            scoring={
                "accuracy": "accuracy",
                "f1_macro": lambda est, X, y: f1_score(y, est.predict(X), average="macro", zero_division=0),
            },
            n_jobs=-1
        )

        acc_mean = scores["test_accuracy"].mean()
        acc_std = scores["test_accuracy"].std()
        f1_mean = scores["test_f1_macro"].mean()

        results.append({
            "split": f"K-Fold {n_splits}x",
            "model": name,
            "accuracy": acc_mean,
            "accuracy_std": acc_std,
            "f1_macro": f1_mean,
        })

    return pd.DataFrame(results)

# ═══════════════════════════════════════════════════════════════════════════════
# VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def plot_model_comparison(results_cross, results_walk, results_kfold):
    """Gráfico comparativo de modelos × split."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), facecolor="#0d0d0d")

    # Plot 1: Cross-Season por metric
    for ax, metric in zip(axes, ["accuracy", "f1_macro"]):
        data = results_cross.pivot_table(values=metric, index="feature_set", columns="model")
        data.plot(kind="bar", ax=ax, width=0.7, color=[
            "#E67E22", "#3498DB", "#2ECC71", "#F39C12"
        ])
        ax.set_title(f"Cross-Season: {metric.upper()}", fontsize=11, color="white", weight="bold")
        ax.set_ylabel("Score", color="white", fontsize=10)
        ax.set_xlabel("Feature Set", color="white", fontsize=10)
        ax.set_facecolor("#1a1a1a")
        ax.tick_params(colors="white", labelsize=9)
        ax.legend(loc="lower left", fontsize=8, framealpha=0.9)
        ax.grid(axis="y", alpha=0.2)
        ax.set_xticklabels(ax.get_xticklabels(), rotation=0)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "07_model_comparison.png", dpi=120, facecolor="#0d0d0d", edgecolor="none")
    plt.close()
    logger.info("Salvo: 07_model_comparison.png")

def plot_confusion_matrices(pipelines, X_test, y_test):
    """Matrizes de confusão no split A (cross-season)."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), facecolor="#0d0d0d")
    axes = axes.flatten()

    class_names = ["A", "D", "H"]

    for idx, (name, pipeline) in enumerate(pipelines.items()):
        y_pred = pipeline.predict(X_test)
        cm = confusion_matrix(y_test, y_pred)

        ax = axes[idx]
        sns.heatmap(cm, annot=True, fmt="d", cmap="YlOrRd", ax=ax, cbar=False,
                   xticklabels=class_names, yticklabels=class_names,
                   annot_kws={"fontsize": 10, "color": "white"})
        ax.set_title(f"{name}", fontsize=11, color="white", weight="bold")
        ax.set_ylabel("True", color="white", fontsize=9)
        ax.set_xlabel("Predicted", color="white", fontsize=9)
        ax.set_facecolor("#1a1a1a")
        ax.tick_params(colors="white", labelsize=8)

    axes[-1].remove()  # Remover último subplot vazio
    plt.suptitle("Confusion Matrices — Cross-Season (Train 2025 → Test 2026)",
                 fontsize=12, color="white", weight="bold", y=1.00)
    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "08_confusion_matrices.png", dpi=120, facecolor="#0d0d0d", edgecolor="none")
    plt.close()
    logger.info("Salvo: 08_confusion_matrices.png")

def plot_xgb_importance(pipeline, feature_names):
    """Feature importance do XGBoost."""
    model = pipeline.named_steps["model"]
    importances = model.feature_importances_

    df_imp = pd.DataFrame({
        "feature": feature_names,
        "importance": importances
    }).sort_values("importance", ascending=True).tail(10)

    fig, ax = plt.subplots(figsize=(10, 6), facecolor="#0d0d0d")
    ax.barh(df_imp["feature"], df_imp["importance"], color="#F39C12", edgecolor="white", linewidth=0.5)
    ax.set_title("XGBoost Feature Importance", fontsize=12, color="white", weight="bold")
    ax.set_xlabel("Gain", color="white", fontsize=10)
    ax.set_facecolor("#1a1a1a")
    ax.tick_params(colors="white", labelsize=9)
    ax.grid(axis="x", alpha=0.2)

    plt.tight_layout()
    fig.savefig(OUTPUT_DIR / "09_xgboost_importance.png", dpi=120, facecolor="#0d0d0d", edgecolor="none")
    plt.close()
    logger.info("Salvo: 09_xgboost_importance.png")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    logger.info("\n" + "="*80)
    logger.info("MODELAGEM PREDITIVA — SÉRIE B 2026")
    logger.info("="*80 + "\n")

    all_results = []
    pipelines_for_viz = None
    X_test_viz, y_test_viz = None, None

    for feature_set, features_list in [("core", CORE_FEATURES), ("full_2026", FULL_FEATURES)]:
        logger.info(f"\n--- Feature Set: {feature_set.upper()} ---")

        # Carrega dados
        X, y, selected_features, season_round = load_data(feature_set)
        logger.info(f"Dataset: {len(X)} matches, {len(selected_features)} features")
        logger.info(f"Target distribution: {dict(zip(*np.unique(y, return_counts=True)))}")

        # Build pipelines
        pipelines = build_pipelines()

        # Verificar se há dados de 2025 para cross-season
        has_2025 = (season_round[:, 0] == 2025).sum() > 0
        has_2026 = (season_round[:, 0] == 2026).sum() > 0

        # SPLIT A: Cross-Season (apenas se tiver 2025 E 2026)
        if has_2025 and has_2026:
            logger.info("\n  ├─ Split A: Cross-Season (Train 2025 → Test 2026)")
            results_cs = run_cross_season(pipelines, X, y, season_round, feature_set)
            all_results.append(results_cs)
            for _, row in results_cs.iterrows():
                logger.info(f"    {row['model']:20s} | Acc={row['accuracy']:.3f} | F1-M={row['f1_macro']:.3f} | LL={row['log_loss']:.3f}")
        else:
            logger.info(f"\n  ├─ Split A: SKIPPED (apenas 2026 disponível para {feature_set})")

        # SPLIT B: Walk-Forward
        if has_2026:
            logger.info("\n  ├─ Split B: Walk-Forward (2026 R4→R7)")
            results_wf = run_walk_forward(pipelines, X, y, season_round, feature_set)
            if len(results_wf) > 0:
                for fold_name in results_wf["split"].unique():
                    fold_data = results_wf[results_wf["split"] == fold_name]
                    logger.info(f"    {fold_name}:")
                    for _, row in fold_data.iterrows():
                        logger.info(f"      {row['model']:20s} | Acc={row['accuracy']:.3f}")
                all_results.append(results_wf)

        # SPLIT C: K-Fold (apenas uma vez)
        if feature_set == "core":
            logger.info("\n  └─ Split C: K-Fold 5x (COMPARAÇÃO APENAS — ignora temporal)")
            results_kf = run_kfold(pipelines, X, y)
            for _, row in results_kf.iterrows():
                logger.info(f"    {row['model']:20s} | Acc={row['accuracy']:.3f}±{row['accuracy_std']:.3f}")
            all_results.append(results_kf)

            # Guardar para visualização
            pipelines_for_viz = pipelines
            mask_test = season_round[:, 0] == 2026
            X_test_viz = X[mask_test]
            y_test_viz = y[mask_test]

    # Consolidar resultados
    df_results = pd.concat(all_results, ignore_index=True)
    csv_path = OUTPUT_DIR / "model_results.csv"
    df_results.to_csv(csv_path, index=False)
    logger.info(f"\n✓ Resultados salvos: {csv_path}")

    # Visualizações
    results_cs_all = pd.concat([r for r in all_results if "Cross-Season" in r["split"].iloc[0] if "split" in r.columns])
    plot_model_comparison(results_cs_all, pd.DataFrame(), pd.DataFrame())

    if pipelines_for_viz is not None and X_test_viz is not None:
        # Treinar novamente no split A com core features para vizualização
        X_train, y_train, _, season_round_train = load_data("core")
        mask_train = season_round_train[:, 0] == 2025
        X_train = X_train[mask_train]
        y_train = y_train[mask_train]

        for pipeline in pipelines_for_viz.values():
            pipeline.fit(X_train, y_train)

        plot_confusion_matrices(pipelines_for_viz, X_test_viz, y_test_viz)
        plot_xgb_importance(pipelines_for_viz["XGBoost"], CORE_FEATURES)

    logger.info("\n" + "="*80)
    logger.info("✓ Modelagem completa")
    logger.info("="*80 + "\n")

if __name__ == "__main__":
    main()
