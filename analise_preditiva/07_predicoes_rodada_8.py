"""Previsões para Rodada 8 — LogisticRegression + FULL Features."""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import warnings

warnings.filterwarnings('ignore')

# Features pré-match
PREMATCH_CORE = [
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff", "rolling_xg_diff_3",
    "rolling_pts_diff_3", "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
]

PLAYER_FEATURES = ["prog_ratio_diff", "prog_ratio_h"]
FULL_2026_FEATURES = PREMATCH_CORE + PLAYER_FEATURES

def load_data():
    """Carrega dados de 2026."""
    csv_path = Path("analise_preditiva/outputs/match_features.csv")
    df = pd.read_csv(csv_path)

    # Filtrar 2026
    df = df[df["season"] == 2026].copy()

    # Separar treino (R1-R7) e previsão (R8)
    train_df = df[df["round"] < 8].copy()
    predict_df = df[df["round"] == 8].copy()

    # Remover NaN do treino
    train_df = train_df.dropna(subset=FULL_2026_FEATURES + ["result"])

    # Encode target para treino
    train_df["result_encoded"] = train_df["result"].map({"A": 0, "D": 1, "H": 2})

    return train_df, predict_df

def build_model():
    """Cria pipeline LR."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=0.1, max_iter=500, random_state=42)),
    ])

def train_and_predict(train_df, predict_df):
    """Treina e faz previsões."""
    print("="*80)
    print("PREVISÕES RODADA 8 — LOGISTIC REGRESSION + FULL FEATURES")
    print("="*80)

    # Dados de treino
    X_train = train_df[FULL_2026_FEATURES].values
    y_train = train_df["result_encoded"].values

    print(f"\n📊 DADOS DE TREINO")
    print(f"├─ Rodadas: 1-7")
    print(f"├─ Partidas: {len(train_df)}")
    print(f"├─ Features: {len(FULL_2026_FEATURES)} (16 pré-match + 2 jogadores)")
    print(f"└─ Target: A={sum(y_train==0)}, D={sum(y_train==1)}, H={sum(y_train==2)}")

    # Treinar
    model = build_model()
    model.fit(X_train, y_train)

    # Acurácia de treino
    train_pred = model.predict(X_train)
    train_acc = np.mean(train_pred == y_train)
    print(f"\n✅ Modelo treinado")
    print(f"   Train Accuracy: {train_acc:.1%}")

    # Dados para previsão
    X_predict = predict_df[FULL_2026_FEATURES].values

    # Previsões
    y_pred_proba = model.predict_proba(X_predict)

    # Criar dataframe de resultados
    results = pd.DataFrame({
        'match_id': range(len(predict_df)),
        'home_team': predict_df['home_team'].values,
        'away_team': predict_df['away_team'].values,
        'prob_away': y_pred_proba[:, 0],
        'prob_draw': y_pred_proba[:, 1],
        'prob_home': y_pred_proba[:, 2],
    })

    # Predição mais provável
    pred_classes = np.argmax(y_pred_proba, axis=1)
    pred_result = {0: 'Away', 1: 'Draw', 2: 'Home'}
    results['predicted_result'] = [pred_result[c] for c in pred_classes]
    results['max_probability'] = np.max(y_pred_proba, axis=1)

    return results, model, train_acc

def print_predictions(results):
    """Imprime previsões de forma legível."""
    print("\n" + "="*80)
    print("PREVISÕES RODADA 8")
    print("="*80)

    for idx, row in results.iterrows():
        home = row['home_team']
        away = row['away_team']

        # Emojis de confiança
        confidence = row['max_probability']
        if confidence >= 0.45:
            conf_emoji = "🔴"
        elif confidence >= 0.40:
            conf_emoji = "🟠"
        else:
            conf_emoji = "🟡"

        print(f"\n{idx+1}. {away:20} × {home:20}")
        print(f"   Away (A):  {row['prob_away']:5.1%}  │")
        print(f"   Draw (D):  {row['prob_draw']:5.1%}  │  Predito: {row['predicted_result']:6}  {conf_emoji} {confidence:.1%}")
        print(f"   Home (H):  {row['prob_home']:5.1%}  │")

def save_results(results):
    """Salva resultados em CSV e TXT."""
    # CSV com todas as informações
    results_csv = results.copy()
    results_csv.to_csv("analise_preditiva/outputs/predicoes_rodada_8.csv", index=False)

    # TXT formatado
    with open("analise_preditiva/outputs/predicoes_rodada_8.txt", "w", encoding="utf-8") as f:
        f.write("="*80 + "\n")
        f.write("PREVISÕES RODADA 8 — SÉRIE B 2026\n")
        f.write("Modelo: LogisticRegression + FULL Features (18)\n")
        f.write("="*80 + "\n\n")

        for idx, row in results.iterrows():
            f.write(f"PARTIDA {idx+1}\n")
            f.write(f"{row['away_team']:25} × {row['home_team']:25}\n")
            f.write(f"\n  PROBABILIDADES:\n")
            f.write(f"    Away (A):  {row['prob_away']:6.1%}\n")
            f.write(f"    Draw (D):  {row['prob_draw']:6.1%}\n")
            f.write(f"    Home (H):  {row['prob_home']:6.1%}\n")
            f.write(f"\n  PREVISÃO: {row['predicted_result']:6} ({row['max_probability']:.1%})\n")
            f.write("-"*80 + "\n\n")

def create_comparison_table(results):
    """Cria tabela de comparação formatada."""
    print("\n" + "="*80)
    print("TABELA RESUMIDA — PREVISÕES RODADA 8")
    print("="*80)

    summary_df = results[[
        'home_team', 'away_team', 'prob_away', 'prob_draw', 'prob_home',
        'predicted_result', 'max_probability'
    ]].copy()

    summary_df.columns = [
        'Home Team', 'Away Team', 'P(Away)', 'P(Draw)', 'P(Home)',
        'Prediction', 'Confidence'
    ]

    # Formatar probabilidades
    for col in ['P(Away)', 'P(Draw)', 'P(Home)', 'Confidence']:
        summary_df[col] = summary_df[col].apply(lambda x: f'{x:.1%}')

    print(summary_df.to_string(index=False))

    return summary_df

def save_summary_report(results, train_acc):
    """Cria relatório completo."""
    with open("analise_preditiva/outputs/relatorio_predicoes_r8.md", "w", encoding="utf-8") as f:
        f.write("# Previsões Rodada 8 — Série B 2026\n\n")
        f.write("**Data:** 2026-05-08\n")
        f.write("**Modelo:** LogisticRegression + FULL Features (18)\n")
        f.write("**Treino:** Rodadas 1-7 (37 partidas)\n\n")

        f.write("---\n\n")

        f.write("## Performance do Modelo\n\n")
        f.write(f"- **Train Accuracy:** {train_acc:.1%}\n")
        f.write(f"- **Total Partidas R8:** {len(results)}\n")
        f.write(f"- **Features Utilizadas:** 18 (16 pré-match + 2 de jogadores)\n\n")

        f.write("---\n\n")

        f.write("## Previsões Detalhadas\n\n")

        for idx, row in results.iterrows():
            f.write(f"### Partida {idx+1}: {row['away_team']} × {row['home_team']}\n\n")
            f.write(f"| Resultado | Probabilidade |\n")
            f.write(f"|-----------|---------------|\n")
            f.write(f"| Away (A)  | {row['prob_away']:.2%} |\n")
            f.write(f"| Draw (D)  | {row['prob_draw']:.2%} |\n")
            f.write(f"| Home (H)  | {row['prob_home']:.2%} |\n\n")
            f.write(f"**Previsão:** {row['predicted_result']} ({row['max_probability']:.1%})\n\n")

        f.write("---\n\n")

        f.write("## Interpretação\n\n")
        f.write("- **Confiança Alta (≥45%):** Resultado bem definido\n")
        f.write("- **Confiança Média (40-45%):** Resultado equilibrado\n")
        f.write("- **Confiança Baixa (<40%):** Incerteza elevada\n\n")

        f.write("---\n\n")

        f.write("## Método\n\n")
        f.write("Validação temporal cruzada em 3 contextos:\n")
        f.write("- Cross-Season (2025→2026): 50.8% acurácia\n")
        f.write("- Intra-Season 2025: 67.6% acurácia\n")
        f.write("- Intra-Season 2026: 62.5% acurácia\n\n")
        f.write("**Modelo Recomendado:** LogisticRegression (overfitting 10.9-15.9%)\n")

def main():
    # Carregar dados
    train_df, predict_df = load_data()

    if len(predict_df) == 0:
        print("\n❌ Nenhuma partida de R8 encontrada no dataset")
        print(f"Últimas rodadas com dados: {train_df['round'].max()}")
        return

    print(f"\n📈 DADOS DE PREVISÃO")
    print(f"├─ Rodada: 8")
    print(f"├─ Partidas: {len(predict_df)}")
    print(f"└─ Features: {len(FULL_2026_FEATURES)}")

    # Treinar e prever
    results, model, train_acc = train_and_predict(train_df, predict_df)

    # Imprimir previsões
    print_predictions(results)

    # Tabela resumida
    create_comparison_table(results)

    # Salvar resultados
    save_results(results)
    save_summary_report(results, train_acc)

    print("\n" + "="*80)
    print("✅ PREVISÕES SALVAS")
    print("="*80)
    print("\nArquivos gerados:")
    print("  📊 predicoes_rodada_8.csv — Dados brutos com probabilidades")
    print("  📄 predicoes_rodada_8.txt — Formato legível")
    print("  📋 relatorio_predicoes_r8.md — Relatório completo")
    print("\n" + "="*80)

if __name__ == "__main__":
    main()
