"""Comparação Train vs Test — Detectar overfitting em cada split."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, log_loss

# Features pré-match (sem target leakage)
PREMATCH_CORE = [
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff", "rolling_xg_diff_3",
    "rolling_pts_diff_3", "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
]

def load_data(feature_set="core"):
    """Carrega CSV, trata NaN, retorna X, y, season_round."""
    csv_path = Path("analise_preditiva/outputs/match_features.csv")
    df = pd.read_csv(csv_path)

    # Remover linhas com NaN
    features = PREMATCH_CORE
    df = df.dropna(subset=features + ["result"])

    # Encode result: A=0, D=1, H=2
    result_map = {"A": 0, "D": 1, "H": 2}
    y = df["result"].map(result_map).values
    X = df[features].values
    season_round = df[["season", "round"]].values

    return X, y, features, season_round

def build_pipelines():
    """Cria pipelines com StandardScaler + modelo."""
    return {
        "Baseline": Pipeline([
            ("scaler", StandardScaler()),
            ("model", DummyClassifier(strategy="most_frequent")),
        ]),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(C=0.1, multi_class="multinomial", max_iter=500)),
        ]),
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("model", RandomForestClassifier(n_estimators=200, max_depth=5, min_samples_leaf=8, random_state=42)),
        ]),
        "XGBoost": Pipeline([
            ("scaler", StandardScaler()),
            ("model", XGBClassifier(
                objective="multi:softprob", max_depth=3, n_estimators=100,
                learning_rate=0.05, min_child_weight=5, subsample=0.8,
                colsample_bytree=0.8, reg_lambda=2.0, random_state=42,
            )),
        ]),
    }

def run_cross_season_with_train_test(pipelines, df, features):
    """Split A: treino 2025, teste 2026. Retorna métricas TRAIN + TEST."""
    results = []

    mask_train = df["season"] == 2025
    mask_test = df["season"] == 2026

    X_train, y_train = df.loc[mask_train, features].values, df.loc[mask_train, "result"].map({"A": 0, "D": 1, "H": 2}).values
    X_test, y_test = df.loc[mask_test, features].values, df.loc[mask_test, "result"].map({"A": 0, "D": 1, "H": 2}).values

    for model_name, pipeline in pipelines.items():
        pipeline.fit(X_train, y_train)

        # Train metrics
        y_pred_train = pipeline.predict(X_train)
        y_proba_train = pipeline.predict_proba(X_train)

        acc_train = accuracy_score(y_train, y_pred_train)
        f1_train = f1_score(y_train, y_pred_train, average="macro", zero_division=0)
        ll_train = log_loss(y_train, y_proba_train)

        # Test metrics
        y_pred_test = pipeline.predict(X_test)
        y_proba_test = pipeline.predict_proba(X_test)

        acc_test = accuracy_score(y_test, y_pred_test)
        f1_test = f1_score(y_test, y_pred_test, average="macro", zero_division=0)
        ll_test = log_loss(y_test, y_proba_test)

        # Gap (overfitting)
        acc_gap = acc_train - acc_test

        results.append({
            "split": "Cross-Season",
            "model": model_name,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "acc_train": acc_train,
            "acc_test": acc_test,
            "acc_gap": acc_gap,
            "f1_train": f1_train,
            "f1_test": f1_test,
            "ll_train": ll_train,
            "ll_test": ll_test,
        })

    return results

def run_walk_forward_with_train_test(pipelines, df, features):
    """Split B: Walk-Forward R4-R7. Retorna métricas TRAIN + TEST por fold."""
    results = []

    for round_n in [5, 6, 7]:
        # Train: 2025 + 2026 R1 a R_{n-1}
        mask_train = (df["season"] == 2025) | ((df["season"] == 2026) & (df["round"] < round_n))
        # Test: 2026 R_n
        mask_test = (df["season"] == 2026) & (df["round"] == round_n)

        X_train = df.loc[mask_train, features].values
        y_train = df.loc[mask_train, "result"].map({"A": 0, "D": 1, "H": 2}).values
        X_test = df.loc[mask_test, features].values
        y_test = df.loc[mask_test, "result"].map({"A": 0, "D": 1, "H": 2}).values

        if len(X_test) == 0:
            continue

        for model_name, pipeline in pipelines.items():
            pipeline.fit(X_train, y_train)

            # Train
            y_pred_train = pipeline.predict(X_train)
            acc_train = accuracy_score(y_train, y_pred_train)

            # Test
            y_pred_test = pipeline.predict(X_test)
            acc_test = accuracy_score(y_test, y_pred_test)
            acc_gap = acc_train - acc_test

            results.append({
                "split": f"Walk-Forward R{round_n}",
                "model": model_name,
                "n_train": len(X_train),
                "n_test": len(X_test),
                "acc_train": acc_train,
                "acc_test": acc_test,
                "acc_gap": acc_gap,
            })

    return results

def plot_train_test_gaps(cross_season_df, walk_forward_df):
    """Visualiza gap treino-teste para cada modelo."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Cross-Season
    ax = axes[0]
    models = cross_season_df["model"].values
    acc_train = cross_season_df["acc_train"].values
    acc_test = cross_season_df["acc_test"].values
    gaps = cross_season_df["acc_gap"].values

    x = np.arange(len(models))
    width = 0.35

    ax.bar(x - width/2, acc_train, width, label="Train", color="#2ecc71", alpha=0.8)
    ax.bar(x + width/2, acc_test, width, label="Test", color="#e74c3c", alpha=0.8)

    # Anotações de gap
    for i, gap in enumerate(gaps):
        ax.text(i, max(acc_train[i], acc_test[i]) + 0.03, f"Δ={gap:.1%}",
                ha="center", fontsize=9, fontweight="bold")

    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_title("Cross-Season (2025→2026)\nTrain vs Test", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    # Walk-Forward
    ax = axes[1]
    wf_summary = walk_forward_df.groupby("model")[["acc_train", "acc_test", "acc_gap"]].mean()
    models_wf = wf_summary.index
    acc_train_wf = wf_summary["acc_train"].values
    acc_test_wf = wf_summary["acc_test"].values
    gaps_wf = wf_summary["acc_gap"].values

    x = np.arange(len(models_wf))
    ax.bar(x - width/2, acc_train_wf, width, label="Train", color="#3498db", alpha=0.8)
    ax.bar(x + width/2, acc_test_wf, width, label="Test", color="#f39c12", alpha=0.8)

    for i, gap in enumerate(gaps_wf):
        ax.text(i, max(acc_train_wf[i], acc_test_wf[i]) + 0.03, f"Δ={gap:.1%}",
                ha="center", fontsize=9, fontweight="bold")

    ax.set_ylabel("Accuracy (média R5-R7)", fontsize=11)
    ax.set_title("Walk-Forward (R5-R7)\nTrain vs Test (média)", fontsize=12, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models_wf, rotation=45, ha="right")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=10)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/14_train_test_comparison.png", dpi=120, facecolor="#1a1a1a")
    print("Salvo: 14_train_test_comparison.png")
    plt.close()

def plot_overfitting_risk(cross_season_df):
    """Visualiza risco de overfitting (gap treino-teste)."""
    fig, ax = plt.subplots(figsize=(10, 6))

    models = cross_season_df["model"].values
    gaps = cross_season_df["acc_gap"].values

    # Cor: verde (gap < 5%) → amarelo (5-15%) → vermelho (> 15%)
    colors = []
    for gap in gaps:
        if gap < 0.05:
            colors.append("#2ecc71")  # Green: minimal overfitting
        elif gap < 0.15:
            colors.append("#f39c12")  # Orange: moderate
        else:
            colors.append("#e74c3c")  # Red: severe overfitting

    bars = ax.barh(models, gaps, color=colors, alpha=0.8, edgecolor="black", linewidth=1.5)

    # Threshold lines
    ax.axvline(0.05, color="orange", linestyle="--", linewidth=1.5, alpha=0.5, label="Moderate (5%)")
    ax.axvline(0.15, color="red", linestyle="--", linewidth=1.5, alpha=0.5, label="Severe (15%)")

    # Anotações
    for i, (model, gap) in enumerate(zip(models, gaps)):
        ax.text(gap + 0.005, i, f"{gap:.1%}", va="center", fontweight="bold", fontsize=10)

    ax.set_xlabel("Train Accuracy - Test Accuracy (Overfitting Gap)", fontsize=11, fontweight="bold")
    ax.set_title("Overfitting Risk Analysis\nCross-Season Split (2025→2026)", fontsize=12, fontweight="bold")
    ax.set_xlim(0, max(gaps) * 1.2)
    ax.legend(fontsize=10, loc="lower right")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/15_overfitting_risk.png", dpi=120, facecolor="#1a1a1a")
    print("Salvo: 15_overfitting_risk.png")
    plt.close()

def main():
    print("=" * 80)
    print("ANÁLISE TRAIN vs TEST — DETECTAR OVERFITTING")
    print("=" * 80)

    X, y, features, season_round = load_data()
    df = pd.read_csv(Path("analise_preditiva/outputs/match_features.csv"))
    df = df.dropna(subset=features + ["result"])

    pipelines = build_pipelines()

    # Cross-Season com train/test split
    cs_results = run_cross_season_with_train_test(pipelines, df, features)
    cs_df = pd.DataFrame(cs_results)

    print("\n--- CROSS-SEASON (2025→2026) ---")
    print(cs_df[["model", "n_train", "n_test", "acc_train", "acc_test", "acc_gap"]].to_string(index=False))

    # Walk-Forward com train/test split
    wf_results = run_walk_forward_with_train_test(pipelines, df, features)
    wf_df = pd.DataFrame(wf_results)

    print("\n--- WALK-FORWARD (R5-R7) ---")
    print(wf_df[["split", "model", "n_train", "n_test", "acc_train", "acc_test", "acc_gap"]].to_string(index=False))

    # Resumo
    print("\n--- RESUMO TRAIN vs TEST ---")
    cs_summary = cs_df[["model", "acc_train", "acc_test", "acc_gap"]].copy()
    cs_summary = cs_summary.sort_values("acc_gap")
    print(cs_summary.to_string(index=False))

    # Interpretação
    print("\n--- INTERPRETAÇÃO ---")
    for _, row in cs_summary.iterrows():
        model = row["model"]
        gap = row["acc_gap"]
        train_acc = row["acc_train"]
        test_acc = row["acc_test"]

        if gap < 0.05:
            risk = "✅ Baixo risco de overfitting"
        elif gap < 0.15:
            risk = "⚠️ Overfitting moderado"
        else:
            risk = "❌ Overfitting severo"

        print(f"{model:20} | Train: {train_acc:.1%} | Test: {test_acc:.1%} | Gap: {gap:.1%} | {risk}")

    # Salvar CSV
    cs_df.to_csv("analise_preditiva/outputs/train_test_comparison.csv", index=False)
    wf_df.to_csv("analise_preditiva/outputs/train_test_walkforward.csv", index=False)
    print("\nSalvo: train_test_comparison.csv")

    # Gráficos
    plot_train_test_gaps(cs_df, wf_df)
    plot_overfitting_risk(cs_df)

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
