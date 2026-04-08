"""
Card de análise de Perotti — Londrina 1×2 Sport · R3 Série B 2026
@SportRecifeLab

Painéis:
  1. Header
  2. Stats (grid de métricas-chave)
  3. xG acumulado por minuto (step chart com marcadores por resultado)
  4. Footer
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
from PIL import Image

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
RED    = "#E04040"
BLUE   = "#4A90D9"
GRAY   = "#444444"
LGRAY  = "#AAAAAA"
WHITE  = "#FFFFFF"

LOGO_PATH = Path(__file__).parent / "sportrecifelab_avatar.png"

# ─── Dados ───────────────────────────────────────────────────────────────────
SHOTS = [
    {"min": 43, "type": "save",  "xg": 0.173},
    {"min": 65, "type": "block", "xg": 0.488},
    {"min": 70, "type": "miss",  "xg": 0.024},
    {"min": 87, "type": "goal",  "xg": 0.171},
]

SHOT_COLOR  = {"goal": YELLOW, "save": BLUE,  "block": RED,  "miss": LGRAY}
SHOT_LABEL  = {"goal": "GOL",  "save": "DEF.", "block": "BLQ.", "miss": "FORA"}
SHOT_MARKER = {"goal": "*",    "save": "o",   "block": "X",   "miss": "^"}
SHOT_SIZE   = {"goal": 260,    "save": 110,   "block": 110,   "miss": 90}

STATS_GRID = [
    # (label, valor, destaque?)
    ("TOQUES",      "26",    False),
    ("PASSES",      "9/12",  False),
    ("ACERTO PASS", "75%",   False),
    ("CHUTES",      "4",     False),
    ("GOL",         "1",     True),
    ("xG TOTAL",    "0.86",  True),
    ("RECUPER.",    "4",     False),
    ("RATING",      "6.7",   False),
]

TOTAL_XG = sum(s["xg"] for s in SHOTS)


# ─── Helpers ─────────────────────────────────────────────────────────────────
def _header(fig):
    fig.text(0.50, 0.977, "SPORT RECIFE  ·  SÉRIE B 2026",
             color=YELLOW, fontsize=8, fontweight="bold",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center")
    fig.text(0.50, 0.955, "PEROTTI  #9  ·  ATACANTE  ·  90MIN",
             color=WHITE, fontsize=21, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
    fig.text(0.50, 0.936, "LONDRINA  1 × 2  SPORT",
             color=YELLOW, fontsize=11, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="center", va="center")
    fig.text(0.50, 0.919, "R3  ·  SÉRIE B 2026  ·  04.04.2026",
             color=LGRAY, fontsize=7.5, fontfamily="Arial",
             ha="center", va="center")


def _stats_panel(ax):
    ax.set_facecolor(BG)
    ax.set_xlim(0, len(STATS_GRID))
    ax.set_ylim(0, 1)
    ax.axis("off")

    cols = len(STATS_GRID)
    for i, (label, value, highlight) in enumerate(STATS_GRID):
        cx = i + 0.5
        vcolor = YELLOW if highlight else WHITE

        # Separador vertical (exceto último)
        if i < cols - 1:
            ax.axvline(i + 1, color=GRAY, linewidth=0.6, alpha=0.5,
                       ymin=0.1, ymax=0.9)

        ax.text(cx, 0.68, value, color=vcolor, fontsize=15,
                fontfamily="Franklin Gothic Heavy", fontweight="bold",
                ha="center", va="center")
        ax.text(cx, 0.25, label, color=LGRAY, fontsize=6.5,
                fontfamily="Arial", ha="center", va="center")

    # Borda superior e inferior
    ax.axhline(0.98, color=GRAY, linewidth=0.5, alpha=0.4)
    ax.axhline(0.02, color=GRAY, linewidth=0.5, alpha=0.4)


def _xg_timeline(ax):
    ax.set_facecolor(BG)

    # Pontos do step chart: começa em 0, sobe a cada chute
    minutes = [0] + [s["min"] for s in SHOTS]
    cumxg   = [0]
    acc = 0.0
    for s in SHOTS:
        acc += s["xg"]
        cumxg.append(acc)

    # Step chart (post = degrau sobe ao chegar no minuto)
    step_x = [0]
    step_y = [0]
    for i in range(1, len(minutes)):
        step_x += [minutes[i], minutes[i]]
        step_y += [step_y[-1], cumxg[i]]

    ax.plot(step_x, step_y, color=YELLOW, linewidth=1.8,
            alpha=0.85, zorder=3, solid_capstyle="round")

    # Área sob a curva
    ax.fill_between(step_x, step_y, alpha=0.12, color=YELLOW, zorder=2)

    # Linha de referência: 1 gol esperado
    ax.axhline(1.0, color=LGRAY, linewidth=0.7, linestyle="--",
               alpha=0.45, zorder=1)
    ax.text(89, 1.015, "1 GOL ESPERADO", color=LGRAY, fontsize=6,
            fontfamily="Arial", ha="right", va="bottom")

    # Marcadores de cada chute
    for s in SHOTS:
        acc_at = sum(x["xg"] for x in SHOTS if x["min"] <= s["min"])
        color  = SHOT_COLOR[s["type"]]
        marker = SHOT_MARKER[s["type"]]
        msize  = SHOT_SIZE[s["type"]]

        ax.scatter(s["min"], acc_at, s=msize, marker=marker,
                   color=color, edgecolors=WHITE, linewidths=0.7, zorder=5)

        # Label: minuto + resultado + xG do chute
        label = f"{s['min']}' · {SHOT_LABEL[s['type']]}\n+{s['xg']:.3f} xG"
        # Alterna posição vertical para evitar sobreposição
        v_offset = 0.06 if s["min"] in (43, 87) else -0.10
        va = "bottom" if v_offset > 0 else "top"
        ax.text(s["min"], acc_at + v_offset, label,
                color=color, fontsize=6.8, fontfamily="Arial",
                ha="center", va=va, linespacing=1.35, zorder=6,
                path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])

    # xG total final
    ax.text(88, TOTAL_XG + 0.06,
            f"xG TOTAL\n{TOTAL_XG:.2f}",
            color=YELLOW, fontsize=7.5, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="right", va="bottom",
            path_effects=[pe.withStroke(linewidth=1.5, foreground=BG)])

    # Eixos
    ax.set_xlim(0, 93)
    ax.set_ylim(-0.05, 1.10)
    ax.set_xlabel("MINUTO", color=LGRAY, fontsize=7, fontfamily="Arial", labelpad=4)
    ax.set_ylabel("xG ACUMULADO", color=LGRAY, fontsize=7, fontfamily="Arial", labelpad=6)
    ax.tick_params(colors=LGRAY, labelsize=6.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color(GRAY)

    # Xticks nos minutos de chute + 0 e 90
    ax.set_xticks([0, 43, 65, 70, 87, 90])
    ax.set_xticklabels(["0", "43'", "65'", "70'", "87'", "90'"],
                       color=LGRAY, fontsize=6.5)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])

    # Linhas de grade suaves
    for gv in [0.25, 0.5, 0.75, 1.0]:
        ax.axhline(gv, color=GRAY, linewidth=0.3, alpha=0.5, zorder=1)

    # Legenda
    legend_handles = [
        Line2D([0], [0], marker="*", color="w", markerfacecolor=YELLOW,
               markersize=9, label="GOL", linestyle="None"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor=BLUE,
               markersize=7, label="DEFENDIDA", linestyle="None"),
        Line2D([0], [0], marker="X", color="w", markerfacecolor=RED,
               markersize=7, label="BLOQUEADA", linestyle="None"),
        Line2D([0], [0], marker="^", color="w", markerfacecolor=LGRAY,
               markersize=7, label="PARA FORA", linestyle="None"),
    ]
    ax.legend(handles=legend_handles, loc="upper left",
              fontsize=6.5, framealpha=0.2, facecolor=BG,
              labelcolor=LGRAY, edgecolor=GRAY, handlelength=1,
              borderpad=0.6, labelspacing=0.5)

    ax.set_title("xG ACUMULADO POR FINALIZAÇÃO", color=LGRAY, fontsize=7.5,
                 fontfamily="Arial", pad=6, loc="left")


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
def generate_card(output_path: str = "card_perotti_londrina_r3.png"):
    fig = plt.figure(figsize=(7.0, 8.5), dpi=130)
    fig.patch.set_facecolor(BG)

    gs = fig.add_gridspec(
        2, 1,
        left=0.09, right=0.97,
        top=0.905, bottom=0.065,
        hspace=0.28,
        height_ratios=[1, 3.8],
    )

    ax_stats = fig.add_subplot(gs[0])
    ax_xg    = fig.add_subplot(gs[1])

    _header(fig)
    _stats_panel(ax_stats)
    _xg_timeline(ax_xg)
    _footer(fig, ax_xg)

    out = Path(output_path)
    plt.savefig(out, dpi=130, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Card salvo: {out}")
    return out


if __name__ == "__main__":
    generate_card()
