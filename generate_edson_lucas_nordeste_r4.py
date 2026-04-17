"""
Card — Edson Lucas · Copa do Nordeste R4 · Sport 5-0 Maranhão
Redesign v3: hierarchy-first, landscape, optimized for social media
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
from PIL import Image

BG      = "#0a0a0a"
YELLOW  = "#F5C400"
WHITE   = "#FFFFFF"
LGRAY   = "#888888"
DGRAY   = "#333333"
GREEN   = "#2ECC71"
RED     = "#E74C3C"
PANEL   = "#131313"

FIG_W, FIG_H = 12.0, 6.8
DPI = 140

STATS = [
    # (label, value_str, delta_str, delta_positive)
    ("PASSES",          "80",     "+67%",  True),
    ("PRECISÃO",        "91.3%",  "+14%",  True),
    ("CAMPO ADV.",      "38",     "+93%",  True),
    ("CHUTES",          "3",      "+350%", True),
    ("DUELOS",          "8",      "+71%",  True),
    ("TOQUES",          "103",    "+74%",  True),
    ("RECUPERAÇÕES",    "9",      "+0%",   True),
]


def _pill(ax, cx, cy, text, color, fontsize=8.5, w=0.072, h=0.055):
    ax.add_patch(patches.FancyBboxPatch(
        (cx - w/2, cy - h/2), w, h,
        boxstyle="round,pad=0.012",
        facecolor=color + "28",   # transparent fill
        edgecolor=color, linewidth=1.2,
        transform=ax.transAxes, zorder=8,
    ))
    ax.text(cx, cy, text,
            color=color, fontsize=fontsize, fontweight="black",
            ha="center", va="center",
            transform=ax.transAxes, zorder=9)


def generate():
    photo = Image.open("edson_lucas_foto.jpg").convert("RGBA")
    photo = photo.resize((460, 460), Image.LANCZOS)
    photo_arr = np.array(photo)

    logo = Image.open("sportrecifelab_avatar.png").convert("RGBA").resize((40, 40), Image.LANCZOS)
    logo_arr = np.array(logo)

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Faixa lateral amarela (acento vertical esquerdo) ─────────────────────
    ax.add_patch(patches.Rectangle((0, 0), 0.008, 1,
                                    facecolor=YELLOW, edgecolor="none",
                                    transform=ax.transAxes, zorder=2))

    # ══════════ PAINEL ESQUERDO ══════════════════════════════════════════════
    L = 0.26   # largura do painel esquerdo

    # Foto com vinheta lateral
    photo_ab = AnnotationBbox(
        OffsetImage(photo_arr, zoom=0.315),
        (L / 2 + 0.008, 0.52),
        xycoords="axes fraction", frameon=False, zorder=4,
    )
    ax.add_artist(photo_ab)

    # Gradiente sobre a foto (base escura para legibilidade do nome)
    for i, alpha in enumerate(np.linspace(0.0, 0.92, 10)):
        y = 0.01 + i * 0.025
        ax.add_patch(patches.Rectangle(
            (0.008, y), L, 0.025,
            facecolor=BG, alpha=alpha, edgecolor="none",
            transform=ax.transAxes, zorder=5,
        ))

    # Nome
    ax.text(L / 2 + 0.008, 0.195, "EDSON",
            color=WHITE, fontsize=22, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=10,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])
    ax.text(L / 2 + 0.008, 0.128, "LUCAS",
            color=YELLOW, fontsize=22, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=10,
            path_effects=[pe.withStroke(linewidth=3, foreground=BG)])

    # Posição e jogo
    ax.text(L / 2 + 0.008, 0.072, "LATERAL ESQ  ·  #96",
            color=LGRAY, fontsize=6.5, ha="center", va="center",
            transform=ax.transAxes, zorder=10)

    # Rating — destaque máximo no canto superior direito do painel
    ax.add_patch(patches.FancyBboxPatch(
        (L - 0.068, 0.78), 0.065, 0.165,
        boxstyle="round,pad=0.010",
        facecolor=YELLOW, edgecolor="none",
        transform=ax.transAxes, zorder=6,
    ))
    ax.text(L - 0.035, 0.900, "RATING",
            color="#111", fontsize=6.5, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=10)
    ax.text(L - 0.035, 0.840, "7.5",
            color="#111", fontsize=26, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=10)

    # ══════════ DIVISÓRIA ════════════════════════════════════════════════════
    ax.plot([L + 0.012, L + 0.012], [0.07, 0.93],
            color=DGRAY, linewidth=0.8, transform=ax.transAxes, zorder=5)

    # ══════════ PAINEL DIREITO ════════════════════════════════════════════════
    R0 = L + 0.028   # início do painel direito

    # Contexto do jogo (topo)
    ax.text(R0, 0.930, "SPORT RECIFE  5 – 0  MARANHÃO AC",
            color=WHITE, fontsize=10.5, fontweight="black",
            ha="left", va="center", transform=ax.transAxes, zorder=10)
    ax.text(R0, 0.882, "COPA DO NORDESTE 2026  ·  RODADA 4  ·  90 MINUTOS",
            color=LGRAY, fontsize=7,
            ha="left", va="center", transform=ax.transAxes, zorder=10)

    # CTA badge
    cta_x = 0.945
    ax.add_patch(patches.FancyBboxPatch(
        (cta_x - 0.098, 0.855), 0.110, 0.090,
        boxstyle="round,pad=0.010",
        facecolor=YELLOW + "22", edgecolor=YELLOW, linewidth=1.0,
        transform=ax.transAxes, zorder=7,
    ))
    ax.text(cta_x - 0.043, 0.907, "MELHOR",
            color=YELLOW, fontsize=6.8, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=10)
    ax.text(cta_x - 0.043, 0.876, "LATERAL?",
            color=YELLOW, fontsize=6.8, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=10)

    # Linha separadora
    ax.plot([R0, 0.990], [0.848, 0.848],
            color=DGRAY, linewidth=0.6, transform=ax.transAxes, zorder=5)

    # Sub-título do comparativo
    ax.text(R0, 0.815, "vs  MÉDIA DOS LATERAIS ESQUERDOS  (Felipinho · Rafinha · Copa do Nordeste)",
            color=LGRAY, fontsize=6.2,
            ha="left", va="center", transform=ax.transAxes, zorder=10)

    # ── Grid de stats: 4 (linha 1) + 3 (linha 2) ─────────────────────────────
    right_w = 0.990 - R0
    ROW1 = STATS[:4]
    ROW2 = STATS[4:]

    def _stat_cell(ax, cx, cy_top, label, value, delta_str, delta_pos):
        d_color = GREEN if delta_pos else RED
        # Valor — elemento dominante
        ax.text(cx, cy_top - 0.060, value,
                color=YELLOW, fontsize=28, fontweight="black",
                ha="center", va="center", transform=ax.transAxes, zorder=10)
        # Delta pill logo abaixo
        _pill(ax, cx, cy_top - 0.148, delta_str, d_color,
              fontsize=8.5, w=0.082, h=0.052)
        # Label pequeno abaixo do pill
        ax.text(cx, cy_top - 0.215, label,
                color=LGRAY, fontsize=6.0,
                ha="center", va="center", transform=ax.transAxes, zorder=10)

    row1_top = 0.775
    for i, (lbl, val, dlt, pos) in enumerate(ROW1):
        step = right_w / 4
        cx = R0 + step * i + step / 2
        _stat_cell(ax, cx, row1_top, lbl, val, dlt, pos)

    # Linha divisória sutil entre linhas
    ax.plot([R0, 0.990], [0.512, 0.512],
            color=DGRAY, linewidth=0.5, alpha=0.6,
            transform=ax.transAxes, zorder=5)

    row2_top = 0.460
    for i, (lbl, val, dlt, pos) in enumerate(ROW2):
        step = right_w / 3
        cx = R0 + step * i + step / 2
        _stat_cell(ax, cx, row2_top, lbl, val, dlt, pos)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.012, 0.992], [0.052, 0.052],
            color=DGRAY, linewidth=0.5, transform=ax.transAxes, zorder=5)

    logo_ab = AnnotationBbox(
        OffsetImage(logo_arr, zoom=0.40), (0.040, 0.028),
        xycoords="axes fraction", frameon=False, zorder=11,
    )
    ax.add_artist(logo_ab)
    ax.text(0.070, 0.028, "@SportRecifeLab",
            color=YELLOW, fontsize=8.5, fontweight="bold",
            ha="left", va="center", transform=ax.transAxes, zorder=10)
    ax.text(0.990, 0.028, "Dados: SofaScore",
            color=LGRAY, fontsize=6.5, ha="right", va="center",
            transform=ax.transAxes, zorder=10)

    out = "card_edson_lucas_nordeste_r4.png"
    plt.tight_layout(pad=0)
    plt.savefig(out, dpi=DPI, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print("Salvo:", out)


if __name__ == "__main__":
    generate()
