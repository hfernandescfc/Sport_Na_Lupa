"""
Gera cards para a thread "Sport 2026 — Temporada em Dados"
@SportRecifeLab

Cards produzidos:
  01_evolucao_saldo.png   — evolução do saldo de xG ao longo do tempo, por fase
  02_saldo_xg_forca.png   — scatter: saldo de xG vs força do adversário

Saída: pending_posts/2026-04-07_evolucao-temporada/
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
RESULTS_PATH = BASE_DIR / "data/processed/2026/sport/sport_2026_results.csv"
STATS_PATH   = BASE_DIR / "data/processed/2026/sport/sport_2026_team_match_stats.csv"
OPP_STR_PATH = BASE_DIR / "data/processed/2026/sport/sport_2026_opponent_strength.csv"
LOGO_PATH    = BASE_DIR / "sportrecifelab_avatar.png"
OUT_DIR      = BASE_DIR / "pending_posts/2026-04-13_evolucao-temporada"

TEAM_NAME        = "Sport Recife"
FASE1_N_JOGOS    = 3
SERIE_B_DEBUT_TS = pd.Timestamp("2026-03-21T23:30:00", tz="UTC")

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
CARD   = "#161616"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
LGRAY  = "#CCCCCC"
GRAY   = "#888888"
DGRAY  = "#333333"
RED    = "#EF4444"
GREEN  = "#22C55E"

FASE_C = {1: "#F59E0B", 2: "#60A5FA", 3: "#34D399"}
FASE_LABELS_LONG = {
    1: "Fase 1 — Sub20",
    2: "Fase 2 — Pré-Série B",
    3: "Fase 3 — Márcio Goiano",
}
FORCE_COLOR = "#C084FC"   # lavanda para a linha de força

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"
DPI        = 150


# ── Carrega e monta o DataFrame de análise ────────────────────────────────────

def _load_df() -> pd.DataFrame:
    results = pd.read_csv(RESULTS_PATH, encoding="utf-8")
    results["match_date_utc"] = pd.to_datetime(results["match_date_utc"], utc=True)
    results = results.sort_values("match_date_utc").reset_index(drop=True)
    results["jogo_num"] = range(1, len(results) + 1)

    def _phase(row):
        if row["jogo_num"] <= FASE1_N_JOGOS:
            return 1
        elif row["match_date_utc"] <= SERIE_B_DEBUT_TS:
            return 2
        return 3

    results["fase"] = results.apply(_phase, axis=1)
    results["opponent"] = results.apply(
        lambda r: r["away_team"] if r["home_team"] == TEAM_NAME else r["home_team"], axis=1
    )
    results["opp_short"] = results["opponent"].str.split().str[0]
    results["label"] = results["jogo_num"].astype(str) + ". " + results["opp_short"]

    team_stats = pd.read_csv(STATS_PATH, encoding="utf-8")
    sport_xg = (
        team_stats.loc[team_stats["team_name"].eq(TEAM_NAME)]
        .drop_duplicates("source_url")[["source_url", "expected_goals"]]
        .rename(columns={"expected_goals": "xg_for"})
    )
    opp_xg = (
        team_stats.loc[~team_stats["team_name"].eq(TEAM_NAME)]
        .drop_duplicates("source_url")[["source_url", "expected_goals"]]
        .rename(columns={"expected_goals": "xg_against"})
    )
    results = results.merge(sport_xg, on="source_url", how="left")
    results = results.merge(opp_xg,   on="source_url", how="left")
    results["xg_diff"] = results["xg_for"] - results["xg_against"]

    opp_str = pd.read_csv(OPP_STR_PATH, encoding="utf-8")
    mv = opp_str["squad_market_value_eur"]
    opp_str["mv_score"]   = (mv - mv.min()) / (mv.max() - mv.min())
    ppg = opp_str["perf_points_per_game"].fillna(0)
    opp_str["perf_score"] = ppg / (ppg.max() or 1)
    opp_str["strength_score"] = opp_str.apply(
        lambda r: 0.60 * r["mv_score"] + 0.40 * r["perf_score"]
        if pd.notna(r["mv_score"]) else r["perf_score"],
        axis=1,
    )
    results = results.merge(
        opp_str[["opponent_name", "squad_market_value_eur", "perf_points_per_game", "strength_score"]],
        left_on="opponent", right_on="opponent_name", how="left",
    )
    return results


# ── Helpers ───────────────────────────────────────────────────────────────────

def _new_fig(w=12.0, h=6.5):
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    fig.patch.set_facecolor(BG)
    return fig


def _add_logo(fig):
    if not HAS_PIL or not LOGO_PATH.exists():
        return
    try:
        img = Image.open(LOGO_PATH).convert("RGBA").resize((56, 56), Image.LANCZOS)
        ax_logo = fig.add_axes([0.045, 0.025, 0.055, 0.09])
        ax_logo.imshow(np.array(img))
        ax_logo.axis("off")
    except Exception:
        pass


def _footer(fig, text="Dados: SofaScore  ·  @SportRecifeLab"):
    fig.text(0.98, 0.022, text, color=GRAY, fontsize=7.5,
             fontfamily=FONT_BODY, ha="right", va="bottom")


def _phase_legend(ax, x0=0.13, y0=0.97):
    for i, (fid, label) in enumerate(FASE_LABELS_LONG.items()):
        ax.scatter([], [], color=FASE_C[fid], s=60, label=label)
    ax.legend(
        loc="upper left",
        bbox_to_anchor=(x0, y0),
        fontsize=7.5,
        frameon=True,
        facecolor="#1a1a1a",
        edgecolor="#333333",
        labelcolor=LGRAY,
        markerscale=1.2,
    )


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  OK  {path}")


def _result_color(outcome):
    return {"win": GREEN, "draw": YELLOW, "loss": RED}.get(outcome, GRAY)


def _result_letter(outcome):
    return {"win": "V", "draw": "E", "loss": "D"}.get(outcome, "?")


# ── Card 01 — Evolução do saldo de xG ao longo do tempo ──────────────────────

def card_evolucao_saldo(df: pd.DataFrame):
    """Narrativa visual: evolução do saldo de xG com picos, quedas e fases — mobile-first."""
    plot = df.dropna(subset=["xg_diff"]).copy().reset_index(drop=True)

    # ── Cores simplificadas (W/L/D) — draw agora é cinza neutro ──────────────
    C_WIN  = "#22c55e"
    C_LOSS = "#ef4444"
    C_DRAW = "#9ca3af"

    def _outcome_color(o):
        return {"win": C_WIN, "loss": C_LOSS, "draw": C_DRAW}.get(o, C_DRAW)

    # ── 16:9 → 2000 × 1125 @ DPI 150 ────────────────────────────────────
    fig = _new_fig(13.33, 7.5)
    ax  = fig.add_axes([0.075, 0.15, 0.895, 0.66])
    ax.set_facecolor(CARD)

    dates  = plot["match_date_utc"].values
    saldos = plot["xg_diff"].values

    # ── Limites do eixo X ─────────────────────────────────────────────────────
    x_min = plot["match_date_utc"].min() - pd.Timedelta(days=4)
    x_max = plot["match_date_utc"].max() + pd.Timedelta(days=6)

    # ── Fronteiras entre fases ────────────────────────────────────────────────
    all_phases = sorted(plot["fase"].unique())
    phase_last  = {f: plot.loc[plot["fase"] == f, "match_date_utc"].max() for f in all_phases}
    phase_first = {f: plot.loc[plot["fase"] == f, "match_date_utc"].min() for f in all_phases}

    boundaries = []
    for i in range(len(all_phases) - 1):
        mid = phase_last[all_phases[i]] + (phase_first[all_phases[i + 1]] - phase_last[all_phases[i]]) / 2
        boundaries.append(mid)

    span_limits = [x_min] + boundaries + [x_max]

    # ── Bandas de fase — sutis, não competem com os dados ────────────────────
    FASE_BG_DARK = {1: "#1a1300", 2: "#001221", 3: "#00160d"}
    for i, fid in enumerate(all_phases):
        ax.axvspan(span_limits[i], span_limits[i + 1],
                   color=FASE_BG_DARK[fid], alpha=0.55, zorder=0)

    # ── Linhas de fronteira de fase ───────────────────────────────────────────
    for b in boundaries:
        ax.axvline(b, color=GRAY, linewidth=0.8, linestyle="--", alpha=0.35, zorder=1)

    # ── Linha zero ────────────────────────────────────────────────────────────
    ax.axhline(0, color=GRAY, linewidth=1.1, linestyle=(0, (5, 4)), alpha=0.55, zorder=2)

    # ── Área sombreada acima/abaixo do zero — mais sutil ─────────────────────
    ax.fill_between(dates, saldos, 0,
                    where=(saldos >= 0), interpolate=True,
                    color=C_WIN, alpha=0.14, zorder=1)
    ax.fill_between(dates, saldos, 0,
                    where=(saldos < 0), interpolate=True,
                    color=C_LOSS, alpha=0.14, zorder=1)

    # ── Linha principal do saldo — halo + traço grosso ───────────────────────
    ax.plot(dates, saldos,
            color=WHITE, linewidth=5.0, alpha=0.18, zorder=3)   # glow
    ax.plot(dates, saldos,
            color=LGRAY, linewidth=2.8, alpha=0.95, zorder=4)

    # ── Pontos coloridos por resultado — maiores, borda escura p/ contraste ──
    for _, row in plot.iterrows():
        fc = _outcome_color(row.get("sport_outcome", ""))
        ax.scatter(row["match_date_utc"], row["xg_diff"],
                   s=130, color=fc, zorder=6,
                   edgecolors=BG, linewidths=1.4)

    # ── Limites Y dinâmicos (sobra para rótulos de fase e callouts) ──────────
    max_abs  = plot["xg_diff"].abs().max()
    y_top    = max_abs + 1.35
    y_bottom = -(max_abs + 1.15)
    ax.set_ylim(y_bottom, y_top)

    # ── MÉDIAS POR FASE — linhas grossas + rótulos proeminentes ──────────────
    phase_means = {}
    for i, fid in enumerate(all_phases):
        sub = plot.loc[plot["fase"] == fid, "xg_diff"].dropna()
        if sub.empty:
            continue
        m = sub.mean()
        phase_means[fid] = m
        ax.hlines(m, span_limits[i], span_limits[i + 1],
                  color=FASE_C[fid], linewidth=3.6, linestyle="-",
                  alpha=0.95, zorder=5)
        # Fase 3 costuma ser estreita e acumula callouts → encosta rótulo à esquerda
        x_pos = 0.18 if fid == 3 else 0.5
        x_label = span_limits[i] + (span_limits[i + 1] - span_limits[i]) * x_pos
        y_off   = 0.24 if m >= 0 else -0.30
        ax.text(x_label, m + y_off, f"Fase {fid}: {m:+.2f}",
                ha="center", va="bottom" if m >= 0 else "top",
                fontsize=12, color=FASE_C[fid],
                fontfamily=FONT_BODY, fontweight="bold", zorder=9,
                bbox=dict(boxstyle="round,pad=0.38", facecolor=CARD,
                          edgecolor=FASE_C[fid], alpha=0.95, linewidth=1.5))

    # ── Rótulos de fase no topo (curtos) ─────────────────────────────────────
    phase_short = {1: "FASE 1", 2: "FASE 2", 3: "FASE 3"}
    for i, fid in enumerate(all_phases):
        mid_x = span_limits[i] + (span_limits[i + 1] - span_limits[i]) / 2
        ax.text(mid_x, y_top - 0.15, phase_short[fid],
                ha="center", va="top", fontsize=11,
                color=FASE_C[fid], fontfamily=FONT_BODY,
                fontweight="bold", alpha=0.85, zorder=7)

    # ── ANOTAÇÕES NARRATIVAS: Pico, Pior, Atual ──────────────────────────────
    idx_best  = plot["xg_diff"].idxmax()
    idx_worst = plot["xg_diff"].idxmin()
    idx_last  = plot.index[-1]

    # (label, idx, borda, deslocamento em pontos)
    annotations = [
        ("Pico de desempenho", idx_best,  C_WIN,  (-65,  55)),
        ("Pior jogo",          idx_worst, C_LOSS, (-35, -65)),
        ("Atual",              idx_last,  YELLOW, ( 30, -70)),
    ]

    for label_text, idx, color, (dx, dy) in annotations:
        if idx not in plot.index:
            continue
        row = plot.loc[idx]
        opp = str(row["opponent"]).split()[0]
        y_val = row["xg_diff"]
        full = f"{label_text}\n{opp}  ({y_val:+.2f})"
        ax.annotate(
            full,
            xy=(row["match_date_utc"], y_val),
            xytext=(dx, dy), textcoords="offset points",
            fontsize=11.5, color=WHITE, fontfamily=FONT_BODY,
            fontweight="bold",
            ha="center", va="center", zorder=10,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a1a",
                      edgecolor=color, alpha=0.96, linewidth=1.8),
            arrowprops=dict(arrowstyle="-|>", color=color,
                            lw=1.8, alpha=0.95,
                            connectionstyle="arc3,rad=0.15",
                            shrinkA=0, shrinkB=8),
        )

    # ── INSIGHT CALLOUT (storytelling) ───────────────────────────────────────
    insight_text = "↑  Tendência de melhora\n↓  Oscilações ainda grandes"
    ax.text(0.985, 0.045, insight_text,
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=12, color=WHITE, fontfamily=FONT_BODY,
            fontweight="bold", linespacing=1.6, zorder=11,
            bbox=dict(boxstyle="round,pad=0.65", facecolor="#1a1a1a",
                      edgecolor=YELLOW, alpha=0.96, linewidth=1.6))

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax.set_xlim(x_min, x_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    # Menos ticks no eixo X — mobile-friendly
    ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=7))
    plt.setp(ax.get_xticklabels(), rotation=0, ha="center",
             fontsize=11, color=LGRAY, fontfamily=FONT_BODY)
    ax.set_ylabel("Saldo de xG  (a favor − contra)",
                  color=LGRAY, fontsize=12, fontfamily=FONT_BODY, labelpad=10)
    ax.set_xlabel("", color=GRAY)
    ax.tick_params(axis="y", colors=LGRAY, labelsize=11)
    ax.tick_params(axis="x", colors=LGRAY, labelsize=11)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(DGRAY)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%+.1f"))
    ax.grid(axis="y", color=DGRAY, linewidth=0.6, alpha=0.35, zorder=0)

    # ── Legenda de resultado (compacta) ──────────────────────────────────────
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C_WIN,
               markeredgecolor=BG, markeredgewidth=1.2, markersize=11, label="Vitória"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C_DRAW,
               markeredgecolor=BG, markeredgewidth=1.2, markersize=11, label="Empate"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=C_LOSS,
               markeredgecolor=BG, markeredgewidth=1.2, markersize=11, label="Derrota"),
    ]
    ax.legend(handles=legend_elems, fontsize=10.5, loc="upper right",
              frameon=True, facecolor="#1a1a1a", edgecolor="#333333",
              labelcolor=LGRAY, ncol=3, handletextpad=0.4, columnspacing=1.1)

    # ── Título narrativo + subtítulo ─────────────────────────────────────────
    fig.text(0.50, 0.955,
             "Sport evolui, mas ainda oscila mais do que deveria",
             ha="center", va="top", color=YELLOW,
             fontsize=22, fontfamily=FONT_TITLE, fontweight="bold")
    fig.text(0.50, 0.895,
             "Saldo de xG por jogo ao longo da temporada",
             ha="center", va="top", color=LGRAY, fontsize=13,
             fontfamily=FONT_BODY)

    _add_logo(fig)
    _footer(fig)
    _save(fig, "01_evolucao_saldo.png")


# ── Card 02 — Saldo de xG vs Força do adversário ──────────────────────────────

def card_saldo_xg_forca(df: pd.DataFrame):
    """Narrativa visual: correlação xG saldo x força — mensagem imediata, mobile-first."""
    plot_df = df.dropna(subset=["xg_diff", "strength_score"]).copy().reset_index(drop=True)

    TREND_C = "#C084FC"   # lavanda — cor exclusiva da linha de tendência

    # ── 16:9 → 2000×1125 @ DPI 150 ───────────────────────────────────────────
    fig = _new_fig(13.33, 7.5)
    ax  = fig.add_axes([0.09, 0.13, 0.86, 0.67])
    ax.set_facecolor(CARD)

    x_all = plot_df["strength_score"].values
    y_all = plot_df["xg_diff"].values

    # ── Limites dinâmicos com margem ──────────────────────────────────────────
    x_span = x_all.max() - x_all.min()
    y_span = y_all.max() - y_all.min()
    xl = (x_all.min() - x_span * 0.10, x_all.max() + x_span * 0.10)
    yl = (y_all.min() - y_span * 0.22, y_all.max() + y_span * 0.48)
    ax.set_xlim(*xl)
    ax.set_ylim(*yl)

    # ── Fundo quadrantes — muito sutil (dados dominam atenção) ───────────────
    ax.fill_betweenx([0, yl[1]], xl[0], xl[1], color=GREEN, alpha=0.04, zorder=0)
    ax.fill_betweenx([yl[0], 0], xl[0], xl[1], color=RED,   alpha=0.05, zorder=0)

    # ── Linha zero ────────────────────────────────────────────────────────────
    ax.axhline(0, color=GRAY, linewidth=1.0, linestyle="--", alpha=0.40, zorder=2)

    # ── Linha de regressão — mais grossa e colorida (mensagem principal) ─────
    coef  = np.polyfit(x_all, y_all, 1)
    x_line = np.linspace(xl[0], xl[1], 300)
    y_line = np.polyval(coef, x_line)
    r = np.corrcoef(x_all, y_all)[0, 1]
    # Halo
    ax.plot(x_line, y_line, color=TREND_C, linewidth=7.0,
            linestyle="--", alpha=0.18, zorder=3)
    # Linha principal
    ax.plot(x_line, y_line, color=TREND_C, linewidth=2.8,
            linestyle="--", alpha=0.90, zorder=4)

    # ── Rótulo da tendência: posicionado no meio-direito da linha ────────────
    x_tlabel = xl[0] + (xl[1] - xl[0]) * 0.65
    y_tlabel = np.polyval(coef, x_tlabel)
    ax.annotate("Tendência: queda de desempenho",
                xy=(x_tlabel, y_tlabel),
                xytext=(0, -45), textcoords="offset points",
                fontsize=11.5, color=TREND_C, fontfamily=FONT_BODY,
                fontweight="bold", ha="center", va="top", zorder=10,
                arrowprops=dict(arrowstyle="-", color=TREND_C,
                                lw=1.3, alpha=0.75, shrinkB=5))

    # ── Scatter: pontos maiores com halo para contraste ──────────────────────
    for fid in sorted(plot_df["fase"].unique()):
        fsub = plot_df.loc[plot_df["fase"] == fid]
        ax.scatter(fsub["strength_score"], fsub["xg_diff"],
                   color=FASE_C[fid], s=360, zorder=4,
                   edgecolors=FASE_C[fid], linewidths=5, alpha=0.15)  # halo
        ax.scatter(fsub["strength_score"], fsub["xg_diff"],
                   color=FASE_C[fid], s=165, zorder=5,
                   edgecolors="#0d0d0d", linewidths=1.3,
                   label=FASE_LABELS_LONG[fid])

    # ── Identifica pontos-chave ───────────────────────────────────────────────
    med_str = np.median(x_all)
    strong_df = plot_df[plot_df["strength_score"] >= med_str]
    weak_df   = plot_df[plot_df["strength_score"] <  med_str]

    # Pior atuação contra adversário forte
    idx_ws = strong_df["xg_diff"].idxmin() if not strong_df.empty else plot_df["xg_diff"].idxmin()
    # Melhor atuação contra adversário fraco
    idx_bw = weak_df["xg_diff"].idxmax()   if not weak_df.empty   else None

    # ── Callout 1: pior ponto (lado forte) ───────────────────────────────────
    ws_row = plot_df.loc[idx_ws]
    ax.annotate(
        f"Pior atuação contra time forte\n({ws_row['opp_short']}  {ws_row['xg_diff']:+.2f})",
        xy=(ws_row["strength_score"], ws_row["xg_diff"]),
        xytext=(80, 55), textcoords="offset points",
        fontsize=11.5, color=WHITE, fontfamily=FONT_BODY,
        fontweight="bold", ha="center", va="center", zorder=12,
        bbox=dict(boxstyle="round,pad=0.55", facecolor="#1a1a1a",
                  edgecolor="#ef4444", alpha=0.96, linewidth=1.8),
        arrowprops=dict(arrowstyle="-|>", color="#ef4444", lw=1.8,
                        alpha=0.95, connectionstyle="arc3,rad=-0.15",
                        shrinkA=0, shrinkB=9))

    # ── Callout 2: melhor ponto (lado fraco) ─────────────────────────────────
    if idx_bw is not None:
        bw_row = plot_df.loc[idx_bw]
        ax.annotate(
            f"Melhores jogos contra adversários fracos\n({bw_row['opp_short']}  {bw_row['xg_diff']:+.2f})",
            xy=(bw_row["strength_score"], bw_row["xg_diff"]),
            xytext=(-30, 65), textcoords="offset points",
            fontsize=11.5, color=WHITE, fontfamily=FONT_BODY,
            fontweight="bold", ha="center", va="center", zorder=12,
            bbox=dict(boxstyle="round,pad=0.55", facecolor="#1a1a1a",
                      edgecolor="#22c55e", alpha=0.95, linewidth=1.8),
            arrowprops=dict(arrowstyle="-|>", color="#22c55e", lw=1.8,
                            alpha=0.90, connectionstyle="arc3,rad=0.15",
                            shrinkA=0, shrinkB=9))

    # ── Centroides por fase — diamantes com nome contextual ──────────────────
    fase_context = {1: "Base fraca", 2: "Era Roger", 3: "Competição real"}
    for fid in sorted(plot_df["fase"].unique()):
        fsub = plot_df.loc[plot_df["fase"] == fid]
        cx, cy = fsub["strength_score"].mean(), fsub["xg_diff"].mean()
        ax.scatter(cx, cy, color=FASE_C[fid], s=420, zorder=7,
                   edgecolors=WHITE, linewidths=2.2, marker="D", alpha=0.95)
        y_off = 0.28 if cy >= 0 else -0.32
        ax.text(cx, cy + y_off,
                f"F{fid} — {fase_context.get(fid, '')} · {cy:+.2f}",
                ha="center", va="bottom" if cy >= 0 else "top",
                fontsize=10.5, color=FASE_C[fid], fontfamily=FONT_BODY,
                fontweight="bold", zorder=8,
                bbox=dict(boxstyle="round,pad=0.35", facecolor=BG,
                          edgecolor=FASE_C[fid], alpha=0.90, linewidth=1.2))

    # ── Correlação — box proeminente no canto inferior esquerdo ──────────────
    ax.text(0.02, 0.05,
            f"Correlação negativa  (r = {r:.2f})\n"
            "Quanto mais forte o adversário → pior o saldo",
            transform=ax.transAxes, ha="left", va="bottom",
            fontsize=12, color=TREND_C, fontfamily=FONT_BODY,
            fontweight="bold", linespacing=1.5, zorder=11,
            bbox=dict(boxstyle="round,pad=0.60", facecolor="#1a1a1a",
                      edgecolor=TREND_C, alpha=0.95, linewidth=1.6))

    # ── Insight box principal (topo direito) ──────────────────────────────────
    ax.text(0.985, 0.97,
            "Domina adversários fracos\nSofre contra adversários fortes",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=12.5, color=WHITE, fontfamily=FONT_BODY,
            fontweight="bold", linespacing=1.55, zorder=11,
            bbox=dict(boxstyle="round,pad=0.65", facecolor="#1a1a1a",
                      edgecolor=YELLOW, alpha=0.96, linewidth=1.7))

    # ── Axes ─────────────────────────────────────────────────────────────────
    ax.set_xlabel("Força do adversário  (0 = mais fraco  ·  1 = mais forte)",
                  color=LGRAY, fontsize=12, fontfamily=FONT_BODY, labelpad=10)
    ax.set_ylabel("Saldo de xG  (a favor − contra)",
                  color=LGRAY, fontsize=12, fontfamily=FONT_BODY, labelpad=10)
    ax.tick_params(colors=LGRAY, labelsize=11)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=6))
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%+.1f"))
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(DGRAY)
    ax.grid(axis="both", color=DGRAY, linewidth=0.5, alpha=0.28, zorder=0)

    # ── Legenda compacta de fases ─────────────────────────────────────────────
    from matplotlib.patches import Patch
    legend_elems = [
        Patch(facecolor=FASE_C[fid], label=FASE_LABELS_LONG[fid])
        for fid in sorted(FASE_LABELS_LONG)
    ]
    ax.legend(handles=legend_elems, fontsize=10.5, loc="lower right",
              frameon=True, facecolor="#1a1a1a", edgecolor="#333333",
              labelcolor=LGRAY)

    # ── Título narrativo + subtítulo ─────────────────────────────────────────
    fig.text(0.50, 0.955,
             "Contra adversários mais fortes, o Sport cai de rendimento",
             ha="center", va="top", color=YELLOW,
             fontsize=20, fontfamily=FONT_TITLE, fontweight="bold")
    fig.text(0.50, 0.895,
             "Saldo de xG vs força do adversário  ·  Losango = média da fase",
             ha="center", va="top", color=LGRAY, fontsize=13,
             fontfamily=FONT_BODY)

    _add_logo(fig)
    _footer(fig)
    _save(fig, "02_saldo_xg_forca.png")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Carregando dados...")
    df = _load_df()
    print(f"  {len(df)} jogos | {df['xg_for'].notna().sum()} com xG | {df['strength_score'].notna().sum()} com força\n")

    print("Gerando Card 01 — Evolução do saldo de xG por fase...")
    card_evolucao_saldo(df)

    print("Gerando Card 02 — Saldo de xG vs Força...")
    card_saldo_xg_forca(df)

    print("\nCards salvos em:", OUT_DIR)
