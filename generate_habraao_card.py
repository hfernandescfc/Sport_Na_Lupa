"""
Card visual do Habraao no estilo @SportRecifeLab — com foto e logo.
Referencia: gustavo_maia_card_v4.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
from PIL import Image

# ─── Paleta ─────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
RED    = "#CC1020"
WHITE  = "#FFFFFF"
GRAY   = "#666666"
LGRAY  = "#AAAAAA"

# ─── Dados do card ───────────────────────────────────────────────────────────
STATS = [
    {
        "label":            "RATING MÉDIO",
        "value":            "7.02",
        "badge":            "47 JOGOS NA SÉRIE B (3 CLUBES)",
        "badge_color":      YELLOW,
        "badge_txt_color":  "#111111",
    },
    {
        "label":            "DUELOS AÉREOS",
        "value":            "70.0%",
        "badge":            "SÉRIE B 2023–2025",
        "badge_color":      YELLOW,
        "badge_txt_color":  "#111111",
    },
    {
        "label":            "PRECISÃO DE PASSE",
        "value":            "81.7%",
        "badge":            "SÉRIE B 2023–2025",
        "badge_color":      YELLOW,
        "badge_txt_color":  "#111111",
    },
    {
        "label":            "CORTES NA SÉRIE B",
        "value":            "280",
        "badge":            "3 TEMPORADAS / 47 JOGOS",
        "badge_color":      "#252525",
        "badge_txt_color":  LGRAY,
    },
    {
        "label":            "TEAM OF THE WEEK",
        "value":            "3x",
        "badge":            "SOFASCORE — SÉRIE B",
        "badge_color":      "#252525",
        "badge_txt_color":  YELLOW,
    },
]

# ─── Layout ──────────────────────────────────────────────────────────────────
FIG_W, FIG_H = 7.2, 9.6   # polegadas
DPI          = 120
SPLIT        = 0.40        # fração da largura dedicada à foto


def load_player_photo(path: str) -> np.ndarray:
    """Abre a foto, faz crop central retrato e retorna array RGBA."""
    img = Image.open(path).convert("RGBA")
    w, h = img.size          # 2560 x 1707

    # crop central: pega ~1100px de largura centrado → retrato 1100×1707
    crop_w = 1100
    x0 = (w - crop_w) // 2
    img = img.crop((x0, 0, x0 + crop_w, h))
    return np.array(img)


def load_logo(path: str, size_px: int = 58) -> np.ndarray:
    img = Image.open(path).convert("RGBA").resize(
        (size_px, size_px), Image.LANCZOS)
    return np.array(img)


def add_gradient_fade(ax, x_start: float, width: float = 0.12):
    """Degrade preto da borda direita do painel de foto → fundo do card."""
    steps = 40
    for i in range(steps):
        alpha = (i / steps) ** 1.6   # curva suave
        rx = x_start + i / steps * width
        r = patches.Rectangle(
            (rx, 0), width / steps, 1,
            facecolor=BG, edgecolor='none', alpha=alpha,
            transform=ax.transAxes, zorder=6,
        )
        ax.add_patch(r)


def generate():
    photo_arr = load_player_photo("habraao_foto.jpg")
    logo_arr  = load_logo("sportrecifelab_avatar.png", size_px=54)

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')

    # ── Foto do jogador (painel esquerdo) ─────────────────────────────────────
    photo_ax = ax.inset_axes([0, 0, SPLIT + 0.05, 1])
    photo_ax.imshow(photo_arr, aspect='auto',
                    extent=[0, 1, 0, 1], origin='upper', zorder=1)
    photo_ax.axis('off')

    # degrade lateral direito da foto → fundo escuro
    add_gradient_fade(ax, x_start=SPLIT - 0.06)

    # ── Painel direito — conteúdo ─────────────────────────────────────────────
    rx = SPLIT + 0.05   # margem esquerda do texto

    # Header
    ax.text(rx, 0.948, "SPORT RECIFE  ·  2026",
            color=YELLOW, fontsize=9, fontweight='bold',
            fontfamily='Franklin Gothic Heavy',
            ha='left', va='center', transform=ax.transAxes, zorder=10)

    # Nome
    ax.text(rx, 0.895, "HABRAÃO",
            color=WHITE, fontsize=44, fontweight='black',
            fontfamily='Franklin Gothic Heavy',
            ha='left', va='center', transform=ax.transAxes, zorder=10,
            path_effects=[pe.withStroke(linewidth=2, foreground='#000000')])

    # Subtítulo
    ax.text(rx, 0.857, "ZAGUEIRO  ·  47J  NA SÉRIE B  ·  4.745'",
            color=LGRAY, fontsize=7.8, fontfamily='Arial',
            ha='left', va='center', transform=ax.transAxes, zorder=10)

    # Linha divisória
    ax.plot([rx, 0.97], [0.838, 0.838], color=YELLOW,
            linewidth=0.9, alpha=0.55, transform=ax.transAxes, zorder=10)

    # ── Stats ─────────────────────────────────────────────────────────────────
    y0      = 0.800
    row_gap = 0.135

    for i, s in enumerate(STATS):
        y = y0 - i * row_gap

        ax.text(rx, y, s["label"],
                color=GRAY, fontsize=7.5, fontfamily='Arial', fontweight='bold',
                ha='left', va='center', transform=ax.transAxes, zorder=10)

        ax.text(rx, y - 0.037, s["value"],
                color=WHITE, fontsize=29, fontweight='black',
                fontfamily='Franklin Gothic Heavy',
                ha='left', va='center', transform=ax.transAxes, zorder=10)

        ax.text(rx + 0.01, y - 0.071, s["badge"],
                color=s["badge_txt_color"], fontsize=6.8,
                fontfamily='Franklin Gothic Heavy', fontweight='bold',
                ha='left', va='center',
                bbox=dict(boxstyle='round,pad=0.32',
                          facecolor=s["badge_color"],
                          edgecolor='none', alpha=0.95),
                transform=ax.transAxes, zorder=10)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.04, 0.96], [0.060, 0.060], color=YELLOW,
            linewidth=0.7, alpha=0.35, transform=ax.transAxes, zorder=10)

    # Logo SportRecifeLab (esquerda)
    logo_img = OffsetImage(logo_arr, zoom=0.55)
    logo_ab  = AnnotationBbox(
        logo_img, (0.065, 0.038),
        xycoords='axes fraction',
        frameon=False, zorder=11,
        box_alignment=(0.5, 0.5),
    )
    ax.add_artist(logo_ab)

    ax.text(0.115, 0.038, "@SportRecifeLab",
            color=YELLOW, fontsize=9, fontfamily='Franklin Gothic Heavy',
            fontweight='bold', ha='left', va='center',
            transform=ax.transAxes, zorder=10)

    ax.text(0.97, 0.038, "Dados: SofaScore  ·  Série B 2023–2025",
            color=GRAY, fontsize=7.2, fontfamily='Arial',
            ha='right', va='center', transform=ax.transAxes, zorder=10)

    # ── Salvar ────────────────────────────────────────────────────────────────
    out = "C:/Users/compesa/Desktop/SportSofa/card_habraao_v2.png"
    plt.tight_layout(pad=0)
    plt.savefig(out, dpi=DPI, bbox_inches='tight',
                facecolor=BG, edgecolor='none')
    plt.close()
    print("Salvo:", out)


if __name__ == "__main__":
    generate()
