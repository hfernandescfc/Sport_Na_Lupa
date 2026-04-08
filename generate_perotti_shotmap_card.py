"""
Card de mapa de finalizações — Perotti · Londrina 1×2 Sport · R3 Série B 2026
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
from mplsoccer import Pitch
from PIL import Image

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG          = "#0d0d0d"
PITCH_COLOR = "#0e3d1f"
LINE_COLOR  = "#2a7a3a"
YELLOW      = "#F5C400"
RED         = "#E04040"
BLUE        = "#4A90D9"
GRAY        = "#333333"
LGRAY       = "#888888"
WHITE       = "#FFFFFF"

LOGO_PATH = Path(__file__).parent / "sportrecifelab_avatar.png"

# ─── Dados ───────────────────────────────────────────────────────────────────
# Coordenadas SofaScore: x = % distância do gol (0=gol, 100=outro extremo)
#                        y = % lateral (0=esq, 100=dir)
SHOTS = [
    {"min": 43, "type": "save",  "xg": 0.173, "coord": (5.4, 60.5)},
    {"min": 65, "type": "block", "xg": 0.488, "coord": (5.0, 50.7)},
    {"min": 70, "type": "miss",  "xg": 0.024, "coord": (23.6, 45.7)},
    {"min": 87, "type": "goal",  "xg": 0.171, "coord": (5.2, 39.3)},
]

SHOT_COLOR  = {"goal": YELLOW, "save": BLUE,  "block": RED,   "miss": LGRAY}
SHOT_LABEL  = {"goal": "GOL",  "save": "DEF.", "block": "BLQ.", "miss": "FORA"}
SHOT_MARKER = {"goal": "*",    "save": "o",   "block": "X",   "miss": "^"}
SHOT_MS     = {"goal": 280,    "save": 130,   "block": 130,   "miss": 110}

# Escala de raio dos círculos xG (em unidades da pitch StatsBomb)
XG_SCALE = 14


def _to_sb(x_ss, y_ss):
    """SofaScore → StatsBomb (120×80)."""
    return 120 - (x_ss / 100 * 120), (y_ss / 100 * 80)


def generate_card(output_path: str = "card_perotti_shotmap.png"):
    fig = plt.figure(figsize=(7.0, 8.5), dpi=130)
    fig.patch.set_facecolor(BG)

    # Layout: header via fig.text, pitch no centro, legenda e footer abaixo
    ax = fig.add_axes([0.03, 0.10, 0.94, 0.72])

    # ── Pitch ─────────────────────────────────────────────────────────────────
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color=PITCH_COLOR,
        line_color=LINE_COLOR,
        linewidth=1.0,
        goal_type="box",
        corner_arcs=True,
        half=True,
    )
    pitch.draw(ax=ax)

    # Zoom no terço final — inclui o chute mais recuado (x=23.6 → sb_x≈91.7)
    ax.set_xlim(78, 122)
    ax.set_ylim(-3, 83)

    # ── Finalizações ──────────────────────────────────────────────────────────
    for shot in SHOTS:
        sx, sy = _to_sb(*shot["coord"])
        color  = SHOT_COLOR[shot["type"]]
        r      = shot["xg"] * XG_SCALE

        # Círculo proporcional ao xG
        circle = plt.Circle((sx, sy), r,
                             color=color, alpha=0.15, zorder=3, linewidth=0)
        ax.add_patch(circle)
        # Borda do círculo
        circle_edge = plt.Circle((sx, sy), r,
                                  color=color, alpha=0.40, fill=False,
                                  linewidth=0.9, zorder=4)
        ax.add_patch(circle_edge)

        # Marcador central
        ax.scatter(sx, sy,
                   s=SHOT_MS[shot["type"]],
                   marker=SHOT_MARKER[shot["type"]],
                   color=color,
                   edgecolors=WHITE, linewidths=0.7,
                   zorder=5)

        # Linha do marcador até o label (para não sobrepor ao círculo)
        label_offset = r + 1.8

        # Posiciona label evitando sobreposição entre chutes próximos
        if shot["min"] == 65:
            lx, ly = sx - label_offset - 1, sy + 1.5
            ha = "right"
        elif shot["min"] == 43:
            lx, ly = sx + label_offset + 1, sy + 1.5
            ha = "left"
        elif shot["min"] == 87:
            lx, ly = sx - label_offset - 1, sy - 2
            ha = "right"
        else:  # 70 (recuado)
            lx, ly = sx, sy + label_offset + 1.5
            ha = "center"

        label = f"{shot['min']}'  {SHOT_LABEL[shot['type']]}\nxG {shot['xg']:.3f}"
        ax.text(lx, ly, label,
                color=color, fontsize=7.5, fontfamily="Arial",
                ha=ha, va="center", linespacing=1.4, zorder=6,
                path_effects=[pe.withStroke(linewidth=2.0, foreground=BG)])

    # ── Header ────────────────────────────────────────────────────────────────
    fig.text(0.50, 0.965, "SPORT RECIFE  ·  SÉRIE B 2026",
             color=YELLOW, fontsize=8, fontweight="bold",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center")
    fig.text(0.50, 0.942, "PEROTTI  #9  ·  ATACANTE  ·  90MIN",
             color=WHITE, fontsize=20, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
    fig.text(0.50, 0.922, "LONDRINA  1 × 2  SPORT",
             color=YELLOW, fontsize=10.5, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="center", va="center")
    fig.text(0.50, 0.906, "R3  ·  SÉRIE B 2026  ·  04.04.2026",
             color=LGRAY, fontsize=7.5, fontfamily="Arial",
             ha="center", va="center")

    # ── Legenda ───────────────────────────────────────────────────────────────
    legend_items = [
        Line2D([0],[0], marker="*", color="w", markerfacecolor=YELLOW,
               markersize=10, label="GOL", linestyle="None"),
        Line2D([0],[0], marker="o", color="w", markerfacecolor=BLUE,
               markersize=8,  label="DEFENDIDA", linestyle="None"),
        Line2D([0],[0], marker="X", color="w", markerfacecolor=RED,
               markersize=8,  label="BLOQUEADA", linestyle="None"),
        Line2D([0],[0], marker="^", color="w", markerfacecolor=LGRAY,
               markersize=8,  label="PARA FORA", linestyle="None"),
    ]
    legend = ax.legend(
        handles=legend_items,
        loc="lower left", bbox_to_anchor=(0.0, 0.0),
        ncol=4, fontsize=7, framealpha=0.2,
        facecolor=BG, labelcolor=LGRAY, edgecolor=GRAY,
        handlelength=1.0, borderpad=0.7, columnspacing=1.0,
    )

    # Nota xG circle scale
    fig.text(0.50, 0.082,
             "tamanho do círculo proporcional ao xG da finalização",
             color="#555555", fontsize=6.5, fontfamily="Arial",
             ha="center", va="center")

    # ── Footer ────────────────────────────────────────────────────────────────
    if LOGO_PATH.exists():
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((38, 38), Image.LANCZOS)
        )
        ab = AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0),
            (0.07, 0.030), xycoords="figure fraction",
            frameon=False, zorder=10,
        )
        ax.add_artist(ab)

    fig.text(0.14, 0.030, "@SportRecifeLab",
             color=YELLOW, fontsize=8, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")
    fig.text(0.97, 0.030, "Dados: SofaScore",
             color=LGRAY, fontsize=7, fontfamily="Arial",
             ha="right", va="center")

    out = Path(output_path)
    plt.savefig(out, dpi=130, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Card salvo: {out}")
    return out


if __name__ == "__main__":
    generate_card()
