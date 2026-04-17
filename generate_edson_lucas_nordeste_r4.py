"""
Card comparativo — Edson Lucas x Média dos Laterais Esquerdos Copa do Nordeste 2026
Jogo: Sport Recife 5x0 Maranhão AC (Rodada 4)
Layout paisagem: painel esquerdo (foto + rating) | painel direito (stats vs média)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
from PIL import Image

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
GRAY   = "#444444"
LGRAY  = "#999999"
GREEN  = "#2ECC71"
RED    = "#E74C3C"
PANEL  = "#141414"

FIG_W, FIG_H = 13.0, 7.2
DPI = 120

# ── Dados ─────────────────────────────────────────────────────────────────────
EDSON = {
    "rating":       7.5,
    "passes":       80,
    "pass_acc":     91.3,
    "opp_half":     38,
    "shots":        3,
    "duels_won":    8,
    "touches":      103,
    "recoveries":   9,
}

OTHERS = [
    {"rating": 6.6, "passes": 54, "pass_acc": 79.6, "opp_half": 20, "shots": 0, "duels_won": 1,  "touches": 63, "recoveries": 3},
    {"rating": 7.6, "passes": 32, "pass_acc": 78.1, "opp_half": 15, "shots": 0, "duels_won": 9,  "touches": 46, "recoveries": 14},
    {"rating": 7.8, "passes": 58, "pass_acc": 82.8, "opp_half": 24, "shots": 2, "duels_won": 4,  "touches": 69, "recoveries": 10},
]

def _mean(key):
    return np.mean([o[key] for o in OTHERS])

def _delta(val, mean, higher_is_better=True):
    if mean == 0:
        return "—", LGRAY
    d = (val - mean) / mean * 100
    sign = "+" if d >= 0 else ""
    color = GREEN if (d >= 0) == higher_is_better else RED
    return f"{sign}{d:.0f}%", color


def generate():
    photo = Image.open("edson_lucas_foto.jpg").convert("RGBA")
    photo = photo.resize((420, 420), Image.LANCZOS)
    photo_arr = np.array(photo)

    logo = Image.open("sportrecifelab_avatar.png").convert("RGBA").resize((44, 44), Image.LANCZOS)
    logo_arr = np.array(logo)

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Faixa topo ────────────────────────────────────────────────────────────
    ax.add_patch(patches.Rectangle((0, 0.88), 1, 0.12,
                                    facecolor=YELLOW, edgecolor="none",
                                    transform=ax.transAxes, zorder=1))
    ax.text(0.5, 0.960, "COPA DO NORDESTE 2026  ·  RODADA 4",
            color="#111", fontsize=8.5, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.5, 0.913, "SPORT RECIFE  5 × 0  MARANHÃO AC",
            color="#111", fontsize=12, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    # ── Linha divisória vertical (separa painéis) ──────────────────────────────
    DIV = 0.30
    ax.plot([DIV, DIV], [0.04, 0.87], color=GRAY,
            linewidth=0.6, alpha=0.5, transform=ax.transAxes, zorder=5)

    # ══════════════════════════════════════════════════════════════
    # PAINEL ESQUERDO — foto + nome + rating
    # ══════════════════════════════════════════════════════════════

    # Moldura amarela da foto
    ax.add_patch(patches.FancyBboxPatch(
        (0.015, 0.13), 0.255, 0.71,
        boxstyle="round,pad=0.006", facecolor=YELLOW,
        edgecolor="none", transform=ax.transAxes, zorder=2,
    ))
    photo_ab = AnnotationBbox(
        OffsetImage(photo_arr, zoom=0.33),
        (0.143, 0.50), xycoords="axes fraction",
        frameon=False, zorder=10,
    )
    ax.add_artist(photo_ab)

    # Nome sobre a foto (faixa escura na base)
    ax.add_patch(patches.Rectangle(
        (0.015, 0.13), 0.255, 0.175,
        facecolor="#0d0d0dCC", edgecolor="none",
        transform=ax.transAxes, zorder=11,
    ))
    ax.text(0.143, 0.255, "EDSON LUCAS",
            color=WHITE, fontsize=13.5, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=12,
            path_effects=[pe.withStroke(linewidth=2, foreground="#000")])
    ax.text(0.143, 0.188, "LATERAL ESQUERDO  ·  #96",
            color=LGRAY, fontsize=7,
            ha="center", va="center", transform=ax.transAxes, zorder=12)
    ax.text(0.143, 0.155, "90 MIN · SPORT 5×0 MARANHÃO",
            color=YELLOW, fontsize=6.5, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=12)

    # Rating badge no topo-direito do painel
    ax.add_patch(patches.FancyBboxPatch(
        (0.175, 0.755), 0.086, 0.095,
        boxstyle="round,pad=0.008", facecolor=YELLOW,
        edgecolor="none", transform=ax.transAxes, zorder=13,
    ))
    ax.text(0.218, 0.820, "RATING",
            color="#111", fontsize=6, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=14)
    ax.text(0.218, 0.783, f"{EDSON['rating']:.1f}",
            color="#111", fontsize=18, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=14)

    # ══════════════════════════════════════════════════════════════
    # PAINEL DIREITO — comparativo vs média
    # ══════════════════════════════════════════════════════════════

    # Cabeçalho da seção
    ax.text(DIV + 0.02, 0.820, "COMPARATIVO  ·  EDSON LUCAS  VS  MÉDIA DOS LATERAIS ESQUERDOS",
            color=LGRAY, fontsize=7.5, fontweight="bold",
            ha="left", va="center", transform=ax.transAxes, zorder=10)
    ax.text(DIV + 0.02, 0.785, "Felipinho (R1 · R3)  e  Rafinha (R2)",
            color=GRAY, fontsize=6.5,
            ha="left", va="center", transform=ax.transAxes, zorder=10)
    ax.plot([DIV + 0.015, 0.985], [0.770, 0.770], color=GRAY,
            linewidth=0.4, alpha=0.5, transform=ax.transAxes, zorder=5)

    # Métricas: (label, key, higher_is_better)
    METRICS = [
        ("PASSES\nTOTAIS",         "passes",     True),
        ("PRECISÃO\nDE PASSE",     "pass_acc",   True),
        ("PASSES CAMPO\nADVERSÁRIO","opp_half",  True),
        ("CHUTES\nAO GOL",         "shots",      True),
        ("DUELOS\nGANHOS",         "duels_won",  True),
        ("TOQUES\nNA BOLA",        "touches",    True),
        ("RECUPERA-\nÇÕES",        "recoveries", True),
    ]

    n = len(METRICS)
    # Grid 4+3 (primeira linha 4, segunda linha 3 centradas)
    ROW1 = METRICS[:4]
    ROW2 = METRICS[4:]

    right_start = DIV + 0.025
    right_end   = 0.985
    right_w     = right_end - right_start

    def _draw_metric_block(ax, cx, cy, label, key, higher_is_better):
        edson_val = EDSON[key]
        mean_val  = _mean(key)
        delta_str, delta_color = _delta(edson_val, mean_val, higher_is_better)

        # Fundo do bloco
        bw, bh = 0.155, 0.270
        ax.add_patch(patches.FancyBboxPatch(
            (cx - bw/2, cy - bh/2), bw, bh,
            boxstyle="round,pad=0.010", facecolor=PANEL,
            edgecolor="#222222", linewidth=0.8,
            transform=ax.transAxes, zorder=6,
        ))

        # Label
        ax.text(cx, cy + bh/2 - 0.035, label,
                color=LGRAY, fontsize=6.2, fontweight="bold",
                ha="center", va="center", multialignment="center",
                transform=ax.transAxes, zorder=10)

        # Valor Edson (grande, amarelo)
        val_str = f"{edson_val:.0f}" if isinstance(edson_val, float) and edson_val != int(edson_val) else str(int(edson_val) if isinstance(edson_val, int) else edson_val)
        if key == "pass_acc":
            val_str = f"{edson_val:.1f}%"
        ax.text(cx, cy + 0.010, val_str,
                color=YELLOW, fontsize=20, fontweight="black",
                ha="center", va="center", transform=ax.transAxes, zorder=10)

        # Delta badge
        ax.text(cx, cy - 0.062, delta_str,
                color=delta_color, fontsize=9, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes, zorder=10,
                bbox=dict(boxstyle="round,pad=0.18", facecolor="#1a1a1a",
                          edgecolor=delta_color, linewidth=0.8, alpha=0.9))

        # Média abaixo
        mean_str = f"{mean_val:.1f}%" if key == "pass_acc" else f"{mean_val:.1f}"
        ax.text(cx, cy - bh/2 + 0.030, f"Média: {mean_str}",
                color=GRAY, fontsize=6,
                ha="center", va="center", transform=ax.transAxes, zorder=10)

    # Linha 1 — 4 métricas
    row1_y = 0.555
    for i, (lbl, key, hib) in enumerate(ROW1):
        step = right_w / 4
        cx = right_start + step * i + step / 2
        _draw_metric_block(ax, cx, row1_y, lbl, key, hib)

    # Linha 2 — 3 métricas centralizadas
    row2_y = 0.255
    for i, (lbl, key, hib) in enumerate(ROW2):
        step = right_w / 3
        cx = right_start + step * i + step / 2
        _draw_metric_block(ax, cx, row2_y, lbl, key, hib)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.015, 0.985], [0.065, 0.065], color=YELLOW,
            linewidth=0.6, alpha=0.30, transform=ax.transAxes, zorder=10)
    logo_ab = AnnotationBbox(
        OffsetImage(logo_arr, zoom=0.44), (0.040, 0.038),
        xycoords="axes fraction", frameon=False, zorder=11,
    )
    ax.add_artist(logo_ab)
    ax.text(0.075, 0.038, "@SportRecifeLab",
            color=YELLOW, fontsize=9, fontweight="bold",
            ha="left", va="center", transform=ax.transAxes, zorder=10)
    ax.text(0.985, 0.038, "Dados: SofaScore",
            color=GRAY, fontsize=7, ha="right", va="center",
            transform=ax.transAxes, zorder=10)

    out = "card_edson_lucas_nordeste_r4.png"
    plt.tight_layout(pad=0)
    plt.savefig(out, dpi=DPI, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print("Salvo:", out)


if __name__ == "__main__":
    generate()
