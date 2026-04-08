"""
Heatmap de posicionamento do Habraao na Serie B 2025
Fonte: SofaScore | Visualizacao: mplsoccer
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from mplsoccer import VerticalPitch
from PIL import Image
import numpy as np
import json

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
GRAY   = "#666666"
LGRAY  = "#AAAAAA"
WHITE  = "#FFFFFF"

# ─── Dados ───────────────────────────────────────────────────────────────────
with open("habraao_heatmap_serie_b_2025.json") as f:
    raw = json.load(f)

# SofaScore: x/y em escala 0-100 (campo orientado horizontal)
# mplsoccer VerticalPitch: x = 0-120 (comprimento), y = 0-80 (largura)
# Conversao: sofascore_x -> pitch_x (*1.2), sofascore_y -> pitch_y (*0.8)
xs     = np.array([p["x"] * 1.2 for p in raw["points"]])
ys     = np.array([p["y"] * 0.8 for p in raw["points"]])
counts = np.array([p["count"] for p in raw["points"]], dtype=float)

# expande pontos pelo count para o KDE
xs_exp = np.repeat(xs, counts.astype(int))
ys_exp = np.repeat(ys, counts.astype(int))

# ─── Figura ──────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6.0, 8.5), dpi=120)
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

pitch = VerticalPitch(
    pitch_type='statsbomb',
    pitch_color='#0e3d1f',
    line_color='#2a7a3a',
    linewidth=1.0,
    goal_type='box',
    corner_arcs=True,
)
pitch.draw(ax=ax)
# reposiciona o eixo: deixa espaço para header (topo) e footer (base)
ax.set_position([0.04, 0.07, 0.92, 0.80])

# KDE heatmap
pitch.kdeplot(
    xs_exp, ys_exp, ax=ax,
    cmap='YlOrRd',
    fill=True,
    alpha=0.82,
    levels=100,
    bw_adjust=0.55,
    zorder=2,
)

# ─── Header ──────────────────────────────────────────────────────────────────
fig.text(0.50, 0.965, "SPORT RECIFE  \u00b7  2025",
         color=YELLOW, fontsize=8.5, fontweight='bold',
         fontfamily='Franklin Gothic Heavy',
         ha='center', va='center')

fig.text(0.50, 0.940, "HABRAAO",
         color=WHITE, fontsize=28, fontweight='black',
         fontfamily='Franklin Gothic Heavy',
         ha='center', va='center',
         path_effects=[pe.withStroke(linewidth=2, foreground=BG)])

fig.text(0.50, 0.918, "MAPA DE CALOR  \u00b7  ZAGUEIRO  \u00b7  SERIE B 2025  \u00b7  14J",
         color=LGRAY, fontsize=7.5, fontfamily='Arial',
         ha='center', va='center')

# ─── Footer ──────────────────────────────────────────────────────────────────
# Logo
logo_arr = np.array(Image.open("sportrecifelab_avatar.png")
                    .convert("RGBA")
                    .resize((46, 46), Image.LANCZOS))
logo_img = OffsetImage(logo_arr, zoom=1.0)
logo_ab  = AnnotationBbox(logo_img, (0.09, 0.028),
                          xycoords='figure fraction',
                          frameon=False, zorder=10)
ax.add_artist(logo_ab)

fig.text(0.175, 0.028, "@SportRecifeLab",
         color=YELLOW, fontsize=8.5, fontfamily='Franklin Gothic Heavy',
         fontweight='bold', ha='left', va='center')

fig.text(0.97, 0.028, "Dados: SofaScore",
         color=GRAY, fontsize=7.2, fontfamily='Arial',
         ha='right', va='center')

# ─── Salvar ──────────────────────────────────────────────────────────────────
out = "C:/Users/compesa/Desktop/SportSofa/card_habraao_heatmap.png"
# layout manual via set_position — não usar tight_layout aqui
plt.savefig(out, dpi=120, bbox_inches='tight',
            facecolor=BG, edgecolor='none')
plt.close()
print("Salvo:", out)
