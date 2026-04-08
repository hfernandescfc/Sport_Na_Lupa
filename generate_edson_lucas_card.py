"""
Card de apresentação — Edson Lucas (@SportRecifeLab)
Layout: headshot centralizado + stats em grade
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
from PIL import Image

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
GRAY   = "#555555"
LGRAY  = "#AAAAAA"
PANEL  = "#161616"

FIG_W, FIG_H = 7.2, 9.6
DPI          = 120

STATS = [
    {"label": "RATING MÉDIO",        "value": "6.89",  "badge": "SÉRIE B 2025  ·  15 JOGOS",      "highlight": True},
    {"label": "CRUZAMENTOS",         "value": "36",    "badge": "LATERAL OFENSIVO  ·  SÉRIE B 2025", "highlight": True},
    {"label": "PASSES NO CAMPO ADV.","value": "73.3%", "badge": "206 DE 281 PASSES CERTOS",        "highlight": False},
    {"label": "GOLS EM 2026",        "value": "2",     "badge": "PAULISTA A2  ·  FERROVIÁRIA",     "highlight": False},
    {"label": "EXP. SÉRIE B",        "value": "23J",   "badge": "2023 + 2025  ·  1.690 MINUTOS",   "highlight": False},
]


def generate():
    photo = Image.open("edson_lucas_foto.jpg").convert("RGBA")
    # upscale suave para exibição
    photo = photo.resize((420, 420), Image.LANCZOS)
    photo_arr = np.array(photo)

    logo = Image.open("sportrecifelab_avatar.png").convert("RGBA").resize((52, 52), Image.LANCZOS)
    logo_arr = np.array(logo)

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ── Faixa de destaque no topo ─────────────────────────────────────────────
    top_bar = patches.Rectangle((0, 0.84), 1, 0.16,
                                 facecolor=YELLOW, edgecolor='none',
                                 transform=ax.transAxes, zorder=1)
    ax.add_patch(top_bar)

    ax.text(0.5, 0.935, "SPORT RECIFE  ·  2026",
            color="#111111", fontsize=10, fontweight='bold',
            fontfamily='Franklin Gothic Heavy',
            ha='center', va='center', transform=ax.transAxes, zorder=5)

    ax.text(0.5, 0.878, "NOVA CONTRATAÇÃO",
            color="#111111", fontsize=8.5, fontfamily='Arial',
            fontweight='bold', ha='center', va='center',
            transform=ax.transAxes, zorder=5)

    # ── Foto centralizada ─────────────────────────────────────────────────────
    # Moldura amarela ao redor do headshot
    frame_size = 0.26
    frame_x, frame_y = 0.5, 0.695
    frame_rect = patches.FancyBboxPatch(
        (frame_x - frame_size / 2 - 0.013, frame_y - frame_size / 2 - 0.013),
        frame_size + 0.026, frame_size + 0.026,
        boxstyle="round,pad=0.005",
        facecolor=YELLOW, edgecolor='none',
        transform=ax.transAxes, zorder=3,
    )
    ax.add_patch(frame_rect)

    # fundo escuro interno (padding visual)
    inner_rect = patches.FancyBboxPatch(
        (frame_x - frame_size / 2 - 0.004, frame_y - frame_size / 2 - 0.004),
        frame_size + 0.008, frame_size + 0.008,
        boxstyle="round,pad=0.003",
        facecolor=BG, edgecolor='none',
        transform=ax.transAxes, zorder=4,
    )
    ax.add_patch(inner_rect)

    photo_img = OffsetImage(photo_arr, zoom=0.335)
    photo_ab  = AnnotationBbox(
        photo_img, (frame_x, frame_y),
        xycoords='axes fraction',
        frameon=False, zorder=5,
        box_alignment=(0.5, 0.5),
    )
    ax.add_artist(photo_ab)

    # ── Nome e posição ────────────────────────────────────────────────────────
    ax.text(0.5, 0.572, "EDSON LUCAS",
            color=WHITE, fontsize=38, fontweight='black',
            fontfamily='Franklin Gothic Heavy',
            ha='center', va='center', transform=ax.transAxes, zorder=10,
            path_effects=[pe.withStroke(linewidth=2, foreground='#000000')])

    ax.text(0.5, 0.535, "LATERAL  ·  SÉRIE B 2025  ·  15J",
            color=LGRAY, fontsize=8, fontfamily='Arial',
            ha='center', va='center', transform=ax.transAxes, zorder=10)

    # linha divisória
    ax.plot([0.08, 0.92], [0.515, 0.515], color=YELLOW,
            linewidth=0.9, alpha=0.5, transform=ax.transAxes, zorder=10)

    # ── Stats ─────────────────────────────────────────────────────────────────
    col_x   = [0.08, 0.55]
    row_y   = [0.480, 0.345, 0.210]
    # ordem: 5 stats em layout 2 colunas (3 linha 1, 2 linha 2, depois linha 3)
    positions = [
        (col_x[0], row_y[0]),
        (col_x[1], row_y[0]),
        (col_x[0], row_y[1]),
        (col_x[1], row_y[1]),
        (col_x[0], row_y[2]),
    ]

    for (x, y), s in zip(positions, STATS):
        badge_color     = YELLOW if s["highlight"] else "#252525"
        badge_txt_color = "#111111" if s["highlight"] else LGRAY

        ax.text(x, y, s["label"],
                color=GRAY, fontsize=7, fontfamily='Arial', fontweight='bold',
                ha='left', va='center', transform=ax.transAxes, zorder=10)

        ax.text(x, y - 0.040, s["value"],
                color=WHITE, fontsize=27, fontweight='black',
                fontfamily='Franklin Gothic Heavy',
                ha='left', va='center', transform=ax.transAxes, zorder=10)

        ax.text(x + 0.008, y - 0.075, s["badge"],
                color=badge_txt_color, fontsize=6.2,
                fontfamily='Franklin Gothic Heavy', fontweight='bold',
                ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.30',
                          facecolor=badge_color,
                          edgecolor='none', alpha=0.95),
                transform=ax.transAxes, zorder=10)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.04, 0.96], [0.060, 0.060], color=YELLOW,
            linewidth=0.7, alpha=0.35, transform=ax.transAxes, zorder=10)

    logo_ab = AnnotationBbox(
        OffsetImage(logo_arr, zoom=0.52), (0.065, 0.037),
        xycoords='axes fraction', frameon=False, zorder=11,
        box_alignment=(0.5, 0.5),
    )
    ax.add_artist(logo_ab)

    ax.text(0.115, 0.037, "@SportRecifeLab",
            color=YELLOW, fontsize=9, fontfamily='Franklin Gothic Heavy',
            fontweight='bold', ha='left', va='center',
            transform=ax.transAxes, zorder=10)

    ax.text(0.97, 0.037, "Dados: SofaScore",
            color=GRAY, fontsize=7.2, fontfamily='Arial',
            ha='right', va='center', transform=ax.transAxes, zorder=10)

    out = "card_edson_lucas.png"
    plt.tight_layout(pad=0)
    plt.savefig(out, dpi=DPI, bbox_inches='tight',
                facecolor=BG, edgecolor='none')
    plt.close()
    print("Salvo:", out)


if __name__ == "__main__":
    generate()
