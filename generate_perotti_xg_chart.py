"""
Gráfico isolado de xG acumulado — Perotti · Londrina 1×2 Sport · R3 Série B 2026
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

BG     = "#0d0d0d"
YELLOW = "#F5C400"
RED    = "#E04040"
BLUE   = "#4A90D9"
GRAY   = "#444444"
LGRAY  = "#888888"
WHITE  = "#FFFFFF"

LOGO_PATH = Path(__file__).parent / "sportrecifelab_avatar.png"

SHOTS = [
    {"min": 43, "type": "save",  "xg": 0.173},
    {"min": 65, "type": "block", "xg": 0.488},
    {"min": 70, "type": "miss",  "xg": 0.024},
    {"min": 87, "type": "goal",  "xg": 0.171},
]
SHOT_COLOR  = {"goal": YELLOW, "save": BLUE,  "block": RED,   "miss": LGRAY}
SHOT_LABEL  = {"goal": "GOL",  "save": "DEF.", "block": "BLQ.", "miss": "FORA"}
SHOT_MARKER = {"goal": "*",    "save": "o",   "block": "X",   "miss": "^"}
SHOT_SIZE   = {"goal": 300,    "save": 120,   "block": 120,   "miss": 100}

TOTAL_XG = sum(s["xg"] for s in SHOTS)


def generate_chart(output_path: str = "chart_perotti_xg.png"):
    fig, ax = plt.subplots(figsize=(7.0, 5.0), dpi=130)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    # Step chart: (x, cumxg) antes e depois de cada chute
    step_x = [0]
    step_y = [0.0]
    acc = 0.0
    for s in SHOTS:
        step_x += [s["min"], s["min"]]
        step_y += [acc, acc + s["xg"]]
        acc += s["xg"]
    step_x.append(90)
    step_y.append(acc)

    ax.plot(step_x, step_y, color=YELLOW, linewidth=2.2,
            alpha=0.90, zorder=3, solid_capstyle="round")
    ax.fill_between(step_x, step_y, alpha=0.10, color=YELLOW, zorder=2)

    # Linha "1 gol esperado"
    ax.axhline(1.0, color=LGRAY, linewidth=0.8, linestyle="--", alpha=0.4, zorder=1)
    ax.text(91, 1.015, "1 GOL ESPERADO",
            color=LGRAY, fontsize=6.5, fontfamily="Arial",
            ha="right", va="bottom")

    # Marcadores e labels de cada chute
    cum = 0.0
    for s in SHOTS:
        cum += s["xg"]
        color  = SHOT_COLOR[s["type"]]
        marker = SHOT_MARKER[s["type"]]

        ax.scatter(s["min"], cum, s=SHOT_SIZE[s["type"]], marker=marker,
                   color=color, edgecolors=WHITE, linewidths=0.8, zorder=5)

        # Offset: 43' e 87' acima; 65' abaixo; 70' acima (evita sobreposição)
        v_offset = {43: 0.06, 65: -0.11, 70: 0.06, 87: 0.06}.get(s["min"], 0.06)
        va = "bottom" if v_offset > 0 else "top"
        label = f"{s['min']}'  {SHOT_LABEL[s['type']]}\n+{s['xg']:.3f} xG"
        ax.text(s["min"], cum + v_offset, label,
                color=color, fontsize=7.2, fontfamily="Arial",
                ha="center", va=va, linespacing=1.35, zorder=6,
                path_effects=[pe.withStroke(linewidth=1.8, foreground=BG)])

    # xG total
    ax.text(89, TOTAL_XG + 0.07,
            f"xG TOTAL: {TOTAL_XG:.2f}  ·  GOLS: 1",
            color=YELLOW, fontsize=8.5, fontfamily="Franklin Gothic Heavy",
            fontweight="bold", ha="right", va="bottom",
            path_effects=[pe.withStroke(linewidth=1.8, foreground=BG)])

    # Título
    ax.set_title("xG ACUMULADO POR FINALIZAÇÃO  ·  PEROTTI  ·  LONDRINA 1×2 SPORT",
                 color=LGRAY, fontsize=8, fontfamily="Arial", pad=10, loc="left")

    # Eixos
    ax.set_xlim(0, 93)
    ax.set_ylim(-0.05, 1.15)
    ax.set_xlabel("MINUTO", color=LGRAY, fontsize=7.5, fontfamily="Arial", labelpad=5)
    ax.set_ylabel("xG ACUMULADO", color=LGRAY, fontsize=7.5, fontfamily="Arial", labelpad=6)
    ax.set_xticks([0, 43, 65, 70, 87, 90])
    ax.set_xticklabels(["0", "43'", "65'", "70'", "87'", "90'"],
                       color=LGRAY, fontsize=7)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.tick_params(colors=LGRAY, labelsize=7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["bottom", "left"]].set_color(GRAY)
    for gv in [0.25, 0.5, 0.75]:
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

    # Footer
    fig.subplots_adjust(bottom=0.13, left=0.10, right=0.97, top=0.92)

    if LOGO_PATH.exists():
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((36, 36), Image.LANCZOS)
        )
        ab = AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0),
            (0.07, 0.04), xycoords="figure fraction",
            frameon=False, zorder=10,
        )
        ax.add_artist(ab)

    fig.text(0.14, 0.04, "@SportRecifeLab",
             color=YELLOW, fontsize=7.5, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")
    fig.text(0.97, 0.04, "Dados: SofaScore",
             color=LGRAY, fontsize=6.5, fontfamily="Arial",
             ha="right", va="center")

    out = Path(output_path)
    plt.savefig(out, dpi=130, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Gráfico salvo: {out}")
    return out


if __name__ == "__main__":
    generate_chart()
