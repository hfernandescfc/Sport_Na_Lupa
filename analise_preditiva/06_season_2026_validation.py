"""Validação 2026 — FULL features (pré-match + player-derived) com split R1-R5 vs R6-R7."""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, f1_score, log_loss, confusion_matrix
import seaborn as sns

# Features pré-match core
PREMATCH_CORE = [
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff", "rolling_xg_diff_3",
    "rolling_pts_diff_3", "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
]

# Features adicionais em 2026 (jogadores)
PLAYER_FEATURES = [
    "prog_ratio_diff", "prog_ratio_h"
]

FULL_2026_FEATURES = PREMATCH_CORE + PLAYER_FEATURES

def load_data_2026():
    """Carrega apenas dados de 2026."""
    csv_path = Path("analise_preditiva/outputs/match_features.csv")
    df = pd.read_csv(csv_path)

    # Filtrar 2026
    df = df[df["season"] == 2026].copy()

    # Remover NaN
    df = df.dropna(subset=FULL_2026_FEATURES + ["result", "round"])

    # Encode result
    df["result_encoded"] = df["result"].map({"A": 0, "D": 1, "H": 2})

    return df

def split_r1_r5_vs_r6_r7(df):
    """Split: R1-R5 treino, R6-R7 teste."""
    train_df = df[df["round"] < 6].copy()
    test_df = df[df["round"].isin([6, 7])].copy()

    print(f"Total 2026: {len(df)} partidas")
    print(f"Train: {len(train_df)} partidas (R1-R5)")
    print(f"Test:  {len(test_df)} partidas (R6-R7)")
    print(f"Split ratio: {len(train_df)/len(df)*100:.1f}% / {len(test_df)/len(df)*100:.1f}%")
    print(f"Train rounds: {int(train_df['round'].min())}-{int(train_df['round'].max())}")
    print(f"Test rounds:  {int(test_df['round'].min())}-{int(test_df['round'].max())}")

    # Distribuição de target
    print(f"\nTarget distribution (Train):")
    print(train_df["result"].value_counts().sort_index())
    print(f"Target distribution (Test):")
    print(test_df["result"].value_counts().sort_index())

    return train_df, test_df

def build_pipelines():
    """Cria pipelines."""
    return {
        "Baseline": Pipeline([
            ("scaler", StandardScaler()),
            ("model", DummyClassifier(strategy="most_frequent")),
        ]),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("model", LogisticRegression(C=0.1, max_iter=500)),
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

def evaluate_models(train_df, test_df, feature_set_name, features):
    """Treina todos modelos e retorna métricas."""
    X_train = train_df[features].values
    y_train = train_df["result_encoded"].values
    X_test = test_df[features].values
    y_test = test_df["result_encoded"].values

    pipelines = build_pipelines()
    results = []
    predictions = {}

    print(f"\n{'='*80}")
    print(f"TREINAMENTO COM FEATURE SET: {feature_set_name}")
    print(f"{'='*80}")

    for model_name, pipeline in pipelines.items():
        print(f"\nTreinando {model_name}...")
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

        gap = acc_train - acc_test

        results.append({
            "feature_set": feature_set_name,
            "model": model_name,
            "n_train": len(X_train),
            "n_test": len(X_test),
            "n_features": len(features),
            "acc_train": acc_train,
            "acc_test": acc_test,
            "gap": gap,
            "f1_train": f1_train,
            "f1_test": f1_test,
            "ll_train": ll_train,
            "ll_test": ll_test,
        })

        predictions[f"{feature_set_name}_{model_name}"] = {
            "y_pred": y_pred_test,
            "y_proba": y_proba_test,
            "y_true": y_test,
        }

        print(f"  Train Acc: {acc_train:.1%} | Test Acc: {acc_test:.1%} | Gap: {gap:.1%}")

    return pd.DataFrame(results), predictions, y_test

def plot_comparison_full_vs_core(core_results, full_results):
    """Compara CORE vs FULL (2026)."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Merge results
    all_results = pd.concat([core_results, full_results])

    models = ["Baseline", "LogisticRegression", "RandomForest", "XGBoost"]
    x = np.arange(len(models))
    width = 0.35

    core_acc = [core_results[core_results["model"] == m]["acc_test"].values[0] for m in models]
    full_acc = [full_results[full_results["model"] == m]["acc_test"].values[0] for m in models]

    ax.bar(x - width/2, core_acc, width, label="CORE (16 features)", color="#3498db", alpha=0.8)
    ax.bar(x + width/2, full_acc, width, label="FULL (18 features + prog_ratio)", color="#2ecc71", alpha=0.8)

    # Anotações de diferença
    for i, (c, f) in enumerate(zip(core_acc, full_acc)):
        diff = f - c
        diff_pct = f"{diff:+.1%}"
        ax.text(i, max(c, f) + 0.03, diff_pct, ha="center", fontsize=9, fontweight="bold",
               color="green" if diff > 0 else "red")

    ax.set_ylabel("Test Accuracy (R6-R7)", fontsize=12, fontweight="bold")
    ax.set_title("2026 Feature Set Comparison\nCORE (16 features) vs FULL (18 features + prog_ratio)",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/19_2026_core_vs_full.png", dpi=120, facecolor="#1a1a1a")
    print("\nSalvo: 19_2026_core_vs_full.png")
    plt.close()

def plot_train_test_full(full_results):
    """Gráfico Train vs Test para FULL."""
    fig, ax = plt.subplots(figsize=(10, 6))

    models = full_results["model"].values
    acc_train = full_results["acc_train"].values
    acc_test = full_results["acc_test"].values
    gaps = full_results["gap"].values

    x = np.arange(len(models))
    width = 0.35

    ax.bar(x - width/2, acc_train, width, label="Train (R1-R5)", color="#2ecc71", alpha=0.8)
    ax.bar(x + width/2, acc_test, width, label="Test (R6-R7)", color="#e74c3c", alpha=0.8)

    for i, gap in enumerate(gaps):
        ax.text(i, max(acc_train[i], acc_test[i]) + 0.03, f"Δ={gap:.1%}",
                ha="center", fontsize=10, fontweight="bold")

    ax.set_ylabel("Accuracy", fontsize=12, fontweight="bold")
    ax.set_title("2026 Full Feature Set — Train vs Test\nTrain (R1-R5) vs Test (R6-R7)",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/20_2026_full_train_test.png", dpi=120, facecolor="#1a1a1a")
    print("Salvo: 20_2026_full_train_test.png")
    plt.close()

def plot_overfitting_full(full_results):
    """Gráfico de overfitting para FULL."""
    fig, ax = plt.subplots(figsize=(10, 6))

    models = full_results["model"].values
    gaps = full_results["gap"].values

    colors = []
    for gap in gaps:
        if gap < 0.05:
            colors.append("#2ecc71")
        elif gap < 0.15:
            colors.append("#f39c12")
        else:
            colors.append("#e74c3c")

    bars = ax.barh(models, gaps, color=colors, alpha=0.8, edgecolor="black", linewidth=1.5)

    ax.axvline(0.05, color="orange", linestyle="--", linewidth=1.5, alpha=0.5, label="Moderate (5%)")
    ax.axvline(0.15, color="red", linestyle="--", linewidth=1.5, alpha=0.5, label="Severe (15%)")

    for i, (model, gap) in enumerate(zip(models, gaps)):
        ax.text(gap + 0.01, i, f"{gap:.1%}", va="center", fontweight="bold", fontsize=11)

    ax.set_xlabel("Overfitting Gap (Train Acc - Test Acc)", fontsize=12, fontweight="bold")
    ax.set_title("2026 Full Feature Set — Overfitting Risk\n(R1-R5 Train vs R6-R7 Test)",
                 fontsize=13, fontweight="bold")
    ax.set_xlim(-0.05, max(gaps) * 1.3)
    ax.legend(fontsize=11, loc="lower right")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/21_2026_full_overfitting.png", dpi=120, facecolor="#1a1a1a")
    print("Salvo: 21_2026_full_overfitting.png")
    plt.close()

def plot_confusion_full(predictions_full, y_test):
    """Matrizes de confusão para FULL."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    class_labels = ["Away (A)", "Draw (D)", "Home (H)"]
    model_names = ["Baseline", "LogisticRegression", "RandomForest", "XGBoost"]

    for idx, model_name in enumerate(model_names):
        key = f"FULL_{model_name}"
        if key in predictions_full:
            y_pred = predictions_full[key]["y_pred"]
            cm = confusion_matrix(y_test, y_pred)

            ax = axes[idx]
            sns.heatmap(cm, annot=True, fmt="d", cmap="YlOrRd", ax=ax, cbar=False,
                       xticklabels=class_labels, yticklabels=class_labels)
            ax.set_title(f"{model_name}", fontsize=11, fontweight="bold")
            ax.set_ylabel("True", fontsize=10)
            ax.set_xlabel("Predicted", fontsize=10)

    fig.suptitle("Confusion Matrices — 2026 Full Features (Test Set R6-R7)",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/22_2026_full_confusion.png", dpi=120, facecolor="#1a1a1a")
    print("Salvo: 22_2026_full_confusion.png")
    plt.close()

def main():
    print("=" * 80)
    print("VALIDAÇÃO 2026 — FULL FEATURE SET (COM PROG_RATIO)")
    print("=" * 80)

    # Carregar dados
    df = load_data_2026()
    print(f"\nDataset 2026: {len(df)} partidas\n")

    # Split R1-R5 vs R6-R7
    train_df, test_df = split_r1_r5_vs_r6_r7(df)

    # Treinar com CORE
    print("\n" + "=" * 80)
    print("FEATURE SET: CORE (16 pré-match)")
    print("=" * 80)
    core_results, predictions_core, y_test = evaluate_models(train_df, test_df, "CORE", PREMATCH_CORE)

    # Treinar com FULL
    print("\n" + "=" * 80)
    print("FEATURE SET: FULL (16 pré-match + 2 jogadores)")
    print("=" * 80)
    full_results, predictions_full, y_test = evaluate_models(train_df, test_df, "FULL", FULL_2026_FEATURES)

    # Imprimir resumo
    print("\n" + "=" * 80)
    print("RESULTADOS — CORE vs FULL")
    print("=" * 80)

    print("\n--- CORE (16 features) ---")
    print(core_results[["model", "acc_train", "acc_test", "gap", "f1_test"]].to_string(index=False))

    print("\n--- FULL (18 features) ---")
    print(full_results[["model", "acc_train", "acc_test", "gap", "f1_test"]].to_string(index=False))

    # Comparação feature sets
    print("\n--- DIFERENÇA FULL - CORE (Test Accuracy) ---")
    for model in ["Baseline", "LogisticRegression", "RandomForest", "XGBoost"]:
        core_acc = core_results[core_results["model"] == model]["acc_test"].values[0]
        full_acc = full_results[full_results["model"] == model]["acc_test"].values[0]
        diff = full_acc - core_acc
        print(f"{model:20} {core_acc:5.1%} → {full_acc:5.1%} ({diff:+.1%})")

    # Salvar CSVs
    all_results = pd.concat([core_results, full_results])
    all_results.to_csv("analise_preditiva/outputs/2026_full_validation_results.csv", index=False)
    print("\nSalvo: 2026_full_validation_results.csv")

    # Gráficos
    print("\nGerando visualizações...")
    plot_comparison_full_vs_core(core_results, full_results)
    plot_train_test_full(full_results)
    plot_overfitting_full(full_results)
    plot_confusion_full(predictions_full, y_test)

    # Interpretação
    print("\n" + "=" * 80)
    print("INTERPRETAÇÃO")
    print("=" * 80)

    best_core = core_results.loc[core_results["acc_test"].idxmax()]
    best_full = full_results.loc[full_results["acc_test"].idxmax()]

    print(f"\nMelhor CORE: {best_core['model']} ({best_core['acc_test']:.1%})")
    print(f"Melhor FULL: {best_full['model']} ({best_full['acc_test']:.1%})")

    print(f"\nGanho com prog_ratio (melhor modelo):")
    core_best_full = core_results[core_results["model"] == best_full['model']]["acc_test"].values[0]
    ganho = best_full['acc_test'] - core_best_full
    print(f"  {best_full['model']}: {core_best_full:.1%} → {best_full['acc_test']:.1%} ({ganho:+.1%})")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
