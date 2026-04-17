"""
Card comparativo — Edson Lucas x Laterais Esquerdos Copa do Nordeste 2026
Jogo: Sport Recife 5x0 Maranhão AC (Rodada 4)

Layout:
  - Topo: hero com foto + stats principais do jogo
  - Seção inferior: comparativo visual vs outros laterais esquerdos da Copa
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.gridspec import GridSpec
import numpy as np
from PIL import Image

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
GRAY   = "#555555"
LGRAY  = "#AAAAAA"
RED    = "#CC3333"
GREEN  = "#33BB66"
MUTED_YELLOW = "#8A6F00"

FIG_W, FIG_H = 8.0, 12.0
DPI = 130

# ── Dados ─────────────────────────────────────────────────────────────────────
EDSON = {
    "name":           "EDSON LUCAS",
    "pos":            "LATERAL ESQ · #96",
    "match":          "SPORT 5×0 MARANHÃO AC · R4 COPA DO NORDESTE",
    "minutes":        "90'",
    "rating":         7.5,
    "passes":         80,
    "pass_acc":       91.3,      # %
    "opp_half":       38,        # accurate passes in opp half
    "opp_half_pct":   86.4,      # % accuracy in opp half
    "long_balls":     5,
    "lb_acc":         60.0,      # %
    "shots":          3,
    "duels_won":      8,
    "clearances":     2,
    "touches":        103,
    "recoveries":     9,
    "was_fouled":     1,
}

# Outros laterais esquerdos nas rodadas 1-3
OTHERS = [
    {"name": "Felipinho",  "round": "R1",
     "rating": 6.6, "passes": 54, "pass_acc": 79.6, "opp_half": 20, "opp_half_pct": 69.0,
     "long_balls": 4, "lb_acc": 50.0, "shots": 0, "duels_won": 1, "touches": 63, "recoveries": 3},
    {"name": "Rafinha",    "round": "R2",
     "rating": 7.6, "passes": 32, "pass_acc": 78.1, "opp_half": 15, "opp_half_pct": 78.9,
     "long_balls": 4, "lb_acc": 50.0, "shots": 0, "duels_won": 9, "touches": 46, "recoveries": 14},
    {"name": "Felipinho",  "round": "R3",
     "rating": 7.8, "passes": 58, "pass_acc": 82.8, "opp_half": 24, "opp_half_pct": 80.0,
     "long_balls": 4, "lb_acc": 75.0, "shots": 2, "duels_won": 4, "touches": 69, "recoveries": 10},
]

def _mean(key):
    return np.mean([o[key] for o in OTHERS])

def _delta_pct(val, mean):
    """Variação relativa em % vs média."""
    if mean == 0:
        return 0
    return (val - mean) / mean * 100

def _fmt_delta(val, mean, higher_is_better=True):
    d = _delta_pct(val, mean)
    sign = "+" if d >= 0 else ""
    return f"{sign}{d:.0f}%", GREEN if (d >= 0) == higher_is_better else RED


# ── Helpers de desenho ────────────────────────────────────────────────────────
def _bar(ax, x, y, w_frac, color, bg_color="#252525", height=0.018, alpha=0.9):
    """Barra de progresso horizontal normalizada."""
    ax.add_patch(patches.FancyBboxPatch(
        (x, y), 1 - x - 0.04, height,
        boxstyle="round,pad=0.002", facecolor=bg_color,
        edgecolor="none", transform=ax.transAxes, zorder=5,
    ))
    fill_w = (1 - x - 0.04) * min(w_frac, 1.0)
    if fill_w > 0:
        ax.add_patch(patches.FancyBboxPatch(
            (x, y), fill_w, height,
            boxstyle="round,pad=0.002", facecolor=color,
            edgecolor="none", alpha=alpha, transform=ax.transAxes, zorder=6,
        ))


def generate():
    photo = Image.open("edson_lucas_foto.jpg").convert("RGBA")
    photo = photo.resize((380, 380), Image.LANCZOS)
    photo_arr = np.array(photo)

    logo = Image.open("sportrecifelab_avatar.png").convert("RGBA").resize((48, 48), Image.LANCZOS)
    logo_arr = np.array(logo)

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Barra de topo ────────────────────────────────────────────────────────
    ax.add_patch(patches.Rectangle((0, 0.89), 1, 0.11,
                                    facecolor=YELLOW, edgecolor="none",
                                    transform=ax.transAxes, zorder=1))
    ax.text(0.5, 0.955, "COPA DO NORDESTE 2026  ·  RODADA 4",
            color="#111111", fontsize=9, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.5, 0.908, "SPORT RECIFE  5 × 0  MARANHÃO AC",
            color="#111111", fontsize=11, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    # ── Foto ─────────────────────────────────────────────────────────────────
    ax.add_patch(patches.FancyBboxPatch(
        (0.07, 0.64), 0.32, 0.245,
        boxstyle="round,pad=0.008", facecolor=YELLOW,
        edgecolor="none", transform=ax.transAxes, zorder=2,
    ))
    photo_ab = AnnotationBbox(
        OffsetImage(photo_arr, zoom=0.265),
        (0.23, 0.763), xycoords="axes fraction",
        frameon=False, zorder=10,
    )
    ax.add_artist(photo_ab)

    # ── Nome / posição ────────────────────────────────────────────────────────
    ax.text(0.43, 0.862, "EDSON LUCAS",
            color=WHITE, fontsize=28, fontweight="black",
            ha="left", va="center", transform=ax.transAxes, zorder=10,
            path_effects=[pe.withStroke(linewidth=2, foreground="#000000")])
    ax.text(0.43, 0.833, "LATERAL ESQUERDO  ·  #96",
            color=LGRAY, fontsize=8,
            ha="left", va="center", transform=ax.transAxes, zorder=10)
    ax.text(0.43, 0.810, "90 MINUTOS JOGADOS",
            color=YELLOW, fontsize=8, fontweight="bold",
            ha="left", va="center", transform=ax.transAxes, zorder=10)

    # Rating destaque
    ax.add_patch(patches.FancyBboxPatch(
        (0.43, 0.65), 0.18, 0.145,
        boxstyle="round,pad=0.01", facecolor="#181818",
        edgecolor=YELLOW, linewidth=1.5, transform=ax.transAxes, zorder=4,
    ))
    ax.text(0.520, 0.740, "RATING",
            color=LGRAY, fontsize=7, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=10)
    ax.text(0.520, 0.700, f"{EDSON['rating']:.1f}",
            color=YELLOW, fontsize=30, fontweight="black",
            ha="center", va="center", transform=ax.transAxes, zorder=10)
    ax.text(0.520, 0.663, "★★★★★",
            color=YELLOW, fontsize=8,
            ha="center", va="center", transform=ax.transAxes, zorder=10)

    # ── Stats principais (4 blocos à direita) ─────────────────────────────────
    hero_stats = [
        ("PASSES",        f"{EDSON['passes']}",         f"{EDSON['pass_acc']:.0f}% precisão"),
        ("NO CAMPO ADV.", f"{EDSON['opp_half']}",        f"{EDSON['opp_half_pct']:.0f}% precisão"),
        ("FINALIZAÇÕES",  f"{EDSON['shots']}",           "3 chutes ao gol"),
        ("DUELOS GANHOS", f"{EDSON['duels_won']}",       f"+ {EDSON['recoveries']} recup."),
    ]
    bx = [0.635, 0.810]
    by = [0.745, 0.655]
    idx = 0
    for row_y in by:
        for col_x in bx:
            if idx >= len(hero_stats):
                break
            lbl, val, sub = hero_stats[idx]
            ax.add_patch(patches.FancyBboxPatch(
                (col_x - 0.005, row_y - 0.005), 0.165, 0.085,
                boxstyle="round,pad=0.008", facecolor="#181818",
                edgecolor="#2a2a2a", linewidth=0.8,
                transform=ax.transAxes, zorder=4,
            ))
            ax.text(col_x + 0.078, row_y + 0.065, lbl,
                    color=GRAY, fontsize=5.8, fontweight="bold",
                    ha="center", va="center", transform=ax.transAxes, zorder=10)
            ax.text(col_x + 0.078, row_y + 0.033, val,
                    color=WHITE, fontsize=20, fontweight="black",
                    ha="center", va="center", transform=ax.transAxes, zorder=10)
            ax.text(col_x + 0.078, row_y + 0.008, sub,
                    color=LGRAY, fontsize=5.5,
                    ha="center", va="center", transform=ax.transAxes, zorder=10)
            idx += 1

    # ── Divisória ─────────────────────────────────────────────────────────────
    ax.plot([0.04, 0.96], [0.635, 0.635], color=YELLOW,
            linewidth=0.8, alpha=0.5, transform=ax.transAxes, zorder=10)
    ax.text(0.5, 0.616, "COMPARATIVO · LATERAIS ESQUERDOS · COPA DO NORDESTE 2026",
            color=LGRAY, fontsize=7.5, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=10)
    ax.plot([0.04, 0.96], [0.600, 0.600], color=GRAY,
            linewidth=0.4, alpha=0.4, transform=ax.transAxes, zorder=10)

    # ── Comparativo em barras ─────────────────────────────────────────────────
    metrics = [
        ("PASSES TOTAIS",        "passes",       80,   False),
        ("PRECISÃO DE PASSE %",  "pass_acc",     91.3, False),
        ("PASSES NO CAMPO ADV.", "opp_half",     38,   False),
        ("FINALIZAÇÕES",         "shots",        3,    False),
        ("DUELOS GANHOS",        "duels_won",    8,    False),
        ("TOQUES NA BOLA",       "touches",      103,  False),
        ("RECUPERAÇÕES",         "recoveries",   9,    False),
    ]

    col_label_x = 0.05
    col_val_x   = 0.36
    col_delta_x = 0.52
    col_bar_x   = 0.625
    bar_max_vals = {
        "passes":    110,
        "pass_acc":  100,
        "opp_half":  50,
        "shots":     5,
        "duels_won": 12,
        "touches":   120,
        "recoveries":18,
    }

    start_y = 0.588
    row_h   = 0.073

    # Header
    ax.text(col_val_x + 0.01, start_y + 0.008, "EDSON",
            color=YELLOW, fontsize=6.5, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=10)
    ax.text(col_delta_x + 0.04, start_y + 0.008, "VS MÉDIA",
            color=LGRAY, fontsize=6.5, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=10)
    ax.text(col_bar_x + 0.15, start_y + 0.008, "COMPARATIVO (BARRA)",
            color=LGRAY, fontsize=6.5, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=10)

    player_labels = [o["name"].split()[0] + f" ({o['round']})" for o in OTHERS]
    player_colors = ["#3A7BD5", "#E67E22", "#3A7BD5"]

    for i, (label, key, edson_val, _) in enumerate(metrics):
        y = start_y - (i + 1) * row_h

        # Fundo da linha alternado
        if i % 2 == 0:
            ax.add_patch(patches.Rectangle((0.03, y - 0.008), 0.94, row_h - 0.004,
                                            facecolor="#111111", edgecolor="none",
                                            transform=ax.transAxes, zorder=2))

        # Label
        ax.text(col_label_x, y + row_h * 0.45, label,
                color=LGRAY, fontsize=6.8, fontweight="bold",
                ha="left", va="center", transform=ax.transAxes, zorder=10)

        # Valor Edson
        ax.text(col_val_x + 0.01, y + row_h * 0.45, str(edson_val),
                color=YELLOW, fontsize=11, fontweight="black",
                ha="center", va="center", transform=ax.transAxes, zorder=10)

        # Delta vs média
        mean_val = _mean(key)
        delta_str, delta_color = _fmt_delta(edson_val, mean_val)
        ax.text(col_delta_x + 0.04, y + row_h * 0.45, delta_str,
                color=delta_color, fontsize=9, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes, zorder=10)

        # Barra comparativa
        bar_max = bar_max_vals[key]
        bar_y_base = y + 0.002
        bar_h = (row_h - 0.016) / (len(OTHERS) + 1)

        # Edson Lucas
        frac = min(edson_val / bar_max, 1.0)
        _bar(ax, col_bar_x, bar_y_base + len(OTHERS) * bar_h,
             frac, YELLOW, height=bar_h * 0.70, alpha=0.95)
        ax.text(col_bar_x - 0.005, bar_y_base + len(OTHERS) * bar_h + bar_h * 0.35,
                "Edson", color=YELLOW, fontsize=4.8,
                ha="right", va="center", transform=ax.transAxes, zorder=12)

        for j, other in enumerate(OTHERS):
            oval = other[key]
            frac_o = min(oval / bar_max, 1.0)
            _bar(ax, col_bar_x, bar_y_base + j * bar_h,
                 frac_o, player_colors[j], height=bar_h * 0.70, alpha=0.7)
            ax.text(col_bar_x - 0.005,
                    bar_y_base + j * bar_h + bar_h * 0.35,
                    player_labels[j], color=player_colors[j], fontsize=4.5,
                    ha="right", va="center", transform=ax.transAxes, zorder=12)

    # ── Linha de média (visual) ────────────────────────────────────────────────
    # Nota explicativa
    y_note = start_y - (len(metrics) + 1) * row_h - 0.005
    ax.text(0.5, y_note,
            "Média dos outros laterais: Felipinho (R1) · Rafinha (R2) · Felipinho (R3)",
            color=GRAY, fontsize=6.2, ha="center", va="center",
            transform=ax.transAxes, zorder=10)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.04, 0.96], [0.055, 0.055], color=YELLOW,
            linewidth=0.7, alpha=0.35, transform=ax.transAxes, zorder=10)
    logo_ab = AnnotationBbox(
        OffsetImage(logo_arr, zoom=0.48), (0.062, 0.032),
        xycoords="axes fraction", frameon=False, zorder=11,
    )
    ax.add_artist(logo_ab)
    ax.text(0.105, 0.032, "@SportRecifeLab",
            color=YELLOW, fontsize=9, fontweight="bold",
            ha="left", va="center", transform=ax.transAxes, zorder=10)
    ax.text(0.97, 0.032, "Dados: SofaScore",
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
