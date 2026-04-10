"""
Card de heatmap de diferença — Zé Lucas vs Zé Gabriel · Sport 3×0 Retrô · Copa NE R3 2026
@SportRecifeLab

Heatmap de diferença normalizado (ambas as densidades integram a 1):
  AMARELO → zonas com maior presença proporcional de Zé Lucas
  AZUL    → zonas com maior presença proporcional de Zé Gabriel
  Neutro  → presença similar (transparente sobre o campo verde)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
from mplsoccer import Pitch
from PIL import Image
import numpy as np
from scipy.stats import gaussian_kde
from scipy.ndimage import gaussian_filter

# ─── Paleta ───────────────────────────────────────────────────────────────────
BG          = "#0d0d0d"
PITCH_COLOR = "#0e3d1f"
LINE_COLOR  = "#2a7a3a"
YELLOW      = "#F5C400"
BLUE        = "#4A90D9"
LGRAY       = "#AAAAAA"
GRAY        = "#555555"
WHITE       = "#FFFFFF"

BASE_DIR  = Path(__file__).parent
LOGO_PATH = BASE_DIR / "sportrecifelab_avatar.png"
DATA_ZL   = BASE_DIR / "data/raw/sofascore/discovery/heatmap_15871851_ze_lucas.json"
DATA_ZG   = BASE_DIR / "data/raw/sofascore/discovery/heatmap_15871851_ze_gabriel.json"
OUT_PATH  = BASE_DIR / "card_ze_lucas_ze_gabriel_heatmap.png"


# ─── Dados ────────────────────────────────────────────────────────────────────
def _load(path: Path):
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    pts = d.get("heatmap", d)
    xs = np.array([p["x"] * 1.2 for p in pts])   # 0-100 → 0-120 (StatsBomb)
    ys = np.array([p["y"] * 0.8 for p in pts])   # 0-100 → 0-80
    return xs, ys

xs_zl, ys_zl = _load(DATA_ZL)
xs_zg, ys_zg = _load(DATA_ZG)


# ─── Grade de densidade ───────────────────────────────────────────────────────
GRID_W, GRID_H = 240, 160   # resolução da grade (proporção 120:80)

gx = np.linspace(0, 120, GRID_W)
gy = np.linspace(0,  80, GRID_H)
GX, GY = np.meshgrid(gx, gy)
grid_pts = np.vstack([GX.ravel(), GY.ravel()])

def _kde(xs, ys, bw=0.28) -> np.ndarray:
    """KDE normalizado (soma = 1) sobre a grade."""
    kde = gaussian_kde(np.vstack([xs, ys]), bw_method=bw)
    d = kde(grid_pts).reshape(GRID_H, GRID_W)
    d /= d.sum()
    return d

dens_zl = _kde(xs_zl, ys_zl)
dens_zg = _kde(xs_zg, ys_zg)

# Diferença: + → ZL domina / − → ZG domina
diff = dens_zl - dens_zg
diff = gaussian_filter(diff, sigma=2.0)   # suavização leve

# Limites simétricos (percentil 98 para descartar picos extremos)
vmax = float(np.percentile(np.abs(diff), 98))


# ─── Colormap divergente ──────────────────────────────────────────────────────
# 0.0 → BLUE opaco / 0.5 → transparente (campo) / 1.0 → YELLOW opaco
_r_b, _g_b, _b_b = 0.29, 0.56, 0.85   # BLUE  (#4A90D9)
_r_y, _g_y, _b_y = 0.96, 0.77, 0.00   # YELLOW (#F5C400)
_r_p, _g_p, _b_p = 0.055, 0.239, 0.12  # PITCH_COLOR (neutro)

cmap_diff = LinearSegmentedColormap.from_list(
    "diff",
    [
        (_r_b, _g_b, _b_b, 0.88),
        (_r_b, _g_b, _b_b, 0.50),
        (_r_p, _g_p, _b_p, 0.00),   # totalmente transparente no neutro
        (_r_y, _g_y, _b_y, 0.50),
        (_r_y, _g_y, _b_y, 0.88),
    ],
    N=512,
)
norm_diff = TwoSlopeNorm(vmin=-vmax, vcenter=0.0, vmax=vmax)


# ─── Figura ───────────────────────────────────────────────────────────────────
fig = plt.figure(figsize=(9.5, 7.2), dpi=120)
fig.patch.set_facecolor(BG)

# Axes do pitch: [left, bottom, width, height]
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
ax.invert_xaxis()   # ataque para a esquerda (mesma convenção dos outros cards)

# Overlay do heatmap de diferença (extent em coordenadas StatsBomb)
ax.imshow(
    diff,
    extent=[0, 120, 0, 80],
    origin="lower",
    aspect="auto",
    cmap=cmap_diff,
    norm=norm_diff,
    zorder=2,
    interpolation="bilinear",
)


# ─── Header ───────────────────────────────────────────────────────────────────
fig.text(0.50, 0.960, "SPORT RECIFE  ·  COPA DO NORDESTE 2026",
         color=YELLOW, fontsize=8.5, fontweight="bold",
         fontfamily="Franklin Gothic Heavy", ha="center", va="center")

# Zé Lucas — esquerda
fig.text(0.28, 0.930, "ZÉ LUCAS",
         color=YELLOW, fontsize=20, fontweight="black",
         fontfamily="Franklin Gothic Heavy", ha="center", va="center",
         path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
fig.text(0.28, 0.910, "#58  ·  MEIA  ·  90MIN",
         color=LGRAY, fontsize=7.5, fontfamily="Arial",
         ha="center", va="center")

# VS
fig.text(0.50, 0.920, "VS",
         color=GRAY, fontsize=13, fontweight="black",
         fontfamily="Franklin Gothic Heavy", ha="center", va="center")

# Zé Gabriel — direita
fig.text(0.72, 0.930, "ZÉ GABRIEL",
         color=BLUE, fontsize=20, fontweight="black",
         fontfamily="Franklin Gothic Heavy", ha="center", va="center",
         path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
fig.text(0.72, 0.910, "#23  ·  MEIA  ·  57MIN",
         color=LGRAY, fontsize=7.5, fontfamily="Arial",
         ha="center", va="center")

# Match info — centralizado
fig.text(0.50, 0.895, "SPORT  3 × 0  RETRÔ   ·   MAPA DE DIFERENÇA DE POSICIONAMENTO",
         color=LGRAY, fontsize=7.2, fontfamily="Arial",
         ha="center", va="center")

# Seta de ataque — desenhada dentro do pitch para não conflitar com o header
# Após invert_xaxis(), x maior aparece à esquerda → xy=(70,76) fica à esquerda de xytext=(52,76)
ax.annotate(
    "", xy=(70, 76), xytext=(52, 76),
    arrowprops=dict(arrowstyle="-|>", color=WHITE, lw=1.5, mutation_scale=11),
    zorder=5,
)
ax.text(61, 79, "ATAQUE", color=WHITE, fontsize=6.5, fontfamily="Arial",
        ha="center", va="bottom", zorder=5)


# ─── Legenda inline (sobre o campo, canto inferior) ──────────────────────────
legend_handles = [
    Line2D([0], [0], marker="s", color="none", markerfacecolor=YELLOW,
           markersize=10, label="Maior presença — Zé Lucas", alpha=0.85),
    Line2D([0], [0], marker="s", color="none", markerfacecolor=BLUE,
           markersize=10, label="Maior presença — Zé Gabriel", alpha=0.85),
]
legend = ax.legend(
    handles=legend_handles,
    loc="lower right",
    fontsize=7.5,
    framealpha=0.55,
    facecolor=BG,
    labelcolor=LGRAY,
    edgecolor="#333333",
    handlelength=1,
    borderpad=0.6,
    labelspacing=0.5,
)


# ─── Footer ───────────────────────────────────────────────────────────────────
if LOGO_PATH.exists():
    logo_arr = np.array(
        Image.open(LOGO_PATH).convert("RGBA").resize((44, 44), Image.LANCZOS)
    )
    ab = AnnotationBbox(
        OffsetImage(logo_arr, zoom=1.0),
        (0.075, 0.038), xycoords="figure fraction",
        frameon=False, zorder=10,
    )
    ax.add_artist(ab)

fig.text(0.155, 0.038, "@SportRecifeLab",
         color=YELLOW, fontsize=8.5, fontfamily="Franklin Gothic Heavy",
         fontweight="bold", ha="left", va="center")
fig.text(0.97, 0.038, "Dados: SofaScore  ·  KDE normalizado p/90",
         color=GRAY, fontsize=7.0, fontfamily="Arial",
         ha="right", va="center")


# ─── Salvar ───────────────────────────────────────────────────────────────────
plt.savefig(OUT_PATH, dpi=120, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
plt.close()
print(f"Salvo: {OUT_PATH}")
