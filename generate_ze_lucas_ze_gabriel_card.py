"""
Card comparativo — Zé Lucas vs Zé Gabriel · Sport 3×0 Retrô · Copa NE R3 2026
@SportRecifeLab

Radar sobreposto (hexagonal) + strip de stats de referência.
Stats de contagem normalizadas por 90 min (Zé Gabriel jogou 57 min).
Sem chutes/xG — meias defensivos.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.lines import Line2D
import numpy as np
from PIL import Image

# ─── Paleta ───────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
BLUE   = "#4A90D9"
GRAY   = "#2a2a2a"
LGRAY  = "#AAAAAA"
WHITE  = "#FFFFFF"

LOGO_PATH = Path(__file__).parent / "sportrecifelab_avatar.png"

# ─── Dados brutos ─────────────────────────────────────────────────────────────
MINUTES_ZL = 90.0
MINUTES_ZG = 57.0
P90_ZG     = 90.0 / MINUTES_ZG

RAW_ZL = dict(
    touches=68.0, total_pass=45.0, pass_pct=95.6,
    possession_lost=7.0, ball_recovery=6.0, fouls=2.0,
)
RAW_ZG = dict(
    touches=46.0, total_pass=37.0, pass_pct=94.6,
    possession_lost=4.0, ball_recovery=1.0, fouls=2.0,
)

# Valores p/90 para o radar
ZL = dict(
    poss_lost_p90   = RAW_ZL["possession_lost"],        # 90 min — sem ajuste
    touches_p90     = RAW_ZL["touches"],
    passes_p90      = RAW_ZL["total_pass"],
    pass_pct        = RAW_ZL["pass_pct"],
    recovery_p90    = RAW_ZL["ball_recovery"],
    fouls_p90       = RAW_ZL["fouls"],
)
ZG = dict(
    poss_lost_p90   = RAW_ZG["possession_lost"] * P90_ZG,
    touches_p90     = RAW_ZG["touches"]         * P90_ZG,
    passes_p90      = RAW_ZG["total_pass"]      * P90_ZG,
    pass_pct        = RAW_ZG["pass_pct"],
    recovery_p90    = RAW_ZG["ball_recovery"]   * P90_ZG,
    fouls_p90       = RAW_ZG["fouls"]           * P90_ZG,
)

# ─── Eixos do radar ───────────────────────────────────────────────────────────
METRICS = [
    "PERD. POSSE\np/90 ↓",  # ↓ = menos é melhor; eixo invertido
    "TOQUES\np/90",
    "PASSES\np/90",
    "% PASSE",
    "RECUPER.\np/90",
    "FALTAS\np/90 ↓",       # ↓ = menos é melhor; eixo invertido
]
KEYS = ["poss_lost_p90", "touches_p90", "passes_p90", "pass_pct", "recovery_p90", "fouls_p90"]
INVERTED = {k: False for k in KEYS}
INVERTED["poss_lost_p90"] = True
INVERTED["fouls_p90"]     = True

NORM_BOUNDS = {
    "poss_lost_p90": (0.0, max(ZL["poss_lost_p90"], ZG["poss_lost_p90"]) * 1.15),
    "touches_p90":   (0.0, max(ZL["touches_p90"],   ZG["touches_p90"])   * 1.15),
    "passes_p90":    (0.0, max(ZL["passes_p90"],     ZG["passes_p90"])   * 1.15),
    "pass_pct":      (80.0, 100.0),
    "recovery_p90":  (0.0, max(ZL["recovery_p90"],  ZG["recovery_p90"]) * 1.15),
    "fouls_p90":     (0.0, max(ZL["fouls_p90"],      ZG["fouls_p90"])   * 1.15),
}


def _norm(val: float, key: str) -> float:
    lo, hi = NORM_BOUNDS[key]
    n = max(0.0, min(1.0, (val - lo) / (hi - lo)))
    return (1.0 - n) if INVERTED[key] else n


def _radar_vals(player_dict):
    return [_norm(player_dict[k], k) for k in KEYS]


# ─── Funções de desenho ───────────────────────────────────────────────────────
def _header(fig):
    fig.text(0.50, 0.977, "SPORT RECIFE  ·  COPA DO NORDESTE 2026",
             color=YELLOW, fontsize=8, fontweight="bold",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center")

    fig.text(0.27, 0.956, "ZÉ LUCAS",
             color=YELLOW, fontsize=20, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
    fig.text(0.27, 0.937, "#58  ·  MEIA  ·  90MIN",
             color=LGRAY, fontsize=8, fontfamily="Arial",
             ha="center", va="center")

    fig.text(0.50, 0.947, "VS",
             color=GRAY, fontsize=14, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center")

    fig.text(0.73, 0.956, "ZÉ GABRIEL",
             color=BLUE, fontsize=20, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
    fig.text(0.73, 0.937, "#23  ·  MEIA  ·  57MIN",
             color=LGRAY, fontsize=8, fontfamily="Arial",
             ha="center", va="center")

    fig.text(0.50, 0.919, "SPORT  3 × 0  RETRÔ",
             color=YELLOW, fontsize=11, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="center", va="center")
    fig.text(0.50, 0.903, "R3  ·  COPA DO NORDESTE 2026  ·  09.04.2026",
             color=LGRAY, fontsize=7.5, fontfamily="Arial",
             ha="center", va="center")


def _radar_panel(ax):
    N      = len(METRICS)
    angles = np.linspace(np.pi / 2, np.pi / 2 + 2 * np.pi, N, endpoint=False)

    vals_zl = _radar_vals(ZL)
    vals_zg = _radar_vals(ZG)

    angles_c = np.append(angles, angles[0])
    vl_c     = vals_zl + [vals_zl[0]]
    vg_c     = vals_zg + [vals_zg[0]]

    ax.set_facecolor(BG)
    ax.set_xlim(-1.45, 1.45)
    ax.set_ylim(-1.45, 1.45)
    ax.set_aspect("equal")
    ax.axis("off")

    # ── Grade concêntrica ──
    for r_frac in [0.25, 0.50, 0.75, 1.0]:
        gx = r_frac * np.cos(angles_c)
        gy = r_frac * np.sin(angles_c)
        lw = 0.8 if r_frac == 1.0 else 0.4
        ax.plot(gx, gy, color="#333333", linewidth=lw, alpha=0.7, zorder=1)

    # ── Linhas de eixo ──
    for ang in angles:
        ax.plot([0, np.cos(ang)], [0, np.sin(ang)],
                color="#333333", linewidth=0.6, alpha=0.6, zorder=1)

    # ── Polígono Zé Lucas ──
    px_zl = [v * np.cos(a) for v, a in zip(vl_c, angles_c)]
    py_zl = [v * np.sin(a) for v, a in zip(vl_c, angles_c)]
    ax.fill(px_zl, py_zl, color=YELLOW, alpha=0.20, zorder=3)
    ax.plot(px_zl, py_zl, color=YELLOW, linewidth=2.2, alpha=0.95, zorder=4)
    ax.scatter([v * np.cos(a) for v, a in zip(vals_zl, angles)],
               [v * np.sin(a) for v, a in zip(vals_zl, angles)],
               s=35, color=YELLOW, zorder=5, edgecolors=BG, linewidths=0.8)

    # ── Polígono Zé Gabriel ──
    px_zg = [v * np.cos(a) for v, a in zip(vg_c, angles_c)]
    py_zg = [v * np.sin(a) for v, a in zip(vg_c, angles_c)]
    ax.fill(px_zg, py_zg, color=BLUE, alpha=0.18, zorder=3)
    ax.plot(px_zg, py_zg, color=BLUE, linewidth=2.2, alpha=0.95, zorder=4)
    ax.scatter([v * np.cos(a) for v, a in zip(vals_zg, angles)],
               [v * np.sin(a) for v, a in zip(vals_zg, angles)],
               s=35, color=BLUE, zorder=5, edgecolors=BG, linewidths=0.8)

    # ── Rótulos dos eixos ──
    LABEL_R = 1.20
    for metric, ang in zip(METRICS, angles):
        lx = LABEL_R * np.cos(ang)
        ly = LABEL_R * np.sin(ang)

        ha = "center"
        if np.cos(ang) > 0.3:
            ha = "left"
        elif np.cos(ang) < -0.3:
            ha = "right"
        va = "center"
        if np.sin(ang) > 0.3:
            va = "bottom"
        elif np.sin(ang) < -0.3:
            va = "top"

        ax.text(lx, ly, metric, color=LGRAY, fontsize=7.5,
                fontfamily="Arial", ha=ha, va=va, linespacing=1.2, zorder=6,
                path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])

    # ── Valores nos vértices (ZL à esquerda do eixo, ZG à direita) ──
    val_labels_zl = [
        f"{RAW_ZL['possession_lost']:.0f}",  # bruto (90 min)
        f"{ZL['touches_p90']:.0f}",
        f"{ZL['passes_p90']:.0f}",
        f"{ZL['pass_pct']:.1f}%",
        f"{ZL['recovery_p90']:.0f}",
        f"{RAW_ZL['fouls']:.0f}",
    ]
    val_labels_zg = [
        f"{ZG['poss_lost_p90']:.1f}",    # p/90
        f"{ZG['touches_p90']:.0f}",
        f"{ZG['passes_p90']:.0f}",
        f"{ZG['pass_pct']:.1f}%",
        f"{ZG['recovery_p90']:.1f}",
        f"{ZG['fouls_p90']:.1f}",
    ]

    for i, (ang, v_zl, v_zg) in enumerate(zip(angles, vals_zl, vals_zg)):
        perp = np.array([-np.sin(ang), np.cos(ang)])
        SIDE = 0.14

        ax.text(v_zl * np.cos(ang) + perp[0] * SIDE,
                v_zl * np.sin(ang) + perp[1] * SIDE,
                val_labels_zl[i],
                color=YELLOW, fontsize=6.5, fontfamily="Franklin Gothic Heavy",
                ha="center", va="center", zorder=7,
                path_effects=[pe.withStroke(linewidth=1.2, foreground=BG)])

        ax.text(v_zg * np.cos(ang) - perp[0] * SIDE,
                v_zg * np.sin(ang) - perp[1] * SIDE,
                val_labels_zg[i],
                color=BLUE, fontsize=6.5, fontfamily="Franklin Gothic Heavy",
                ha="center", va="center", zorder=7,
                path_effects=[pe.withStroke(linewidth=1.2, foreground=BG)])

    # ── Legenda ──
    legend_handles = [
        Line2D([0], [0], color=YELLOW, linewidth=2.0, label="Zé Lucas"),
        Line2D([0], [0], color=BLUE,   linewidth=2.0, label="Zé Gabriel"),
    ]
    ax.legend(handles=legend_handles, loc="lower center",
              bbox_to_anchor=(0.5, -0.06),
              fontsize=8, framealpha=0, facecolor=BG,
              labelcolor=LGRAY, edgecolor="none",
              handlelength=1.5, ncol=2, columnspacing=1.5)


def _stats_strip(ax):
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.axhline(0.98, color="#333333", linewidth=0.5, alpha=0.5)

    cols_x  = [0.07, 0.25, 0.41, 0.55, 0.68, 0.82, 0.96]
    headers = ["", "TOQUES", "PASSES", "PERD. POSSE", "RECUPER.", "FALTAS", "RATING"]
    note    = "  (*p/90 para Zé Gabriel — 57 min)"
    ax.text(0.01, 0.82, "STATS BRUTOS", color=LGRAY, fontsize=6.0,
            fontfamily="Arial", va="center")
    ax.text(0.25, 0.82, note, color="#555555", fontsize=5.8,
            fontfamily="Arial", va="center")

    for x, h in zip(cols_x[1:], headers[1:]):
        ax.text(x, 0.62, h, color=LGRAY, fontsize=5.8,
                fontfamily="Arial", ha="center", va="center")

    # ZL
    ax.text(cols_x[0], 0.38, "ZÉ LUCAS", color=YELLOW, fontsize=7,
            fontfamily="Franklin Gothic Heavy", va="center")
    zl_raw = [
        f"{RAW_ZL['touches']:.0f}",
        f"{RAW_ZL['total_pass']:.0f}",
        f"{RAW_ZL['possession_lost']:.0f}",
        f"{RAW_ZL['ball_recovery']:.0f}",
        f"{RAW_ZL['fouls']:.0f}",
        "6.8",
    ]
    for x, v in zip(cols_x[1:], zl_raw):
        ax.text(x, 0.38, v, color=YELLOW, fontsize=8,
                fontfamily="Franklin Gothic Heavy", ha="center", va="center")

    # ZG (bruto + p/90)
    ax.text(cols_x[0], 0.15, "ZÉ GABRIEL", color=BLUE, fontsize=7,
            fontfamily="Franklin Gothic Heavy", va="center")
    zg_raw  = [f"{RAW_ZG['touches']:.0f}", f"{RAW_ZG['total_pass']:.0f}",
               f"{RAW_ZG['possession_lost']:.0f}", f"{RAW_ZG['ball_recovery']:.0f}",
               f"{RAW_ZG['fouls']:.0f}", "6.6"]
    zg_p90  = [f"{RAW_ZG['touches']*P90_ZG:.0f}*",
               f"{RAW_ZG['total_pass']*P90_ZG:.0f}*",
               f"{RAW_ZG['possession_lost']*P90_ZG:.1f}*",
               f"{RAW_ZG['ball_recovery']*P90_ZG:.1f}*",
               f"{RAW_ZG['fouls']*P90_ZG:.1f}*",
               "—"]
    for x, v_raw, v_p90 in zip(cols_x[1:], zg_raw, zg_p90):
        ax.text(x, 0.26, v_raw, color=BLUE, fontsize=8,
                fontfamily="Franklin Gothic Heavy", ha="center", va="center")
        ax.text(x, 0.07, v_p90, color="#5588aa", fontsize=5.8,
                fontfamily="Arial", ha="center", va="center")


def _footer(fig, ax_ref):
    if LOGO_PATH.exists():
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((40, 40), Image.LANCZOS)
        )
        ab = AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0),
            (0.07, 0.025), xycoords="figure fraction",
            frameon=False, zorder=10,
        )
        ax_ref.add_artist(ab)

    fig.text(0.14, 0.025, "@SportRecifeLab",
             color=YELLOW, fontsize=8, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")
    fig.text(0.97, 0.025, "Dados: SofaScore",
             color=LGRAY, fontsize=7, fontfamily="Arial",
             ha="right", va="center")


# ─── Main ─────────────────────────────────────────────────────────────────────
def generate_card(output_path: str = "card_ze_lucas_ze_gabriel_retro.png"):
    fig = plt.figure(figsize=(7.0, 9.0), dpi=130)
    fig.patch.set_facecolor(BG)

    gs = fig.add_gridspec(
        2, 1,
        left=0.04, right=0.96,
        top=0.895, bottom=0.060,
        hspace=0.04,
        height_ratios=[6.5, 1.3],
    )

    ax_radar = fig.add_subplot(gs[0])
    ax_stats = fig.add_subplot(gs[1])

    _header(fig)
    _radar_panel(ax_radar)
    _stats_strip(ax_stats)
    _footer(fig, ax_stats)

    out = Path(output_path)
    plt.savefig(out, dpi=130, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Card salvo: {out}")
    return out


if __name__ == "__main__":
    generate_card()
