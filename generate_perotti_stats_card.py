"""
Card de estatísticas — Perotti · Londrina 1×2 Sport · R3 Série B 2026

Exibe métricas do Perotti com escala de cor comparando com os outros
atacantes (posição F, ≥45 min) da mesma partida.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.colors import LinearSegmentedColormap
import numpy as np
from PIL import Image

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
GRAY   = "#333333"
LGRAY  = "#888888"
WHITE  = "#FFFFFF"
PANEL  = "#161616"

LOGO_PATH = Path(__file__).parent / "sportrecifelab_avatar.png"

# Gradiente: pior → melhor (vermelho → amarelo → verde)
CMAP = LinearSegmentedColormap.from_list(
    "rg", ["#C0392B", "#E67E22", "#F5C400", "#27AE60"]
)

# ─── Dados: atacantes F com ≥45min em Londrina x Sport (event_id 15526008) ──
# Ordem: Bruno Santos, Barletta, Perotti, Biel Fonseca
PEERS = [
    {"name": "B. Santos",  "team": "Londrina",    "min": 90},
    {"name": "Barletta",   "team": "Sport",        "min": 88},
    {"name": "Perotti",    "team": "Sport",        "min": 90},
    {"name": "B. Fonseca", "team": "Sport",        "min": 90},
]

# Métricas: (label, valores por jogador na ordem acima, higher_is_better)
# Valores: [B.Santos, Barletta, Perotti, B.Fonseca]
METRICS = [
    ("CHUTES",         [5,    2,    4,    2   ], True),
    ("TOQUES",         [45,   45,   26,   66  ], True),
    ("PASSES CERTOS",  [19,   15,   9,    46  ], True),
    ("ACERTO DE PASSE",[79.2, 75.0, 75.0, 90.2], True),
    ("RECUPERAÇÕES",   [5,    4,    4,    4   ], True),
    ("PERDA DE POSSE", [14,   21,   8,    8   ], False),  # menor = melhor
    ("RATING",         [7.7,  7.4,  6.7,  7.2 ], True),
]

PEROTTI_IDX = 2  # posição de Perotti na lista PEERS


def _percentile(values: list[float], idx: int, higher_is_better: bool) -> float:
    """Retorna o percentil (0–1) do jogador no índice `idx`."""
    valid = [v for v in values if v is not None]
    if len(valid) <= 1:
        return 0.5
    rank = sorted(valid).index(values[idx])  # rank 0 = pior
    pct = rank / (len(valid) - 1)
    return pct if higher_is_better else (1 - pct)


def _draw_header(fig):
    fig.text(0.50, 0.977, "SPORT RECIFE  ·  SÉRIE B 2026",
             color=YELLOW, fontsize=8, fontweight="bold",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center")
    fig.text(0.50, 0.952, "PEROTTI  #9  ·  ATACANTE  ·  90MIN",
             color=WHITE, fontsize=21, fontweight="black",
             fontfamily="Franklin Gothic Heavy", ha="center", va="center",
             path_effects=[pe.withStroke(linewidth=2, foreground=BG)])
    fig.text(0.50, 0.930, "LONDRINA  1 × 2  SPORT",
             color=YELLOW, fontsize=10.5, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="center", va="center")
    fig.text(0.50, 0.913, "R3  ·  SÉRIE B 2026  ·  04.04.2026",
             color=LGRAY, fontsize=7.5, fontfamily="Arial",
             ha="center", va="center")


def _draw_stats(ax):
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    n = len(METRICS)
    row_h = 1.0 / n
    ax.set_ylim(0, 1)
    ax.axis("off")

    bar_x0    = 0.48   # início da barra
    bar_w     = 0.44   # largura total da barra
    bar_h     = 0.018  # espessura da barra
    dot_r     = 0.009  # raio dos pontos de comparação

    for i, (label, values, higher) in enumerate(METRICS):
        # y central desta linha (de cima para baixo)
        yc = 1.0 - (i + 0.5) * row_h

        pct = _percentile(values, PEROTTI_IDX, higher)
        bar_color = CMAP(pct)

        perotti_val = values[PEROTTI_IDX]

        # ── Separador ────────────────────────────────────────────────────────
        if i > 0:
            ax.axhline(yc + row_h * 0.5, color=GRAY, linewidth=0.4, alpha=0.5)

        # ── Label da métrica ─────────────────────────────────────────────────
        ax.text(0.02, yc + 0.012, label,
                color=LGRAY, fontsize=7.2, fontfamily="Arial",
                ha="left", va="center")

        # ── Valor do Perotti ──────────────────────────────────────────────────
        val_str = (f"{perotti_val:.0f}" if isinstance(perotti_val, float)
                   and perotti_val == int(perotti_val)
                   else f"{perotti_val}")
        ax.text(0.02, yc - 0.018, val_str,
                color=bar_color, fontsize=17,
                fontfamily="Franklin Gothic Heavy", fontweight="bold",
                ha="left", va="center")

        # ── Trilho da barra (fundo) ───────────────────────────────────────────
        ax.add_patch(plt.Rectangle(
            (bar_x0, yc - bar_h / 2), bar_w, bar_h,
            color="#222222", zorder=2, clip_on=False,
        ))

        # ── Barra preenchida até o percentil ─────────────────────────────────
        ax.add_patch(plt.Rectangle(
            (bar_x0, yc - bar_h / 2), bar_w * pct, bar_h,
            color=bar_color, alpha=0.85, zorder=3, clip_on=False,
        ))

        # ── Pontos de todos os jogadores na barra ────────────────────────────
        # Posição do ponto = rank relativo (pior=esquerda, melhor=direita)
        valid_vals = [v for v in values if v is not None]
        ranked = sorted(valid_vals, reverse=not higher)  # índice 0 = pior
        n_valid = len(ranked)

        for j, v in enumerate(values):
            if v is None:
                continue
            rank = ranked.index(v)
            norm_x = rank / (n_valid - 1) if n_valid > 1 else 0.5

            dot_x = bar_x0 + norm_x * bar_w
            is_perotti = (j == PEROTTI_IDX)

            ax.scatter(dot_x, yc,
                       s=60 if is_perotti else 30,
                       color=bar_color if is_perotti else "#555555",
                       edgecolors=WHITE if is_perotti else "none",
                       linewidths=0.8,
                       zorder=5 if is_perotti else 4)

        # ── Rótulo: pior / melhor ─────────────────────────────────────────────
        lo_val = min(valid_vals) if higher else max(valid_vals)
        hi_val = max(valid_vals) if higher else min(valid_vals)
        ax.text(bar_x0 - 0.01, yc,
                f"{lo_val:.0f}" if lo_val == int(lo_val) else f"{lo_val:.1f}",
                color="#444444", fontsize=6, fontfamily="Arial",
                ha="right", va="center")
        ax.text(bar_x0 + bar_w + 0.01, yc,
                f"{hi_val:.0f}" if hi_val == int(hi_val) else f"{hi_val:.1f}",
                color="#444444", fontsize=6, fontfamily="Arial",
                ha="left", va="center")

    # ── Nota de contexto ──────────────────────────────────────────────────────
    ax.text(0.50, -0.04,
            "comparado com atacantes com ≥45min na partida (n=4)",
            color="#444444", fontsize=6.5, fontfamily="Arial",
            ha="center", va="center")


def _draw_footer(fig, ax_ref):
    if LOGO_PATH.exists():
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((40, 40), Image.LANCZOS)
        )
        ab = AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0),
            (0.07, 0.025), xycoords="figure fraction",
            frameon=False, zorder=10,
        )
        ax_ref.add_artist(ab)

    fig.text(0.14, 0.025, "@SportRecifeLab",
             color=YELLOW, fontsize=8, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")
    fig.text(0.97, 0.025, "Dados: SofaScore",
             color=LGRAY, fontsize=7, fontfamily="Arial",
             ha="right", va="center")


def generate_card(output_path: str = "card_perotti_stats.png"):
    fig = plt.figure(figsize=(6.5, 9.0), dpi=130)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.06, 0.07, 0.90, 0.83])

    _draw_header(fig)
    _draw_stats(ax)
    _draw_footer(fig, ax)

    out = Path(output_path)
    plt.savefig(out, dpi=130, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Card salvo: {out}")
    return out


if __name__ == "__main__":
    generate_card()
