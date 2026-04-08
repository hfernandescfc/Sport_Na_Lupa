"""
Gerador de card de heatmap para Perotti x Londrina — @SportRecifeLab.
Usa Pitch horizontal (landscape) com x-axis invertido (ataque para a esquerda).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from mplsoccer import Pitch
from PIL import Image
import numpy as np

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG           = "#0d0d0d"
PITCH_COLOR  = "#0e3d1f"
LINE_COLOR   = "#2a7a3a"
YELLOW       = "#F5C400"
GRAY         = "#888888"
LGRAY        = "#AAAAAA"
WHITE        = "#FFFFFF"

BASE_DIR  = Path(__file__).parent
LOGO_PATH = BASE_DIR / "sportrecifelab_avatar.png"
DATA_PATH = BASE_DIR / "data/raw/sofascore/perotti_londrina_heatmap.json"
OUT_PATH  = BASE_DIR / "card_perotti_heatmap.png"

# ─── Dados ───────────────────────────────────────────────────────────────────
with open(DATA_PATH, encoding="utf-8") as f:
    raw = json.load(f)

points = raw.get("heatmap", raw)

# Mapeamento coordenadas:
# x=0  → próprio gol  (defesa)
# x=100 → gol adversário (ataque)
# Estatsbomb: comprimento 0-120, largura 0-80
# pitch_x = x * 1.2   → 0-120
# pitch_y = y * 0.8   → 0-80
# invert_xaxis() → x=120 (ataque) vai para ESQUERDA

pitch_xs = np.array([p["x"] * 1.2 for p in points])
pitch_ys = np.array([p["y"] * 0.8 for p in points])

# ─── Figura ──────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(8.5, 6.0), dpi=120)
fig.patch.set_facecolor(BG)

# Área do pitch — deixa espaço para header (topo) e footer (base)
# [left, bottom, width, height] em fração da figura
ax = fig.add_axes([0.03, 0.10, 0.94, 0.76])

pitch = Pitch(
    pitch_type="statsbomb",
    pitch_color=PITCH_COLOR,
    line_color=LINE_COLOR,
    linewidth=1.2,
    goal_type="box",
    corner_arcs=True,
)
pitch.draw(ax=ax)

# Inverter eixo x → ataque vai para a ESQUERDA
ax.invert_xaxis()

# Colormap customizado: transparente nas bordas → amarelo → laranja → vermelho opaco
# Permite que o verde do campo apareça nas zonas de baixa densidade
_cmap_colors = [
    (0.055, 0.239, 0.122, 0.00),  # verde do campo, totalmente transparente
    (0.055, 0.239, 0.122, 0.00),  # mantém transparente até ~20% de densidade
    (0.95,  0.85,  0.00,  0.45),  # amarelo, semi-transparente
    (0.95,  0.45,  0.05,  0.78),  # laranja
    (0.72,  0.05,  0.05,  0.92),  # vermelho escuro, quase opaco
]
_heat_cmap = LinearSegmentedColormap.from_list("football_heat", _cmap_colors, N=256)

# KDE plot — bw_adjust calibrado para separar zonas sem explodir
pitch.kdeplot(
    pitch_xs, pitch_ys, ax=ax,
    cmap=_heat_cmap,
    fill=True,
    levels=45,
    bw_adjust=0.30,
    zorder=2,
    thresh=0.22,
)

# ─── Seta de direção de ataque — posicionada no header da figura ─────────────
# Usando FancyArrowPatch em coordenadas de figura
from matplotlib.patches import FancyArrowPatch
arrow = FancyArrowPatch(
    posA=(0.55, 0.885), posB=(0.35, 0.885),
    transform=fig.transFigure,
    arrowstyle="-|>",
    color=WHITE,
    lw=1.8,
    mutation_scale=14,
)
fig.add_artist(arrow)

# ─── Header ──────────────────────────────────────────────────────────────────
fig.text(
    0.50, 0.955,
    "SPORT RECIFE  ·  SÉRIE B 2026",
    color=YELLOW, fontsize=8.5, fontweight="bold",
    fontfamily="Franklin Gothic Heavy",
    ha="center", va="center",
)

fig.text(
    0.50, 0.925,
    "PEROTTI",
    color=WHITE, fontsize=28, fontweight="black",
    fontfamily="Franklin Gothic Heavy",
    ha="center", va="center",
    path_effects=[pe.withStroke(linewidth=2, foreground=BG)],
)

fig.text(
    0.50, 0.898,
    "MAPA DE CALOR  ·  ATACANTE  ·  LONDRINA 1×2 SPORT  ·  R3",
    color=LGRAY, fontsize=7.5, fontfamily="Arial",
    ha="center", va="center",
)

# ─── Footer ──────────────────────────────────────────────────────────────────
if LOGO_PATH.exists():
    logo_arr = np.array(
        Image.open(LOGO_PATH).convert("RGBA").resize((46, 46), Image.LANCZOS)
    )
    logo_ab = AnnotationBbox(
        OffsetImage(logo_arr, zoom=1.0),
        (0.09, 0.038),
        xycoords="figure fraction",
        frameon=False,
        zorder=10,
    )
    ax.add_artist(logo_ab)

fig.text(
    0.175, 0.038, "@SportRecifeLab",
    color=YELLOW, fontsize=8.5, fontfamily="Franklin Gothic Heavy",
    fontweight="bold", ha="left", va="center",
)

fig.text(
    0.97, 0.038, "Dados: SofaScore",
    color=GRAY, fontsize=7.2, fontfamily="Arial",
    ha="right", va="center",
)

# ─── Salvar ──────────────────────────────────────────────────────────────────
plt.savefig(OUT_PATH, dpi=120, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
plt.close()
print(f"Salvo: {OUT_PATH}")
