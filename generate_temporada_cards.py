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
OUT_DIR      = BASE_DIR / "pending_posts/2026-04-07_evolucao-temporada"

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
    results = pd.read_csv(RESULTS_PATH)
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

    team_stats = pd.read_csv(STATS_PATH)
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

    opp_str = pd.read_csv(OPP_STR_PATH)
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
    """Linha temporal do saldo de xG por jogo, com bandas de fase — estilo dark."""
    plot = df.dropna(subset=["xg_diff"]).copy()

    fig = _new_fig(13.0, 6.8)
    ax  = fig.add_axes([0.08, 0.14, 0.87, 0.70])
    ax.set_facecolor(CARD)

    dates  = plot["match_date_utc"].values
    saldos = plot["xg_diff"].values

    # ── Limites do eixo X ─────────────────────────────────────────────────────
    x_min = plot["match_date_utc"].min() - pd.Timedelta(days=4)
    x_max = plot["match_date_utc"].max() + pd.Timedelta(days=4)

    # ── Fronteiras entre fases ────────────────────────────────────────────────
    all_phases = sorted(plot["fase"].unique())
    phase_last  = {f: plot.loc[plot["fase"] == f, "match_date_utc"].max() for f in all_phases}
    phase_first = {f: plot.loc[plot["fase"] == f, "match_date_utc"].min() for f in all_phases}

    boundaries = []
    for i in range(len(all_phases) - 1):
        mid = phase_last[all_phases[i]] + (phase_first[all_phases[i + 1]] - phase_last[all_phases[i]]) / 2
        boundaries.append(mid)

    span_limits = [x_min] + boundaries + [x_max]

    # ── Bandas de fase ────────────────────────────────────────────────────────
    # Paleta de fundo escura (cada fase tem um tom sutil)
    FASE_BG_DARK = {1: "#1A1200", 2: "#001428", 3: "#001A10"}
    for i, fid in enumerate(all_phases):
        ax.axvspan(span_limits[i], span_limits[i + 1],
                   color=FASE_BG_DARK[fid], alpha=1.0, zorder=0)

    # ── Linhas de fronteira de fase ───────────────────────────────────────────
    for b in boundaries:
        ax.axvline(b, color=GRAY, linewidth=1.0, linestyle="--", alpha=0.4, zorder=1)

    # ── Linha zero ────────────────────────────────────────────────────────────
    ax.axhline(0, color=RED, linewidth=1.2, linestyle=(0, (5, 4)), alpha=0.55, zorder=2)

    # ── Área sombreada acima/abaixo do zero ───────────────────────────────────
    ax.fill_between(dates, saldos, 0,
                    where=(saldos >= 0), interpolate=True,
                    color=GREEN, alpha=0.12, zorder=1)
    ax.fill_between(dates, saldos, 0,
                    where=(saldos < 0), interpolate=True,
                    color=RED, alpha=0.12, zorder=1)

    # ── Linha principal do saldo ──────────────────────────────────────────────
    ax.plot(dates, saldos,
            color=LGRAY, linewidth=1.8, alpha=0.7,
            marker="o", markersize=5, markerfacecolor=WHITE,
            markeredgecolor=LGRAY, markeredgewidth=1.2, zorder=3)

    # ── Ponto colorido por resultado ──────────────────────────────────────────
    for _, row in plot.iterrows():
        ec = _result_color(row.get("sport_outcome", ""))
        ax.scatter(row["match_date_utc"], row["xg_diff"],
                   s=55, color=ec, zorder=5, linewidths=0)

    # ── Rótulos dos adversários ───────────────────────────────────────────────
    # Ajustes manuais de offset para evitar sobreposição nos clusters
    OFFSET_OVERRIDES = {
        "Náutico": (0, -14),   # dois jogos juntos, empurrar para baixo
        "Retrô":   (0, 8),
    }
    labeled: dict = {}
    for _, row in plot.iterrows():
        opp   = str(row["opponent"]).split()[0]
        y_val = row["xg_diff"]
        default_offset = (0, 8) if y_val >= 0 else (0, -12)
        xoff, yoff = OFFSET_OVERRIDES.get(opp, default_offset)
        va = "bottom" if yoff >= 0 else "top"

        # Se o mesmo adversário aparece várias vezes, alterna offset
        if opp in labeled:
            yoff = -yoff
            va   = "top" if yoff < 0 else "bottom"
        labeled[opp] = labeled.get(opp, 0) + 1

        ax.annotate(
            opp,
            xy=(row["match_date_utc"], y_val),
            xytext=(xoff, yoff), textcoords="offset points",
            fontsize=7.2, color=LGRAY, fontfamily=FONT_BODY,
            ha="center", va=va, zorder=6,
        )

    # ── Médias por fase (linha tracejada) ─────────────────────────────────────
    for i, fid in enumerate(all_phases):
        sub = plot.loc[plot["fase"] == fid, "xg_diff"].dropna()
        if sub.empty:
            continue
        m = sub.mean()
        ax.hlines(m, span_limits[i], span_limits[i + 1],
                  color=FASE_C[fid], linewidth=1.6, linestyle="--",
                  alpha=0.75, zorder=4)
        # Badge com a média
        mid_x = span_limits[i] + (span_limits[i + 1] - span_limits[i]) * 0.82
        ax.text(mid_x, m + (0.12 if m >= 0 else -0.18),
                f"x̄ {m:+.2f}",
                ha="center", va="bottom" if m >= 0 else "top",
                fontsize=7.5, color=FASE_C[fid],
                fontfamily=FONT_BODY, fontweight="bold", zorder=7,
                bbox=dict(boxstyle="round,pad=0.25", facecolor=CARD,
                          edgecolor=FASE_C[fid], alpha=0.85, linewidth=0.8))

    # ── Rótulos de fase no topo ───────────────────────────────────────────────
    y_top = plot["xg_diff"].max()
    for i, fid in enumerate(all_phases):
        mid_x = span_limits[i] + (span_limits[i + 1] - span_limits[i]) / 2
        lbl   = FASE_LABELS_LONG[fid].replace(" — ", "\n")
        ax.text(mid_x, y_top * 1.10, lbl,
                ha="center", va="top", fontsize=8.5,
                color=FASE_C[fid], fontfamily=FONT_BODY,
                fontweight="bold", linespacing=1.3, zorder=7)

    # ── Axes ──────────────────────────────────────────────────────────────────
    max_abs = plot["xg_diff"].abs().max()
    ax.set_ylim(-(max_abs + 0.6), max_abs + 0.9)
    ax.set_xlim(x_min, x_max)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right",
             fontsize=7.5, color=LGRAY, fontfamily=FONT_BODY)
    ax.set_ylabel("Saldo de xG  (a favor − contra)",
                  color=LGRAY, fontsize=9, fontfamily=FONT_BODY, labelpad=8)
    ax.set_xlabel("Data do jogo", color=GRAY, fontsize=8.5,
                  fontfamily=FONT_BODY, labelpad=6)
    ax.tick_params(axis="y", colors=LGRAY, labelsize=7.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(DGRAY)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%+.1f"))

    # ── Legenda resultado ──────────────────────────────────────────────────────
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GREEN,
               markersize=7, label="Vitória"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=YELLOW,
               markersize=7, label="Empate"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=RED,
               markersize=7, label="Derrota"),
    ]
    ax.legend(handles=legend_elems, fontsize=7.5, loc="lower right",
              frameon=True, facecolor="#1a1a1a", edgecolor="#333333",
              labelcolor=LGRAY)

    # ── Título ────────────────────────────────────────────────────────────────
    fig.text(0.50, 0.97, "SPORT 2026 — SALDO DE xG POR FASE",
             ha="center", va="top", color=YELLOW,
             fontsize=14, fontfamily=FONT_TITLE, fontweight="bold")
    fig.text(0.50, 0.925,
             "Ponto colorido = resultado  ·  Tracejado = média da fase  ·  3 jogos do Retrô sem dados de xG omitidos",
             ha="center", va="top", color=GRAY, fontsize=8, fontfamily=FONT_BODY)

    _add_logo(fig)
    _footer(fig)
    _save(fig, "01_evolucao_saldo.png")


# ── Card 02 — Saldo de xG vs Força do adversário ──────────────────────────────

def card_saldo_xg_forca(df: pd.DataFrame):
    plot_df = df.dropna(subset=["xg_diff", "strength_score"]).copy()

    fig = _new_fig(10.0, 6.8)
    ax  = fig.add_axes([0.10, 0.13, 0.82, 0.72])
    ax.set_facecolor(CARD)

    # ── Quadrantes de fundo ───────────────────────────────────────────────────
    xmax = plot_df["strength_score"].max() + 0.08
    ax.fill_betweenx([0, plot_df["xg_diff"].max() + 0.5],
                     0, xmax, color=GREEN, alpha=0.04, zorder=0)
    ax.fill_betweenx([plot_df["xg_diff"].min() - 0.5, 0],
                     0, xmax, color=RED, alpha=0.04, zorder=0)

    # ── Linha zero ────────────────────────────────────────────────────────────
    ax.axhline(0, color=RED, linewidth=0.9, linestyle="--", alpha=0.5, zorder=2)

    # ── Linha de regressão ────────────────────────────────────────────────────
    x_reg = plot_df["strength_score"].values
    y_reg = plot_df["xg_diff"].values
    coef  = np.polyfit(x_reg, y_reg, 1)
    x_line = np.linspace(x_reg.min() - 0.03, x_reg.max() + 0.03, 100)
    ax.plot(x_line, np.polyval(coef, x_line),
            color=GRAY, linewidth=1.4, linestyle="--", alpha=0.6, zorder=3)
    r = np.corrcoef(x_reg, y_reg)[0, 1]

    # ── Scatter por fase ──────────────────────────────────────────────────────
    for fid in sorted(plot_df["fase"].unique()):
        fsub = plot_df.loc[plot_df["fase"] == fid]
        ax.scatter(fsub["strength_score"], fsub["xg_diff"],
                   color=FASE_C[fid], s=110, zorder=5,
                   edgecolors="#0d0d0d", linewidths=0.8,
                   label=FASE_LABELS_LONG[fid])

    # ── Rótulos dos pontos ────────────────────────────────────────────────────
    for _, row in plot_df.iterrows():
        label = row["opp_short"]
        xoff, yoff = 5, 4

        # Ajuste manual para evitar sobreposição em clusters
        if row["opponent"] in ("Náutico", "Náutico ") or "Náutico" in row["opponent"]:
            yoff = -12
        if "Acadêmica" in row["opponent"]:
            xoff = -52
        if "Decisão" in row["opponent"]:
            xoff = 5; yoff = 6

        ax.annotate(
            label,
            xy=(row["strength_score"], row["xg_diff"]),
            xytext=(xoff, yoff), textcoords="offset points",
            fontsize=6.8, color=LGRAY, fontfamily=FONT_BODY,
            zorder=6,
        )

    # ── Centroides por fase (marcador maior) ──────────────────────────────────
    for fid in sorted(plot_df["fase"].unique()):
        fsub = plot_df.loc[plot_df["fase"] == fid]
        cx   = fsub["strength_score"].mean()
        cy   = fsub["xg_diff"].mean()
        ax.scatter(cx, cy, color=FASE_C[fid], s=260, zorder=7,
                   edgecolors=WHITE, linewidths=1.8,
                   marker="D", alpha=0.85)
        ax.text(cx, cy + 0.17, f"x̄ F{fid}\n({cy:+.2f})",
                ha="center", va="bottom", fontsize=7,
                color=FASE_C[fid], fontfamily=FONT_BODY, fontweight="bold",
                linespacing=1.2, zorder=8)

    # ── Badge r ───────────────────────────────────────────────────────────────
    ax.text(0.97, 0.97, f"r = {r:.2f}",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=9.5, color=WHITE, fontfamily=FONT_BODY,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#2a2a2a",
                      edgecolor=GRAY, alpha=0.9))

    # ── Rótulos de quadrante ──────────────────────────────────────────────────
    ax.text(0.02, 0.98, "saldo positivo", transform=ax.transAxes,
            ha="left", va="top", fontsize=7, color=GREEN, alpha=0.55,
            fontfamily=FONT_BODY, style="italic")
    ax.text(0.02, 0.02, "saldo negativo", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=7, color=RED, alpha=0.55,
            fontfamily=FONT_BODY, style="italic")

    # ── Axes ──────────────────────────────────────────────────────────────────
    ax.set_xlabel("Força do adversário  (0 = mais fraco  ·  1 = mais forte)",
                  color=LGRAY, fontsize=9, fontfamily=FONT_BODY, labelpad=8)
    ax.set_ylabel("Saldo de xG  (xG a favor − xG contra)",
                  color=LGRAY, fontsize=9, fontfamily=FONT_BODY, labelpad=8)
    ax.tick_params(colors=LGRAY, labelsize=7.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(DGRAY)

    # ── Legenda ───────────────────────────────────────────────────────────────
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    legend_elems = [
        Patch(facecolor=FASE_C[fid], label=FASE_LABELS_LONG[fid])
        for fid in sorted(FASE_LABELS_LONG)
    ] + [
        Line2D([0], [0], color=GRAY, linewidth=1.4, linestyle="--", label="Tendência geral"),
    ]
    ax.legend(
        handles=legend_elems, fontsize=7.5, loc="lower left",
        frameon=True, facecolor="#1a1a1a", edgecolor="#333333",
        labelcolor=LGRAY,
    )

    # ── Título ────────────────────────────────────────────────────────────────
    fig.text(0.50, 0.97, "SPORT 2026 — SALDO DE xG vs FORÇA DO ADVERSÁRIO",
             ha="center", va="top", color=YELLOW,
             fontsize=13, fontfamily=FONT_TITLE, fontweight="bold")
    fig.text(0.50, 0.925,
             "Losango = média da fase  ·  Quanto mais forte o adversário, menor o saldo",
             ha="center", va="top", color=GRAY, fontsize=8, fontfamily=FONT_BODY)

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
