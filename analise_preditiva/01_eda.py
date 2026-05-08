"""
EDA — Análise Exploratória para Predição de Partidas
Série B 2025 (R1 + R21-R38) + Série B 2026 (R1-R7)
=====================================================
Outputs em analise_preditiva/outputs/
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

from src.features.match_features import build_match_features

# ── Caminhos ──────────────────────────────────────────────────────────────────
OUT_DIR = Path(__file__).parent / "outputs"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCES = {
    "serie_b_2025": {
        "label":   "Série B 2025",
        "color":   "#60A5FA",
        "matches": ROOT / "data/curated/serie_b_2025/matches.csv",
        "stats":   ROOT / "data/curated/serie_b_2025/team_match_stats.csv",
        "players": None,
        "note":    "R1 + R21–R38 (R2–R20 ausentes; rolling form interpolado)",
    },
    "serie_b_2026": {
        "label":   "Série B 2026",
        "color":   "#F5C400",
        "matches": ROOT / "data/curated/serie_b_2026/matches.csv",
        "stats":   ROOT / "data/curated/serie_b_2026/team_match_stats.csv",
        "players": ROOT / "data/curated/serie_b_2026/player_match_stats.csv",
        "note":    "R1–R7 (temporada em curso)",
    },
}

BG    = "#0d0d0d"
GOLD  = "#F5C400"
GRAY  = "#555555"
DGRAY = "#2a2a2a"
RED   = "#EF4444"
GREEN = "#22C55E"
BLUE  = "#60A5FA"

RESULT_COLORS = {"H": GREEN, "D": GRAY, "A": RED}
RESULT_LABELS = {"H": "Vitória Mandante", "D": "Empate", "A": "Vitória Visitante"}

FEATURE_GROUPS = {
    "Diferenciais": [
        "xg_diff", "shots_diff", "sot_diff", "poss_diff",
        "passes_acc_pct_diff", "corners_diff",
    ],
    "Eficiência": [
        "xg_per_shot_diff", "xg_overperformance_h",
        "xg_overperformance_a", "xg_overperformance_diff",
    ],
    "Field Tilt": [
        "field_tilt_sot_h", "field_tilt_sot_diff",
        "xg_tilt_h", "xg_tilt_diff",
    ],
    "Rolling Form (3)": [
        "rolling_xg_diff_3", "rolling_pts_diff_3",
        "rolling_pts_3_h", "rolling_pts_3_a",
    ],
    "xG Contextual": ["xg_ctx_h", "xg_ctx_a", "xg_ctx_diff"],
    "Posicionamento (2026 only)": [
        "prog_ratio_diff", "prog_ratio_h",
    ],
}

ALL_FEATS = [f for grp in FEATURE_GROUPS.values() for f in grp]


def _divider(c="─", w=80): print(c * w)
def _section(t): print(); _divider("═"); print(f"  {t}"); _divider("═")


# ── Carrega e constrói features por fonte ────────────────────────────────────

def load_all() -> pd.DataFrame:
    frames = []
    for src_key, cfg in SOURCES.items():
        print(f"  [{cfg['label']}] carregando... ({cfg['note']})")
        matches = pd.read_csv(cfg["matches"])
        stats   = pd.read_csv(cfg["stats"])
        players = pd.read_csv(cfg["players"]) if cfg["players"] and Path(cfg["players"]).exists() else None

        df = build_match_features(matches, stats, players=players, rolling_window=3)
        df["data_source"] = src_key
        df["source_label"] = cfg["label"]
        frames.append(df)
        n = len(df)
        rounds = sorted(df["round"].unique().astype(int).tolist())
        rng = f"R{rounds[0]}–R{rounds[-1]}" if len(rounds) > 1 else f"R{rounds[0]}"
        print(f"    {n} partidas · {rng} · {len(df.columns)} colunas")

    combined = pd.concat(frames, ignore_index=True)
    print(f"\n  Total combinado: {len(combined)} partidas\n")
    return combined


# ── Distribuição de resultados ────────────────────────────────────────────────

def print_result_distribution(df: pd.DataFrame):
    _section("DISTRIBUIÇÃO DE RESULTADOS")
    for src_key, cfg in SOURCES.items():
        sub = df[df["data_source"] == src_key]
        n = len(sub)
        if n == 0: continue
        dist = sub["result"].value_counts()
        print(f"\n  [{cfg['label']}]  ({n} partidas)")
        for code, label in RESULT_LABELS.items():
            cnt = dist.get(code, 0)
            pct = cnt / n * 100
            bar = "█" * int(pct / 3)
            print(f"    {label:25s} {cnt:3d}  ({pct:5.1f}%)  {bar}")
        home_pts  = sub["pts_h"].mean()
        away_pts  = sub["pts_a"].mean()
        print(f"    Home advantage: mandante {home_pts:.3f} pts  vs  visitante {away_pts:.3f} pts  ({home_pts-away_pts:+.3f})")

    # Combined
    n_all = len(df)
    dist_all = df["result"].value_counts()
    print(f"\n  [COMBINADO]  ({n_all} partidas)")
    for code, label in RESULT_LABELS.items():
        cnt = dist_all.get(code, 0)
        pct = cnt / n_all * 100
        print(f"    {label:25s} {cnt:3d}  ({pct:5.1f}%)")
    baseline = dist_all.max() / n_all
    print(f"\n  Baseline (mais frequente): {baseline:.1%}")


def plot_result_distribution(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), sharey=True)
    fig.patch.set_facecolor(BG)
    titles = {src: cfg["label"] for src, cfg in SOURCES.items()}
    titles["combined"] = "Combinado (2025+2026)"

    datasets = {src: df[df["data_source"] == src] for src in SOURCES}
    datasets["combined"] = df

    for ax, (key, sub) in zip(axes, datasets.items()):
        ax.set_facecolor("#111111")
        n = len(sub)
        dist = sub["result"].value_counts().reindex(["H", "D", "A"]).fillna(0)
        colors = [RESULT_COLORS[r] for r in dist.index]
        bars = ax.bar([RESULT_LABELS[r] for r in dist.index],
                      dist.values / n * 100, color=colors, alpha=0.82, width=0.55)
        for bar, val in zip(bars, dist.values):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.6,
                    f"{val:.0f}", ha="center", va="bottom",
                    color="white", fontsize=10, fontweight="bold")
        ax.set_title(titles[key], color=GOLD, fontsize=10)
        ax.set_ylabel("% Partidas", color="white")
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values(): spine.set_edgecolor(GRAY)

    fig.suptitle("Distribuição de Resultados por Fonte", color=GOLD, fontsize=12, y=1.02)
    plt.tight_layout()
    _save(fig, "01_result_distribution.png")


# ── Médias por resultado e fonte ──────────────────────────────────────────────

def print_means_by_source(df: pd.DataFrame):
    _section("MÉDIAS POR RESULTADO — COMPARAÇÃO POR ANO")
    key_feats = [
        ("xg_h",                "xG mandante"),
        ("xg_a",                "xG visitante"),
        ("xg_diff",             "xG diferencial"),
        ("sot_diff",            "SoT diferencial"),
        ("xg_overperformance_diff", "xG Overperf diff"),
        ("field_tilt_sot_h",    "Field Tilt SoT"),
        ("xg_tilt_diff",        "xG Tilt diff"),
        ("poss_h",              "Posse mandante %"),
        ("passes_acc_pct_h",    "Passes acc% mandante"),
        ("shots_h",             "Chutes mandante"),
    ]

    for feat, label in key_feats:
        if feat not in df.columns: continue
        print(f"\n  {label} ({feat})")
        header = f"    {'Fonte':<22} {'H':>8}  {'D':>8}  {'A':>8}  {'H−A':>8}"
        print(header)
        _divider("-", 64)
        for src_key, cfg in SOURCES.items():
            sub = df[df["data_source"] == src_key]
            means = sub.groupby("result")[feat].mean()
            h = means.get("H", np.nan); d = means.get("D", np.nan); a = means.get("A", np.nan)
            diff = h - a if not (np.isnan(h) or np.isnan(a)) else np.nan
            print(f"    {cfg['label']:<22} {h:>8.3f}  {d:>8.3f}  {a:>8.3f}  {diff:>+8.3f}")
        # Combined
        means_all = df.groupby("result")[feat].mean()
        h = means_all.get("H", np.nan); d = means_all.get("D", np.nan); a = means_all.get("A", np.nan)
        diff = h - a if not (np.isnan(h) or np.isnan(a)) else np.nan
        print(f"    {'Combinado':<22} {h:>8.3f}  {d:>8.3f}  {a:>8.3f}  {diff:>+8.3f}")


# ── Estatísticas gerais por fonte ─────────────────────────────────────────────

def print_season_stats(df: pd.DataFrame):
    _section("ESTATÍSTICAS GERAIS POR ANO")
    stat_feats = [
        ("xg_h",             "xG médio mandante"),
        ("xg_a",             "xG médio visitante"),
        ("shots_h",          "Chutes mandante"),
        ("sot_h",            "Chutes a gol mandante"),
        ("poss_h",           "Posse mandante %"),
        ("passes_acc_pct_h", "Passes acc% mandante"),
        ("yellow_h",         "Cartões amarelos mandante"),
        ("fouls_h",          "Faltas mandante"),
    ]

    header = f"  {'Métrica':<35} {'2025':>10}  {'2026':>10}  {'Delta':>10}"
    print(header)
    _divider("-", 72)
    for feat, label in stat_feats:
        if feat not in df.columns: continue
        v25 = df[df["data_source"] == "serie_b_2025"][feat].mean()
        v26 = df[df["data_source"] == "serie_b_2026"][feat].mean()
        delta = v26 - v25 if not (np.isnan(v25) or np.isnan(v26)) else np.nan
        print(f"  {label:<35} {v25:>10.3f}  {v26:>10.3f}  {delta:>+10.3f}")


# ── Correlações por fonte ─────────────────────────────────────────────────────

def compute_correlations_by_source(df: pd.DataFrame) -> pd.DataFrame:
    feats = [f for f in ALL_FEATS if f in df.columns]
    rows = []
    for feat in feats:
        row = {"feature": feat}
        for src_key, cfg in SOURCES.items():
            sub = df[df["data_source"] == src_key][[feat, "result_num"]].dropna()
            if len(sub) < 10:
                row[f"r_{src_key[-4:]}"] = np.nan
                row[f"p_{src_key[-4:]}"] = np.nan
                row[f"n_{src_key[-4:]}"] = len(sub)
                continue
            r, p = scipy_stats.pearsonr(sub[feat], sub["result_num"])
            row[f"r_{src_key[-4:]}"]  = round(r, 4)
            row[f"p_{src_key[-4:]}"]  = round(p, 4)
            row[f"n_{src_key[-4:]}"]  = len(sub)
        # Combined
        sub_all = df[[feat, "result_num"]].dropna()
        if len(sub_all) >= 10:
            r, p = scipy_stats.pearsonr(sub_all[feat], sub_all["result_num"])
            row["r_comb"] = round(r, 4)
            row["p_comb"] = round(p, 4)
            row["n_comb"] = len(sub_all)
        else:
            row["r_comb"] = np.nan; row["p_comb"] = np.nan; row["n_comb"] = len(sub_all)
        rows.append(row)

    corr_df = pd.DataFrame(rows)
    corr_df["abs_r_comb"] = corr_df["r_comb"].abs()
    corr_df = corr_df.sort_values("abs_r_comb", ascending=False).drop(columns="abs_r_comb")
    return corr_df.reset_index(drop=True)


def print_correlations(corr_df: pd.DataFrame):
    _section("CORRELAÇÃO PEARSON COM RESULTADO — POR ANO E COMBINADO")
    print(f"  {'Feature':<32}  {'r_2025':>8}  {'r_2026':>8}  {'r_comb':>8}  "
          f"{'n_2025':>7}  {'n_2026':>7}  {'n_comb':>7}")
    _divider("-", 90)
    for _, row in corr_df.iterrows():
        r25  = f"{row['r_2025']:+.4f}" if not np.isnan(row.get("r_2025", np.nan)) else "     —  "
        r26  = f"{row['r_2026']:+.4f}" if not np.isnan(row.get("r_2026", np.nan)) else "     —  "
        rc   = f"{row['r_comb']:+.4f}"  if not np.isnan(row.get("r_comb", np.nan)) else "     —  "
        sig25 = "*" if not np.isnan(row.get("p_2025", np.nan)) and row["p_2025"] < 0.05 else " "
        sig26 = "*" if not np.isnan(row.get("p_2026", np.nan)) and row["p_2026"] < 0.05 else " "
        sigc  = "*" if not np.isnan(row.get("p_comb", np.nan)) and row["p_comb"]  < 0.05 else " "
        n25 = int(row.get("n_2025", 0)) if not np.isnan(row.get("n_2025", np.nan)) else 0
        n26 = int(row.get("n_2026", 0)) if not np.isnan(row.get("n_2026", np.nan)) else 0
        nc  = int(row.get("n_comb", 0)) if not np.isnan(row.get("n_comb", np.nan)) else 0
        print(f"  {row['feature']:<32}  {r25}{sig25}  {r26}{sig26}  {rc}{sigc}  "
              f"{n25:>7}  {n26:>7}  {nc:>7}")
    print("\n  * p < 0.05")


def plot_correlation_comparison(corr_df: pd.DataFrame):
    df_plot = corr_df.dropna(subset=["r_comb"]).head(18)
    n = len(df_plot)
    y_pos = list(range(n))

    fig, ax = plt.subplots(figsize=(11, 7))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor("#111111")

    w = 0.26
    r25 = df_plot["r_2025"].fillna(0).values
    r26 = df_plot["r_2026"].fillna(0).values
    rc  = df_plot["r_comb"].values

    ys = np.array(y_pos)
    ax.barh(ys + w, r25, height=w, color=BLUE,  alpha=0.80, label="2025")
    ax.barh(ys,      r26, height=w, color=GOLD,  alpha=0.80, label="2026")
    ax.barh(ys - w, rc,  height=w, color=GREEN, alpha=0.60, label="Combinado")

    ax.set_yticks(ys)
    ax.set_yticklabels(df_plot["feature"].values, fontsize=8, color="white")
    ax.axvline(0, color=GRAY, lw=0.8)
    ax.set_xlabel("Pearson r  (result_num: H=1, D=0, A=−1)", color="white")
    ax.set_title("Correlação por Feature e por Fonte", color=GOLD, fontsize=12)
    ax.legend(facecolor="#222222", labelcolor="white", fontsize=9)
    ax.tick_params(colors="white")
    for spine in ax.spines.values(): spine.set_edgecolor(GRAY)

    plt.tight_layout()
    _save(fig, "02_correlation_comparison.png")


# ── Heatmap de multicolinearidade ─────────────────────────────────────────────

def plot_multicollinearity(df: pd.DataFrame):
    diff_feats = [f for f in [
        "xg_diff", "sot_diff", "poss_diff", "passes_acc_pct_diff",
        "field_tilt_sot_diff", "xg_tilt_diff",
        "xg_overperformance_diff", "xg_ctx_diff",
        "rolling_xg_diff_3", "rolling_pts_diff_3",
    ] if f in df.columns]

    sub = df[diff_feats].dropna(how="all")
    corr_matrix = sub.corr()
    n = len(diff_feats)

    fig, ax = plt.subplots(figsize=(9, 8))
    fig.patch.set_facecolor(BG); ax.set_facecolor(BG)
    im = ax.imshow(corr_matrix.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    plt.colorbar(im, ax=ax, fraction=0.04, pad=0.02)
    ax.set_xticks(range(n)); ax.set_yticks(range(n))
    ax.set_xticklabels(diff_feats, rotation=45, ha="right", fontsize=8, color="white")
    ax.set_yticklabels(diff_feats, fontsize=8, color="white")
    for i in range(n):
        for j in range(n):
            val = corr_matrix.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=6.5, color="white" if abs(val) > 0.5 else "#aaaaaa")
    ax.set_title("Heatmap de Multicolinearidade — Dataset Combinado", color=GOLD, fontsize=11)
    plt.tight_layout()
    _save(fig, "03_multicollinearity.png")


# ── Box plots por fonte ────────────────────────────────────────────────────────

def plot_boxplots_by_source(df: pd.DataFrame):
    PLOT_FEATS = [
        ("xg_diff",               "xG Diferencial"),
        ("xg_tilt_diff",          "xG Tilt"),
        ("field_tilt_sot_diff",   "Field Tilt SoT"),
        ("sot_diff",              "Chutes a Gol Diff"),
        ("xg_overperformance_diff","xG Overperf Diff"),
        ("poss_diff",             "Posse Diff"),
        ("rolling_pts_diff_3",    "Rolling Pts Diff (3)"),
        ("xg_ctx_diff",           "xG Contextual Diff"),
    ]
    avail = [(f, l) for f, l in PLOT_FEATS if f in df.columns]
    if not avail: return

    for src_key, cfg in [("combined", None), *[(k, v) for k, v in SOURCES.items()]]:
        sub = df if src_key == "combined" else df[df["data_source"] == src_key]
        title_sfx = "Combinado (2025+2026)" if src_key == "combined" else cfg["label"]

        ncols = 4
        nrows = -(-len(avail) // ncols)
        fig, axes = plt.subplots(nrows, ncols, figsize=(14, 4 * nrows))
        fig.patch.set_facecolor(BG)
        axs = axes.flatten() if hasattr(axes, "flatten") else [axes]

        for idx, (feat, label) in enumerate(avail):
            ax = axs[idx]
            ax.set_facecolor("#111111")
            groups = [sub[sub["result"] == r][feat].dropna().values for r in ["H", "D", "A"]]
            bp = ax.boxplot(groups, patch_artist=True, widths=0.55,
                            medianprops=dict(color="white", lw=1.5))
            for patch, r in zip(bp["boxes"], ["H", "D", "A"]):
                patch.set_facecolor(RESULT_COLORS[r]); patch.set_alpha(0.75)
            for elem in ("whiskers", "caps", "fliers"):
                for line in bp[elem]: line.set_color(GRAY)
            ax.set_xticklabels(["Vitória H", "Empate", "Vitória A"], fontsize=7.5, color="white")
            ax.set_title(label, color=GOLD, fontsize=8.5, pad=4)
            ax.axhline(0, color=GRAY, lw=0.6, ls="--")
            ax.tick_params(colors="white", labelsize=7)
            for spine in ax.spines.values(): spine.set_edgecolor(GRAY)

        for idx in range(len(avail), len(axs)):
            axs[idx].set_visible(False)

        fig.suptitle(f"Features por Resultado — {title_sfx}",
                     color=GOLD, fontsize=12, y=1.01)
        plt.tight_layout()
        slug = src_key.replace("serie_b_", "")
        _save(fig, f"04_boxplots_{slug}.png")


# ── Scatter de diferenças entre anos ──────────────────────────────────────────

def plot_season_comparison(df: pd.DataFrame):
    """Radar/bar: média de features selecionadas comparando 2025 vs 2026."""
    feats_plot = [
        "xg_diff", "xg_tilt_diff", "field_tilt_sot_diff",
        "sot_diff", "xg_overperformance_diff", "poss_diff",
    ]
    avail = [f for f in feats_plot if f in df.columns]
    if not avail: return

    s25 = df[df["data_source"] == "serie_b_2025"]
    s26 = df[df["data_source"] == "serie_b_2026"]

    fig, axes = plt.subplots(1, len(avail), figsize=(3.5 * len(avail), 4.5))
    fig.patch.set_facecolor(BG)
    if len(avail) == 1: axes = [axes]

    for ax, feat in zip(axes, avail):
        ax.set_facecolor("#111111")
        for src, color, label in [(s25, BLUE, "2025"), (s26, GOLD, "2026")]:
            means = src.groupby("result")[feat].mean().reindex(["H", "D", "A"])
            ax.plot(["H", "D", "A"], means.values, color=color,
                    marker="o", ms=6, lw=2.0, label=label)
        ax.set_title(feat.replace("_", " "), color=GOLD, fontsize=8)
        ax.axhline(0, color=GRAY, lw=0.6, ls="--")
        ax.tick_params(colors="white", labelsize=8)
        for spine in ax.spines.values(): spine.set_edgecolor(GRAY)
        ax.legend(fontsize=7, labelcolor="white", facecolor="#222222")

    fig.suptitle("Médias por Resultado: 2025 vs 2026", color=GOLD, fontsize=12, y=1.02)
    plt.tight_layout()
    _save(fig, "05_season_comparison.png")


def _save(fig, name):
    out = OUT_DIR / name
    fig.savefig(out, dpi=120, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"  Salvo: {name}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("\n  Carregando e construindo features por fonte...")
    df = load_all()

    out_csv = OUT_DIR / "match_features.csv"
    df.to_csv(out_csv, index=False)
    print(f"  Dataset combinado salvo: {out_csv.name} ({len(df)} linhas, {len(df.columns)} colunas)\n")

    print_result_distribution(df)
    plot_result_distribution(df)

    print_season_stats(df)
    print_means_by_source(df)

    corr_df = compute_correlations_by_source(df)
    print_correlations(corr_df)
    corr_df.to_csv(OUT_DIR / "correlations.csv", index=False)
    print(f"\n  Correlações salvas: correlations.csv")

    plot_correlation_comparison(corr_df)
    plot_multicollinearity(df)
    plot_boxplots_by_source(df)
    plot_season_comparison(df)

    _section("RESUMO — TOP 5 FEATURES (CORRELAÇÃO COMBINADA)")
    top5 = corr_df.dropna(subset=["r_comb"]).head(5)
    for _, row in top5.iterrows():
        sig_c  = "[sig]" if not np.isnan(row.get("p_comb",  np.nan)) and row["p_comb"]  < 0.05 else ""
        r25_s  = f"{row['r_2025']:+.4f}" if not np.isnan(row.get("r_2025", np.nan)) else "  —  "
        r26_s  = f"{row['r_2026']:+.4f}" if not np.isnan(row.get("r_2026", np.nan)) else "  —  "
        print(f"  {row['feature']:<32}  comb={row['r_comb']:+.4f} {sig_c}  (2025={r25_s}, 2026={r26_s})")
    print(f"\n  Gráficos em: {OUT_DIR}\n")


if __name__ == "__main__":
    main()
