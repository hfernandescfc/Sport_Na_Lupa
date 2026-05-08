"""Previsões Pré-Jogo Rodada 8 — LogisticRegression + FULL Features via Rolling Proxies.

Este script constrói features de R8 usando rolling means (window=3) do histórico R1-R7,
permitindo previsões ANTES dos jogos acontecerem (true pre-match predictions).
"""
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import warnings

warnings.filterwarnings('ignore')

PREMATCH_CORE = [
    "xg_diff", "xg_h", "xg_a", "xg_per_shot_diff",
    "xg_tilt_h", "xg_tilt_diff", "field_tilt_sot_h", "field_tilt_sot_diff",
    "sot_diff", "shots_diff", "poss_diff", "rolling_xg_diff_3",
    "rolling_pts_diff_3", "xg_ctx_diff", "passes_acc_pct_diff", "corners_diff",
]

PLAYER_FEATURES = ["prog_ratio_diff", "prog_ratio_h"]
FULL_2026_FEATURES = PREMATCH_CORE + PLAYER_FEATURES


def load_r8_fixtures():
    """Carrega partidas de R8 (fixtures) de matches.csv."""
    matches_path = Path("data/curated/serie_b_2026/matches.csv")
    df = pd.read_csv(matches_path)

    r8 = df[df["round"] == 8].copy()
    return r8.sort_values("match_date_utc").reset_index(drop=True)


def compute_team_rolling(window=3):
    """
    Calcula médias móveis de stats por time de R1-R7.
    Retorna: {team_key: {xg, shots, sot, poss, passes_acc_pct, corners, pts, xg_conc}}
    """
    stats_path = Path("data/curated/serie_b_2026/team_match_stats.csv")
    df = pd.read_csv(stats_path)

    # Filtrar apenas R1-R7
    df = df[df["round"] < 8].copy()
    df = df.sort_values(["team_key", "round"])

    # Calcular pontos (W=3, D=1, L=0)
    def get_points(row):
        if row["match_code"] in home_matches:
            h_score, a_score = home_matches[row["match_code"]]
        else:
            return np.nan

        if row["is_home"]:
            if h_score > a_score:
                return 3
            elif h_score == a_score:
                return 1
            else:
                return 0
        else:
            if a_score > h_score:
                return 3
            elif a_score == h_score:
                return 1
            else:
                return 0

    # Build score lookup
    matches_path = Path("data/curated/serie_b_2026/matches.csv")
    matches = pd.read_csv(matches_path)
    matches = matches[matches["round"] < 8]
    home_matches = {}
    for _, row in matches.iterrows():
        home_matches[row["match_code"]] = (row["home_score"], row["away_score"])

    df["pts"] = df.apply(get_points, axis=1)

    # xG concedido = xG do adversário; vamos calcular isso depois por equipe
    team_rolling = {}

    for team_key in df["team_key"].unique():
        team_df = df[df["team_key"] == team_key].copy()

        # Calcular rolling means
        rolling_xg = team_df["expected_goals"].rolling(window=window, min_periods=1).mean().iloc[-1]
        rolling_shots = team_df["shots_total"].rolling(window=window, min_periods=1).mean().iloc[-1]
        rolling_sot = team_df["shots_on_target"].rolling(window=window, min_periods=1).mean().iloc[-1]
        rolling_poss = team_df["possession"].rolling(window=window, min_periods=1).mean().iloc[-1]
        rolling_pass_acc = team_df["passes_accuracy_pct"].rolling(window=window, min_periods=1).mean().iloc[-1]
        rolling_corners = team_df["corners"].rolling(window=window, min_periods=1).mean().iloc[-1]
        rolling_pts = team_df["pts"].rolling(window=window, min_periods=1).mean().iloc[-1]

        # xG concedido: média de xG sofrido (oposto team em mesmas partidas)
        team_matches = team_df["match_code"].unique()
        team_df_all = df[df["match_code"].isin(team_matches)]
        xg_conc_list = team_df_all[team_df_all["team_key"] != team_key]["expected_goals"].tolist()
        rolling_xg_conc = np.mean(xg_conc_list[-window:]) if xg_conc_list else 1.0

        team_rolling[team_key] = {
            "xg": rolling_xg,
            "shots": rolling_shots,
            "sot": rolling_sot,
            "poss": rolling_poss,
            "passes_acc_pct": rolling_pass_acc,
            "corners": rolling_corners,
            "pts": rolling_pts,
            "xg_conc": rolling_xg_conc,
        }

    return team_rolling


def compute_prog_ratio_rolling(window=3):
    """
    Calcula prog_ratio (progressive carries / total carries) por partida/time,
    depois rolling mean(3) para cada team_key de R1-R7.
    """
    players_path = Path("data/curated/serie_b_2026/player_match_stats.csv")
    df = pd.read_csv(players_path)

    # Filtrar R1-R7
    matches_path = Path("data/curated/serie_b_2026/matches.csv")
    matches = pd.read_csv(matches_path)
    matches = matches[matches["round"] < 8][["match_code", "round"]]
    df = df.merge(matches, on="match_code", how="inner")

    # Agrupar por (match_code, team_key) e calcular prog_ratio
    prog_by_match_team = []
    for (match_code, team_key), group in df.groupby(["match_code", "team_key"]):
        total_carries = group["ball_carries_count"].sum()
        prog_carries = group["progressive_ball_carries_count"].sum()

        if total_carries > 0:
            prog_ratio = prog_carries / total_carries
        else:
            prog_ratio = 0.0

        prog_by_match_team.append({
            "match_code": match_code,
            "team_key": team_key,
            "prog_ratio": prog_ratio
        })

    prog_df = pd.DataFrame(prog_by_match_team)
    if prog_df.empty:
        return {}

    # Merge com rodada
    prog_df = prog_df.merge(matches, on="match_code", how="inner")
    prog_df = prog_df.sort_values(["team_key", "round"])

    prog_rolling = {}
    for team_key in prog_df["team_key"].unique():
        team_prog = prog_df[prog_df["team_key"] == team_key]["prog_ratio"]
        rolling_mean = team_prog.rolling(window=window, min_periods=1).mean().iloc[-1]
        prog_rolling[team_key] = rolling_mean

    return prog_rolling


def build_r8_feature_rows(fixtures, team_rolling, prog_rolling):
    """Monta DataFrame com features de R8 usando rolling proxies."""
    rows = []

    for _, fix in fixtures.iterrows():
        home_key = fix["home_team_key"]
        away_key = fix["away_team_key"]
        home_team = fix["home_team"]
        away_team = fix["away_team"]

        # Lookup team stats
        h_stats = team_rolling.get(home_key, {})
        a_stats = team_rolling.get(away_key, {})

        # Safe defaults
        h_xg = h_stats.get("xg", 0.5)
        a_xg = a_stats.get("xg", 0.5)
        h_shots = h_stats.get("shots", 5.0)
        a_shots = a_stats.get("shots", 5.0)
        h_sot = h_stats.get("sot", 2.0)
        a_sot = a_stats.get("sot", 2.0)
        h_poss = h_stats.get("poss", 50.0)
        a_poss = a_stats.get("poss", 50.0)
        h_pass_acc = h_stats.get("passes_acc_pct", 70.0)
        a_pass_acc = a_stats.get("passes_acc_pct", 70.0)
        h_corners = h_stats.get("corners", 3.0)
        a_corners = a_stats.get("corners", 3.0)
        h_pts = h_stats.get("pts", 1.0)
        a_pts = a_stats.get("pts", 1.0)
        h_xg_conc = h_stats.get("xg_conc", 1.0)
        a_xg_conc = a_stats.get("xg_conc", 1.0)

        h_prog = prog_rolling.get(home_key, 0.3)
        a_prog = prog_rolling.get(away_key, 0.3)

        # Evitar divisão por zero
        if h_shots == 0:
            h_shots = 0.1
        if a_shots == 0:
            a_shots = 0.1
        if h_sot == 0:
            h_sot = 0.1
        if a_sot == 0:
            a_sot = 0.1
        if h_xg + a_xg == 0:
            h_xg, a_xg = 0.5, 0.5
        if h_sot + a_sot == 0:
            h_sot, a_sot = 0.5, 0.5
        if h_xg_conc == 0:
            h_xg_conc = 0.1
        if a_xg_conc == 0:
            a_xg_conc = 0.1

        # Build features
        row = {
            "season": 2026,
            "round": 8,
            "home_team": home_team,
            "away_team": away_team,
            "home_team_key": home_key,
            "away_team_key": away_key,
            "xg_h": h_xg,
            "xg_a": a_xg,
            "xg_diff": h_xg - a_xg,
            "xg_per_shot_diff": (h_xg / h_shots) - (a_xg / a_shots),
            "xg_tilt_h": h_xg / (h_xg + a_xg),
            "xg_tilt_diff": (h_xg / (h_xg + a_xg)) - 0.5,
            "field_tilt_sot_h": h_sot / (h_sot + a_sot),
            "field_tilt_sot_diff": (h_sot / (h_sot + a_sot)) - 0.5,
            "sot_diff": h_sot - a_sot,
            "shots_diff": h_shots - a_shots,
            "poss_diff": h_poss - a_poss,
            "rolling_xg_diff_3": h_xg - a_xg,  # Já é rolling mean de 3
            "rolling_pts_diff_3": h_pts - a_pts,  # Já é rolling mean de 3
            "xg_ctx_diff": (h_xg / a_xg_conc) - (a_xg / h_xg_conc),
            "passes_acc_pct_diff": h_pass_acc - a_pass_acc,
            "corners_diff": h_corners - a_corners,
            "prog_ratio_h": h_prog,
            "prog_ratio_diff": h_prog - a_prog,
        }

        rows.append(row)

    return pd.DataFrame(rows)


def train_and_predict(feature_df):
    """Carrega modelo de R1-R7, faz previsões em R8."""
    print("="*80)
    print("PREVISÕES PRÉ-JOGO RODADA 8 — LOGISTIC REGRESSION + FULL FEATURES")
    print("(features via rolling proxies de R1-R7)")
    print("="*80)

    # Carregar dados de treino
    train_path = Path("analise_preditiva/outputs/match_features.csv")
    df_all = pd.read_csv(train_path)

    train_df = df_all[df_all["season"] == 2026][df_all["round"] < 8].copy()
    train_df = train_df.dropna(subset=FULL_2026_FEATURES + ["result"])
    train_df["result_encoded"] = train_df["result"].map({"A": 0, "D": 1, "H": 2})

    print(f"\n📊 DADOS DE TREINO")
    print(f"├─ Rodadas: 1-7")
    print(f"├─ Partidas: {len(train_df)}")
    print(f"├─ Features: {len(FULL_2026_FEATURES)} (16 pré-match + 2 jogadores)")
    print(f"└─ Target: A={sum(train_df['result_encoded']==0)}, D={sum(train_df['result_encoded']==1)}, H={sum(train_df['result_encoded']==2)}")

    X_train = train_df[FULL_2026_FEATURES].values
    y_train = train_df["result_encoded"].values

    # Treinar modelo
    model = Pipeline([
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(C=0.1, max_iter=500, random_state=42)),
    ])
    model.fit(X_train, y_train)

    train_acc = np.mean(model.predict(X_train) == y_train)
    print(f"\n✅ Modelo treinado")
    print(f"   Train Accuracy: {train_acc:.1%}")

    print(f"\n📈 DADOS DE PREVISÃO")
    print(f"├─ Rodada: 8")
    print(f"├─ Partidas: {len(feature_df)}")
    print(f"└─ Features: {len(FULL_2026_FEATURES)} (construídas via rolling proxies)")

    # Fazer previsões
    X_predict = feature_df[FULL_2026_FEATURES].values
    y_pred_proba = model.predict_proba(X_predict)

    # Montar resultados
    results = pd.DataFrame({
        "match_id": range(len(feature_df)),
        "home_team": feature_df["home_team"].values,
        "away_team": feature_df["away_team"].values,
        "prob_away": y_pred_proba[:, 0],
        "prob_draw": y_pred_proba[:, 1],
        "prob_home": y_pred_proba[:, 2],
    })

    pred_classes = np.argmax(y_pred_proba, axis=1)
    pred_result = {0: "Away", 1: "Draw", 2: "Home"}
    results["predicted_result"] = [pred_result[c] for c in pred_classes]
    results["max_probability"] = np.max(y_pred_proba, axis=1)

    return results, model, train_acc


def print_predictions(results):
    """Imprime previsões formatadas."""
    print("\n" + "="*80)
    print("PREVISÕES RODADA 8 — PRÉ-JOGO")
    print("="*80)

    for idx, row in results.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        confidence = row["max_probability"]

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
    """Salva resultados em 3 formatos."""
    out_dir = Path("analise_preditiva/outputs")

    # CSV
    results.to_csv(out_dir / "predicoes_r8_prematch.csv", index=False)

    # TXT
    with open(out_dir / "predicoes_r8_prematch.txt", "w", encoding="utf-8") as f:
        f.write("="*80 + "\n")
        f.write("PREVISÕES RODADA 8 — PRÉ-JOGO (SÉRIE B 2026)\n")
        f.write("Modelo: LogisticRegression + FULL Features (18)\n")
        f.write("Features: rolling proxies de R1-R7\n")
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

    # MD
    with open(out_dir / "relatorio_predicoes_r8_prematch.md", "w", encoding="utf-8") as f:
        f.write("# Previsões Pré-Jogo Rodada 8 — Série B 2026\n\n")
        f.write("**Data:** 2026-05-08\n")
        f.write("**Modelo:** LogisticRegression + FULL Features (18)\n")
        f.write("**Treino:** Rodadas 1-7 (70 partidas)\n")
        f.write("**Features:** Construídas via rolling proxies (window=3) do histórico R1-R7\n\n")

        f.write("---\n\n")
        f.write("## Metodologia\n\n")
        f.write("As features de R8 foram construídas usando médias móveis de R1-R7:\n\n")
        f.write("| Feature | Cálculo |\n")
        f.write("|---|---|\n")
        f.write("| `xg_h`, `xg_a`, `shots_diff`, `sot_diff`, etc. | rolling_mean(R1-R7, window=3) |\n")
        f.write("| `rolling_xg_diff_3`, `rolling_pts_diff_3` | Média dos últimos 3 jogos |\n")
        f.write("| `prog_ratio_h`, `prog_ratio_diff` | rolling_mean de progressive carries (player stats) |\n\n")
        f.write("Isto permite previsões **antes** dos jogos acontecerem, usando apenas histórico.\n\n")

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
        f.write("## Interpretação de Confiança\n\n")
        f.write("- **Alta (≥45%):** Resultado bem definido\n")
        f.write("- **Média (40-45%):** Resultado equilibrado\n")
        f.write("- **Baixa (<40%):** Incerteza elevada\n\n")


def main():
    print("\n🔮 Construindo features de R8 via rolling proxies...\n")

    fixtures = load_r8_fixtures()
    print(f"✓ {len(fixtures)} fixtures de R8 carregadas")

    team_rolling = compute_team_rolling()
    print(f"✓ Médias móveis de time calculadas ({len(team_rolling)} times)")

    prog_rolling = compute_prog_ratio_rolling()
    print(f"✓ Médias móveis de prog_ratio calculadas ({len(prog_rolling)} times)")

    feature_df = build_r8_feature_rows(fixtures, team_rolling, prog_rolling)
    print(f"✓ Features de R8 construídas ({len(feature_df)} partidas, {len(feature_df.columns)} colunas)\n")

    # Treinar e prever
    results, model, train_acc = train_and_predict(feature_df)

    # Imprimir
    print_predictions(results)

    # Salvar
    save_results(results)

    print("\n" + "="*80)
    print("✅ PREVISÕES SALVAS")
    print("="*80)
    print("\nArquivos gerados:")
    print("  📊 predicoes_r8_prematch.csv — Dados brutos com probabilidades")
    print("  📄 predicoes_r8_prematch.txt — Formato legível")
    print("  📋 relatorio_predicoes_r8_prematch.md — Relatório completo")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
