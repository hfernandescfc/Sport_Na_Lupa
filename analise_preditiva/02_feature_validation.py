"""
Feature Validation — Capacidade Preditiva Individual
=====================================================
Para cada feature construída em src/features/match_features, calcula:
  - Correlação de Pearson + Spearman com result_num
  - Cramér's V com result (3 classes: H/D/A)
  - Acurácia LOO com regressão logística (se sklearn disponível)
  - Delta vs. baselines (prever sempre H, prever sempre o mais frequente)

Output: analise_preditiva/outputs/feature_ranking.csv
        analise_preditiva/outputs/05_feature_ranking.png
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import warnings
warnings.filterwarnings("ignore")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats
from scipy.stats import chi2_contingency

from src.features.match_features import build_match_features

# ── sklearn opcional ──────────────────────────────────────────────────────────
try:
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import LeaveOneOut, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# ── Caminhos ──────────────────────────────────────────────────────────────────
DATA_DIR = ROOT / "data/curated/serie_b_2026"
OUT_DIR  = Path(__file__).parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BG   = "#0d0d0d"
GOLD = "#F5C400"
GRAY = "#555555"
RED  = "#EF4444"
GREEN = "#22C55E"

# Features a avaliar — todas as construídas pelo módulo
FEATURES_TO_EVALUATE = [
    # Absolutas
    "xg_h", "xg_a", "shots_h", "shots_a", "sot_h", "sot_a",
    "poss_h", "poss_a", "passes_acc_pct_h", "passes_acc_pct_a",
    # Diferenciais
    "xg_diff", "shots_diff", "sot_diff", "poss_diff",
    "passes_acc_pct_diff", "corners_diff", "tackles_diff",
    # Eficiência
    "xg_per_shot_h", "xg_per_shot_a", "xg_per_shot_diff",
    "xg_overperformance_h", "xg_overperformance_a", "xg_overperformance_diff",
    # Field Tilt
    "field_tilt_h", "field_tilt_sot_h", "xg_tilt_h",
    "field_tilt_diff", "field_tilt_sot_diff", "xg_tilt_diff",
    # Rolling form
    "rolling_xg_prod_3_h", "rolling_xg_prod_3_a",
    "rolling_xg_conc_3_h", "rolling_xg_conc_3_a",
    "rolling_pts_3_h", "rolling_pts_3_a",
    "rolling_xg_diff_3", "rolling_pts_diff_3",
    # xG Contextual
    "xg_ctx_h", "xg_ctx_a", "xg_ctx_diff",
    # Posicionamento (se disponível)
    "line_height_h", "line_height_a", "line_height_diff",
    "prog_ratio_h", "prog_ratio_a", "prog_ratio_diff",
]


def _divider(char="─", width=100):
    print(char * width)


def _section(title: str):
    print()
    _divider("═")
    print(f"  {title}")
    _divider("═")


# ── Cramér's V ────────────────────────────────────────────────────────────────

def cramers_v(feat_vals: pd.Series, result: pd.Series) -> float:
    """Cramér's V entre uma variável contínua (discretizada) e o resultado (3 classes)."""
    try:
        # Discretizar em 3 bins (baixo/médio/alto)
        bins = pd.qcut(feat_vals, q=3, duplicates="drop", labels=False)
        ct = pd.crosstab(bins, result)
        if ct.shape[0] < 2 or ct.shape[1] < 2:
            return np.nan
        chi2, _, _, _ = chi2_contingency(ct)
        n = ct.sum().sum()
        r, k = ct.shape
        v = np.sqrt(chi2 / (n * (min(r, k) - 1)))
        return float(v)
    except Exception:
        return np.nan


# ── LOO accuracy com logistic regression ─────────────────────────────────────

def loo_accuracy(feat_vals: np.ndarray, y: np.ndarray) -> float | None:
    if not HAS_SKLEARN:
        return None
    valid_mask = ~np.isnan(feat_vals)
    X_v = feat_vals[valid_mask].reshape(-1, 1)
    y_v = y[valid_mask]
    if len(X_v) < 15 or len(np.unique(y_v)) < 2:
        return None
    try:
        pipe = make_pipeline(
            StandardScaler(),
            LogisticRegression(max_iter=500, solver="lbfgs", multi_class="multinomial",
                               C=1.0, random_state=42),
        )
        scores = cross_val_score(pipe, X_v, y_v, cv=LeaveOneOut(), scoring="accuracy", n_jobs=-1)
        return float(scores.mean())
    except Exception:
        return None


# ── Baseline ──────────────────────────────────────────────────────────────────

def compute_baselines(df: pd.DataFrame) -> dict[str, float]:
    n = len(df)
    most_frequent = df["result"].mode()[0]
    return {
        "always_most_frequent": (df["result"] == most_frequent).mean(),
        "always_home_win": (df["result"] == "H").mean(),
        "always_away_win": (df["result"] == "A").mean(),
    }


# ── Avaliação por feature ─────────────────────────────────────────────────────

def evaluate_features(df: pd.DataFrame) -> pd.DataFrame:
    y_num = df["result_num"].values
    y_cat = df["result"].values

    rows = []
    for feat in FEATURES_TO_EVALUATE:
        if feat not in df.columns:
            continue
        vals = df[feat].values.astype(float)
        valid = ~np.isnan(vals)
        n_valid = valid.sum()

        if n_valid < 10:
            rows.append({"feature": feat, "n": n_valid,
                         "pearson_r": np.nan, "p_pearson": np.nan,
                         "spearman_r": np.nan, "cramers_v": np.nan,
                         "loo_accuracy": np.nan})
            continue

        r_p, p_p = scipy_stats.pearsonr(vals[valid], y_num[valid])
        r_s, _ = scipy_stats.spearmanr(vals[valid], y_num[valid])
        cv = cramers_v(pd.Series(vals[valid]), pd.Series(y_cat[valid]))
        loo = loo_accuracy(vals, y_cat)

        rows.append({
            "feature": feat,
            "n": int(n_valid),
            "pearson_r": round(r_p, 4),
            "p_pearson": round(p_p, 4),
            "spearman_r": round(r_s, 4),
            "cramers_v": round(cv, 4) if not np.isnan(cv) else np.nan,
            "loo_accuracy": round(loo, 4) if loo is not None else np.nan,
        })

    result_df = pd.DataFrame(rows)
    # Ordena por |pearson_r| descendente
    result_df["abs_r"] = result_df["pearson_r"].abs()
    result_df = result_df.sort_values("abs_r", ascending=False).drop(columns="abs_r")
    return result_df.reset_index(drop=True)


# ── Output ────────────────────────────────────────────────────────────────────

def print_ranking(ranking: pd.DataFrame, baselines: dict[str, float]):
    _section("RANKING DE FEATURES — CAPACIDADE PREDITIVA")

    loo_header = "LOO Acc" if HAS_SKLEARN else "LOO Acc (sklearn não instalado)"
    print(f"  {'Feature':<34}  {'n':>5}  {'Pearson r':>10}  {'Spearman r':>10}"
          f"  {'Cramér V':>9}  {loo_header:>9}")
    _divider("-", 100)

    for _, row in ranking.iterrows():
        sig = ""
        if not np.isnan(row["p_pearson"]):
            sig = " *" if row["p_pearson"] < 0.05 else "  "
        r_str   = f"{row['pearson_r']:+.4f}{sig}" if not np.isnan(row["pearson_r"]) else "     —    "
        rs_str  = f"{row['spearman_r']:+.4f}"     if not np.isnan(row["spearman_r"]) else "     —"
        cv_str  = f"{row['cramers_v']:.4f}"        if not np.isnan(row["cramers_v"]) else "     —"
        loo_str = f"{row['loo_accuracy']:.1%}"     if not np.isnan(row["loo_accuracy"]) else "     —"
        print(f"  {row['feature']:<34}  {row['n']:>5}  {r_str:>12}  {rs_str:>10}"
              f"  {cv_str:>9}  {loo_str:>9}")

    print("\n  * p < 0.05")

    print()
    _divider("-", 60)
    print("  Baselines:")
    for name, acc in baselines.items():
        print(f"    {name:<30}: {acc:.1%}")

    if HAS_SKLEARN:
        top_loo = ranking.dropna(subset=["loo_accuracy"]).head(5)
        print()
        print("  Top 5 features por LOO accuracy:")
        for _, row in top_loo.iterrows():
            delta = row["loo_accuracy"] - baselines["always_most_frequent"]
            print(f"    {row['feature']:<34}  {row['loo_accuracy']:.1%}  "
                  f"({delta:+.1%} vs baseline)")


def plot_ranking(ranking: pd.DataFrame, baselines: dict[str, float]):
    df_plot = ranking.dropna(subset=["pearson_r"]).head(20)

    fig, axes = plt.subplots(1, 2, figsize=(14, 7))
    fig.patch.set_facecolor(BG)

    # Left: Pearson r
    ax = axes[0]
    ax.set_facecolor("#111111")
    y_pos = range(len(df_plot))
    colors = [GREEN if r > 0 else RED for r in df_plot["pearson_r"]]
    ax.barh(list(y_pos), df_plot["pearson_r"].values, color=colors, alpha=0.82, height=0.65)
    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(df_plot["feature"].values, fontsize=7.5, color="white")
    ax.axvline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("Pearson r  (result_num)", color="white", fontsize=9)
    ax.set_title("Correlação com Resultado", color=GOLD, fontsize=11)
    ax.tick_params(colors="white")
    for spine in ax.spines.values(): spine.set_edgecolor(GRAY)

    # Right: LOO accuracy (se disponível) ou Cramér's V
    ax2 = axes[1]
    ax2.set_facecolor("#111111")
    if HAS_SKLEARN and df_plot["loo_accuracy"].notna().any():
        vals  = df_plot["loo_accuracy"].values
        label = "LOO Accuracy"
        base  = baselines["always_most_frequent"]
        bar_colors = [GREEN if v > base else RED for v in vals]
        ax2.barh(list(y_pos), vals, color=bar_colors, alpha=0.82, height=0.65)
        ax2.axvline(base, color=GOLD, lw=1.2, ls="--", label=f"Baseline {base:.1%}")
        ax2.legend(fontsize=8, labelcolor="white", facecolor="#222222")
    else:
        cv_vals = df_plot["cramers_v"].fillna(0).values
        ax2.barh(list(y_pos), cv_vals, color=BLUE, alpha=0.75, height=0.65)
        label = "Cramér's V"

    ax2.set_yticks(list(y_pos))
    ax2.set_yticklabels(df_plot["feature"].values, fontsize=7.5, color="white")
    ax2.set_xlabel(label, color="white", fontsize=9)
    ax2.set_title("Capacidade Preditiva", color=GOLD, fontsize=11)
    ax2.tick_params(colors="white")
    for spine in ax2.spines.values(): spine.set_edgecolor(GRAY)

    fig.suptitle("Ranking de Features — Série B 2025+2026 Combinado", color=GOLD, fontsize=13, y=1.01)
    plt.tight_layout()
    out = OUT_DIR / "06_feature_ranking.png"
    fig.savefig(out, dpi=120, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Gráfico salvo: {out.name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def _eval_source(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Roda evaluate_features num subconjunto e adiciona coluna source."""
    sub = evaluate_features(df)
    sub.insert(0, "source", label)
    return sub


def main():
    features_csv = OUT_DIR / "match_features.csv"
    if features_csv.exists():
        print(f"\n  Carregando features de {features_csv.name}...")
        df = pd.read_csv(features_csv)
    else:
        print("\n  match_features.csv não encontrado — execute 01_eda.py primeiro")
        sys.exit(1)

    has_source = "data_source" in df.columns
    n = len(df)
    print(f"  {n} partidas  |  sklearn: {'disponível' if HAS_SKLEARN else 'NÃO instalado'}")
    if not HAS_SKLEARN:
        print("  LOO accuracy não disponível — instale: pip install scikit-learn")

    # ── Combinado ────────────────────────────────────────────────────────────
    print(f"\n  [1/3] Avaliando dataset combinado ({n} partidas)...")
    baselines_all = compute_baselines(df)
    ranking_all   = evaluate_features(df)
    print_ranking(ranking_all, baselines_all)

    ranking_all.to_csv(OUT_DIR / "feature_ranking.csv", index=False)
    print(f"\n  Ranking combinado salvo: feature_ranking.csv")
    plot_ranking(ranking_all, baselines_all)

    # ── Por fonte ────────────────────────────────────────────────────────────
    if has_source:
        sources = df["data_source"].unique()
        per_source_frames = []
        for src in sorted(sources):
            sub = df[df["data_source"] == src]
            label = "2025" if "2025" in src else "2026"
            print(f"\n  [{sources.tolist().index(src)+2}/{len(sources)+1}] "
                  f"Avaliando {src} ({len(sub)} partidas)...")
            rank_src = _eval_source(sub, label)
            per_source_frames.append(rank_src)

        combined_per_src = pd.concat(per_source_frames, ignore_index=True)
        combined_per_src.to_csv(OUT_DIR / "feature_ranking_per_source.csv", index=False)
        print(f"\n  Ranking por fonte salvo: feature_ranking_per_source.csv")

        # Tabela comparativa resumida
        _section("COMPARAÇÃO ENTRE FONTES — TOP 15 FEATURES (COMBINADO)")
        top15 = ranking_all.dropna(subset=["pearson_r"]).head(15)
        print(f"  {'Feature':<34}  {'r_comb':>8}  {'r_2025':>8}  {'r_2026':>8}  {'Consistente?':>14}")
        _divider("-", 80)
        for _, row in top15.iterrows():
            feat = row["feature"]
            r_comb = row["pearson_r"]
            r25 = combined_per_src.loc[
                (combined_per_src["source"] == "2025") & (combined_per_src["feature"] == feat),
                "pearson_r"
            ]
            r26 = combined_per_src.loc[
                (combined_per_src["source"] == "2026") & (combined_per_src["feature"] == feat),
                "pearson_r"
            ]
            r25_v = r25.iloc[0] if not r25.empty and not np.isnan(r25.iloc[0]) else np.nan
            r26_v = r26.iloc[0] if not r26.empty and not np.isnan(r26.iloc[0]) else np.nan

            consistent = "—"
            if not (np.isnan(r25_v) or np.isnan(r26_v)):
                same_sign = (r25_v > 0) == (r26_v > 0)
                both_sig  = True  # simplificação — focar no sinal
                consistent = "Sim" if same_sign else "Sinal INVERTIDO"

            r25_s = f"{r25_v:+.4f}" if not np.isnan(r25_v) else "     —"
            r26_s = f"{r26_v:+.4f}" if not np.isnan(r26_v) else "     —"
            print(f"  {feat:<34}  {r_comb:+.4f}  {r25_s}  {r26_s}  {consistent:>14}")

    _section("RESUMO EXECUTIVO — TOP 10 FEATURES (COMBINADO)")
    top = ranking_all.dropna(subset=["pearson_r"]).head(10)
    for i, (_, row) in enumerate(top.iterrows(), 1):
        sig = " [sig]" if not np.isnan(row["p_pearson"]) and row["p_pearson"] < 0.05 else ""
        print(f"  {i:>2}. {row['feature']:<34}  r={row['pearson_r']:+.4f}{sig}"
              f"  LOO={row['loo_accuracy']:.1%}" if not np.isnan(row.get("loo_accuracy", np.nan))
              else f"  {i:>2}. {row['feature']:<34}  r={row['pearson_r']:+.4f}{sig}")
    print()


if __name__ == "__main__":
    main()
