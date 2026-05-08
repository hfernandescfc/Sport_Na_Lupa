"""Validação intra-temporada 2025 — Train/Test Split 80/20 temporal."""
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

# Features pré-match
PREMATCH_CORE = [
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff", "rolling_xg_diff_3",
    "rolling_pts_diff_3", "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
]

def load_data_2025():
    """Carrega apenas dados de 2025."""
    csv_path = Path("analise_preditiva/outputs/match_features.csv")
    df = pd.read_csv(csv_path)

    # Filtrar 2025
    df = df[df["season"] == 2025].copy()

    # Remover NaN
    df = df.dropna(subset=PREMATCH_CORE + ["result", "round"])

    # Encode result
    df["result_encoded"] = df["result"].map({"A": 0, "D": 1, "H": 2})

    return df

def temporal_split_80_20(df):
    """
    Split temporal 80/20: treina nas rodadas iniciais, testa nas finais.
    Calcula cutoff de rodada para 80% treino.
    """
    sorted_df = df.sort_values("round")

    total_rows = len(sorted_df)
    train_size = int(total_rows * 0.8)

    # Encontrar a rodada cutoff
    train_df = sorted_df.iloc[:train_size]
    test_df = sorted_df.iloc[train_size:]

    cutoff_round = train_df["round"].max()

    print(f"Total 2025: {total_rows} partidas")
    print(f"Train: {len(train_df)} partidas (R1-R{int(cutoff_round)})")
    print(f"Test:  {len(test_df)} partidas (R{int(cutoff_round)+1}-R38)")
    print(f"Split ratio: {len(train_df)/total_rows*100:.1f}% / {len(test_df)/total_rows*100:.1f}%")
    print(f"Train rounds: {int(train_df['round'].min())}-{int(train_df['round'].max())}")
    print(f"Test rounds:  {int(test_df['round'].min())}-{int(test_df['round'].max())}")

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

def evaluate_models(train_df, test_df):
    """Treina todos modelos e retorna métricas."""
    X_train = train_df[PREMATCH_CORE].values
    y_train = train_df["result_encoded"].values
    X_test = test_df[PREMATCH_CORE].values
    y_test = test_df["result_encoded"].values

    pipelines = build_pipelines()
    results = []
    predictions = {}

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
            "model": model_name,
            "acc_train": acc_train,
            "acc_test": acc_test,
            "gap": gap,
            "f1_train": f1_train,
            "f1_test": f1_test,
            "ll_train": ll_train,
            "ll_test": ll_test,
        })

        predictions[model_name] = {
            "y_pred": y_pred_test,
            "y_proba": y_proba_test,
            "y_true": y_test,
        }

        print(f"  Train Acc: {acc_train:.1%} | Test Acc: {acc_test:.1%} | Gap: {gap:.1%}")

    return pd.DataFrame(results), predictions, y_test

def plot_train_test_comparison(results_df):
    """Gráfico Train vs Test."""
    fig, ax = plt.subplots(figsize=(10, 6))

    models = results_df["model"].values
    acc_train = results_df["acc_train"].values
    acc_test = results_df["acc_test"].values
    gaps = results_df["gap"].values

    x = np.arange(len(models))
    width = 0.35

    ax.bar(x - width/2, acc_train, width, label="Train (R1-R31)", color="#2ecc71", alpha=0.8)
    ax.bar(x + width/2, acc_test, width, label="Test (R32-R38)", color="#e74c3c", alpha=0.8)

    for i, gap in enumerate(gaps):
        ax.text(i, max(acc_train[i], acc_test[i]) + 0.03, f"Δ={gap:.1%}",
                ha="center", fontsize=10, fontweight="bold")

    ax.set_ylabel("Accuracy", fontsize=12, fontweight="bold")
    ax.set_title("Intra-Season Validation — 2025 Only\nTrain (R1-R31, 80%) vs Test (R32-R38, 20%)",
                 fontsize=13, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=45, ha="right")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=11)
    ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/16_intra_season_train_test.png", dpi=120, facecolor="#1a1a1a")
    print("\nSalvo: 16_intra_season_train_test.png")
    plt.close()

def plot_confusion_matrices(predictions, y_test):
    """Matrizes de confusão para cada modelo."""
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    axes = axes.flatten()

    class_labels = ["Away (A)", "Draw (D)", "Home (H)"]

    for idx, (model_name, pred_data) in enumerate(predictions.items()):
        y_pred = pred_data["y_pred"]
        cm = confusion_matrix(y_test, y_pred)

        ax = axes[idx]
        sns.heatmap(cm, annot=True, fmt="d", cmap="YlOrRd", ax=ax, cbar=False,
                   xticklabels=class_labels, yticklabels=class_labels)
        ax.set_title(f"{model_name}", fontsize=11, fontweight="bold")
        ax.set_ylabel("True", fontsize=10)
        ax.set_xlabel("Predicted", fontsize=10)

    fig.suptitle("Confusion Matrices — 2025 Intra-Season (Test Set R32-R38)",
                 fontsize=13, fontweight="bold", y=1.00)
    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/17_intra_season_confusion.png", dpi=120, facecolor="#1a1a1a")
    print("Salvo: 17_intra_season_confusion.png")
    plt.close()

def plot_overfitting_risk(results_df):
    """Gráfico de risco de overfitting."""
    fig, ax = plt.subplots(figsize=(10, 6))

    models = results_df["model"].values
    gaps = results_df["gap"].values

    colors = []
    for gap in gaps:
        if gap < 0.05:
            colors.append("#2ecc71")  # Green
        elif gap < 0.15:
            colors.append("#f39c12")  # Orange
        else:
            colors.append("#e74c3c")  # Red

    bars = ax.barh(models, gaps, color=colors, alpha=0.8, edgecolor="black", linewidth=1.5)

    ax.axvline(0.05, color="orange", linestyle="--", linewidth=1.5, alpha=0.5, label="Moderate (5%)")
    ax.axvline(0.15, color="red", linestyle="--", linewidth=1.5, alpha=0.5, label="Severe (15%)")

    for i, (model, gap) in enumerate(zip(models, gaps)):
        ax.text(gap + 0.005, i, f"{gap:.1%}", va="center", fontweight="bold", fontsize=11)

    ax.set_xlabel("Overfitting Gap (Train Acc - Test Acc)", fontsize=12, fontweight="bold")
    ax.set_title("Overfitting Risk — 2025 Intra-Season\n(R1-R31 Train vs R32-R38 Test)",
                 fontsize=13, fontweight="bold")
    ax.set_xlim(0, max(gaps) * 1.2)
    ax.legend(fontsize=11, loc="lower right")
    ax.grid(axis="x", alpha=0.3)

    plt.tight_layout()
    plt.savefig("analise_preditiva/outputs/18_intra_season_overfitting.png", dpi=120, facecolor="#1a1a1a")
    print("Salvo: 18_intra_season_overfitting.png")
    plt.close()

def main():
    print("=" * 80)
    print("VALIDAÇÃO INTRA-TEMPORADA — 2025 APENAS")
    print("=" * 80)

    # Carregar dados
    df = load_data_2025()
    print(f"\nDataset 2025: {len(df)} partidas\n")

    # Split temporal 80/20
    train_df, test_df = temporal_split_80_20(df)

    # Treinar e avaliar
    print("\n" + "=" * 80)
    print("TREINAMENTO E AVALIAÇÃO")
    print("=" * 80)

    results_df, predictions, y_test = evaluate_models(train_df, test_df)

    # Imprimir resumo
    print("\n" + "=" * 80)
    print("RESULTADOS")
    print("=" * 80)
    print(results_df[["model", "acc_train", "acc_test", "gap", "f1_test", "ll_test"]].to_string(index=False))

    # Salvar CSV
    results_df.to_csv("analise_preditiva/outputs/intra_season_2025_results.csv", index=False)
    print("\nSalvo: intra_season_2025_results.csv")

    # Gráficos
    print("\nGerando visualizações...")
    plot_train_test_comparison(results_df)
    plot_confusion_matrices(predictions, y_test)
    plot_overfitting_risk(results_df)

    # Interpretação
    print("\n" + "=" * 80)
    print("INTERPRETAÇÃO")
    print("=" * 80)

    best_test = results_df.loc[results_df["acc_test"].idxmax()]
    print(f"\nMelhor Performance em Test: {best_test['model']}")
    print(f"  Train Acc: {best_test['acc_train']:.1%}")
    print(f"  Test Acc:  {best_test['acc_test']:.1%}")
    print(f"  Gap:       {best_test['gap']:.1%}")
    print(f"  F1-Macro:  {best_test['f1_test']:.3f}")

    print("\nComparação Modelos (Test Accuracy):")
    for _, row in results_df.sort_values("acc_test", ascending=False).iterrows():
        gap_status = "✅" if row["gap"] < 0.15 else "⚠️" if row["gap"] < 0.25 else "❌"
        print(f"  {row['model']:20} {row['acc_test']:5.1%}  (gap: {row['gap']:5.1%}) {gap_status}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    main()
