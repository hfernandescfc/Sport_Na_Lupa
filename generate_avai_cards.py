"""
Gera os cards visuais da thread "Raio-X: Avaí FC"
Série B 2026 | Rodada 4 — @SportRecifeLab

Cards produzidos:
  01_cover.png          — abertura da thread
  02_campanha.png       — temporada 2026 (campanha geral)
  03_mandante_vis.png   — mandante vs visitante
  04_ultimos5.png       — últimos 5 jogos
  05_xg.png             — análise xG e perfil ofensivo
  06_jogadores.png      — destaque individual

Dados:
  Temporada 2026 (até 08/04/2026) — 20 partidas disputadas
  Série B: 3 jogos — 2V 1E 0D (7pts, 77%)

Saída: pending_posts/2026-04-11_raio-x-avai/
"""

import os
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from collections import deque


# ─── Helpers de imagem ────────────────────────────────────────────────────────

def _remove_bg(img, thresh=25):
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    is_white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()
    for y in range(h):
        for x in (0, w - 1):
            if is_white[y, x] and not visited[y, x]:
                visited[y, x] = True; queue.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if is_white[y, x] and not visited[y, x]:
                visited[y, x] = True; queue.append((y, x))
    while queue:
        y, x = queue.popleft(); data[y, x, 3] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True; queue.append((ny, nx))
    return Image.fromarray(data, "RGBA")


def _load_logo(path, size, remove_bg=False):
    if not HAS_PIL or not Path(path).exists():
        return None
    try:
        img = Image.open(path).convert("RGBA")
        if remove_bg:
            img = _remove_bg(img)
        return np.array(img.resize((size, size), Image.LANCZOS))
    except Exception:
        return None


# ─── Paleta @SportRecifeLab ───────────────────────────────────────────────────
BG      = "#0d0d0d"
CARD    = "#161616"
CARD2   = "#1c1c1c"
YELLOW  = "#F5C400"
WHITE   = "#FFFFFF"
LGRAY   = "#CCCCCC"
GRAY    = "#888888"
DGRAY   = "#444444"
RED     = "#CC1020"
GREEN   = "#2a9148"
BLUE    = "#003DA5"   # cor Avaí

FIG_W, FIG_H = 9.0, 9.0
DPI = 120
OUT_DIR = "pending_posts/2026-04-11_raio-x-avai"
LOGO_PATH = "data/cache/logos/7315.png"
SRL_LOGO  = "sportrecifelab_avatar.png"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

# ─── Dados da temporada 2026 (até 08/04) ─────────────────────────────────────
AVAI_2026 = {
    "total_j": 20, "total_v": 10, "total_e": 3, "total_d": 7,
    "gols_marc": 35, "gols_sof": 29, "pts": 33, "aprov": 55,
    # Mandante
    "home_j": 10, "home_v": 6, "home_e": 3, "home_d": 1,
    "home_gm": 21, "home_gs": 11, "home_pts": 21, "home_aprov": 70,
    # Visitante
    "away_j": 10, "away_v": 4, "away_e": 0, "away_d": 6,
    "away_gm": 14, "away_gs": 18, "away_pts": 12, "away_aprov": 40,
    # Série B
    "sb_j": 3, "sb_v": 2, "sb_e": 1, "sb_d": 0,
    "sb_gm": 3, "sb_gs": 0, "sb_pts": 7, "sb_aprov": 78,
    "xg_per_game": 1.25,
}

# Últimos 5 jogos completados
LAST_5 = [
    {"date": "25/03", "comp": "Copa Sul-Sudeste", "home": "Tombense",      "hs": 3, "away": "Avaí",         "as_": 2, "is_home": False, "outcome": "loss"},
    {"date": "29/03", "comp": "Copa Sul-Sudeste", "home": "Avaí",          "hs": 2, "away": "Cianorte",      "as_": 2, "is_home": True,  "outcome": "draw"},
    {"date": "02/04", "comp": "Série B R2",       "home": "CRB",           "hs": 0, "away": "Avaí",          "as_": 1, "is_home": False, "outcome": "win"},
    {"date": "05/04", "comp": "Série B R3",       "home": "Avaí",          "hs": 0, "away": "Operário-PR",   "as_": 0, "is_home": True,  "outcome": "draw"},
    {"date": "08/04", "comp": "Copa Sul-Sudeste", "home": "Chapecoense",   "hs": 2, "away": "Avaí",          "as_": 1, "is_home": False, "outcome": "loss"},
]

# Top jogadores por rating
TOP_PLAYERS = [
    {"name": "Leão Aragão",    "pos": "GOL", "j": 8,  "rating": 7.32, "shots": 0,  "assists": 0},
    {"name": "Daniel Penha",   "pos": "MEI", "j": 10, "rating": 7.20, "shots": 18, "assists": 1},
    {"name": "Douglas Teixeira","pos": "ZAG","j": 12, "rating": 7.19, "shots": 10, "assists": 0},
    {"name": "Maurício Garcez","pos": "MEI", "j": 6,  "rating": 7.18, "shots": 17, "assists": 2},
    {"name": "Jean Lucas",     "pos": "MEI", "j": 14, "rating": 7.01, "shots": 28, "assists": 1},
    {"name": "Thayllon Roberth","pos": "MEI","j": 13, "rating": 7.01, "shots": 15, "assists": 3},
]

# xG / perfil ofensivo (dados do attack_profile — base 3 jogos Série B)
XG_PROFILE = {
    "possession": 41.73,
    "xg_per_game": 1.25,
    "shots_total": 10.73,
    "shots_on_target": 3.33,
    "shots_inside_box_pct": 49.7,
    "shots_outside_box": 5.40,
    "final_third_entries": 10.33,
    "long_balls_pct": 6.9,
    "crosses_accurate": 2.6,
    "corners": 4.0,
    "interceptions": 14.33,
}


# ─── Helpers de layout ────────────────────────────────────────────────────────

def _new_fig():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def _add_srl_logo(fig):
    logo = _load_logo(SRL_LOGO, 48)
    if logo is not None:
        lax = fig.add_axes([0.030, 0.022, 0.055, 0.055])
        lax.imshow(logo); lax.axis("off")


def _add_avai_logo(fig, x=0.75, y=0.18, size=0.22):
    logo = _load_logo(LOGO_PATH, 240, remove_bg=True)
    if logo is not None:
        lax = fig.add_axes([x, y, size, size])
        lax.imshow(logo); lax.axis("off")
        lax.set_facecolor("none")
    return logo is not None


def _label(ax, x, y, text, color=GRAY, size=8, weight="normal", family=FONT_BODY,
           ha="center", va="center", alpha=1.0, zorder=4):
    ax.text(x, y, text, color=color, fontsize=size, fontweight=weight,
            fontfamily=family, ha=ha, va=va, transform=ax.transAxes,
            alpha=alpha, zorder=zorder)


def _hline(ax, y, x0=0.07, x1=0.93, color=YELLOW, lw=0.7, alpha=0.35):
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw, alpha=alpha,
            transform=ax.transAxes, zorder=3)


def _footer(ax, source="Dados: SofaScore  ·  @SportRecifeLab"):
    ax.text(0.82, 0.038, source, color=DGRAY, fontsize=7,
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=4)


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  OK {path}")


def _result_color(outcome):
    return {"win": GREEN, "draw": YELLOW, "loss": RED}.get(outcome, GRAY)


def _result_label(outcome):
    return {"win": "V", "draw": "E", "loss": "D"}.get(outcome, "?")


def _header_bar(ax, title, subtitle=""):
    ax.add_patch(patches.Rectangle((0.05, 0.916), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.956, title, color=YELLOW, size=10.5,
           weight="bold", family=FONT_TITLE)
    if subtitle:
        _label(ax, 0.50, 0.892, subtitle, color=WHITE, size=26,
               weight="bold", family=FONT_TITLE)


# ─── Card 01 — COVER ─────────────────────────────────────────────────────────

def card_cover():
    fig, ax = _new_fig()

    # Fundo diagonal decorativo
    poly = plt.Polygon([[0, 0.55], [0, 0.68], [0.50, 0.68], [0.60, 0.55]],
                       closed=True, facecolor=BLUE, alpha=0.07, zorder=1)
    ax.add_patch(poly)

    # Barra superior
    ax.add_patch(patches.Rectangle((0.05, 0.916), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.956, "SÉRIE B 2026  ·  RODADA 4",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    # Título principal
    ax.text(0.50, 0.840, "RAIO-X",
            color=YELLOW, fontsize=96, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4,
            path_effects=[pe.withStroke(linewidth=4, foreground="#0d0d0d")])

    ax.text(0.50, 0.726, "AVAÍ FC",
            color=WHITE, fontsize=48, fontweight="bold",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4)

    _hline(ax, 0.690, alpha=0.55)
    _label(ax, 0.50, 0.648, "SPORT RECEBE EM CASA",
           color=LGRAY, size=12.5, weight="bold", family=FONT_TITLE)

    # Escudo
    has_logo = _add_avai_logo(fig, x=0.07, y=0.18, size=0.26)
    if not has_logo:
        # Fallback: polígono azul com "AV"
        shield = plt.Polygon([
            [0.19, 0.56], [0.30, 0.56], [0.30, 0.48],
            [0.245, 0.40], [0.19, 0.48],
        ], closed=True, facecolor=BLUE, edgecolor=LGRAY, linewidth=1.5,
           alpha=0.85, zorder=3, transform=ax.transAxes)
        ax.add_patch(shield)
        ax.text(0.245, 0.49, "AV", color=WHITE, fontsize=28,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    # Stats (lado direito)
    d = AVAI_2026
    stats = [
        (f"{d['sb_v']}V  {d['sb_e']}E  {d['sb_d']}D", "SÉRIE B 2026",   YELLOW),
        (f"+{d['sb_gm']-d['sb_gs']}",                   "SALDO S.B.",     GREEN),
        (f"{d['sb_aprov']}%",                            "APROVEITAMENTO", LGRAY),
        (f"{d['xg_per_game']:.2f}".replace('.',','),    "xG / JOGO",      BLUE),
    ]
    sx, sy_start, row_gap = 0.73, 0.570, 0.112

    for k, (val, lbl, color) in enumerate(stats):
        sy = sy_start - k * row_gap
        ax.add_patch(FancyBboxPatch((sx - 0.21, sy - 0.044), 0.42, 0.086,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=DGRAY,
                                    linewidth=0.6, zorder=2))
        ax.text(sx, sy + 0.010, val, color=color, fontsize=18,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(sx, sy - 0.025, lbl, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_srl_logo(fig)
    _save(fig, "01_cover.png")


# ─── Card 02 — CAMPANHA ───────────────────────────────────────────────────────

def card_campanha():
    fig, ax = _new_fig()

    _header_bar(ax, "TEMPORADA 2026  ·  TODAS AS COMPETIÇÕES")
    _label(ax, 0.50, 0.892, "AVAÍ FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.852, f"{AVAI_2026['total_j']} PARTIDAS DISPUTADAS",
           color=GRAY, size=10, family=FONT_BODY)
    _hline(ax, 0.828)

    # V/E/D
    results = [
        (AVAI_2026["total_v"], "VITÓRIAS",  GREEN),
        (AVAI_2026["total_e"], "EMPATES",   YELLOW),
        (AVAI_2026["total_d"], "DERROTAS",  RED),
    ]
    xs = [0.20, 0.50, 0.80]
    for (n, lbl, color), x in zip(results, xs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.615), 0.26, 0.190,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=color,
                                    linewidth=2.0, zorder=2))
        ax.text(x, 0.730, str(n), color=color, fontsize=56,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.630, lbl, color=LGRAY, fontsize=9,
                fontfamily=FONT_BODY, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    _hline(ax, 0.606)
    pts = AVAI_2026["pts"]; aprov = AVAI_2026["aprov"]
    _label(ax, 0.50, 0.576, f"{pts} pontos  ·  {aprov}% de aproveitamento",
           color=LGRAY, size=10.5, weight="bold", family=FONT_BODY)
    _hline(ax, 0.553, alpha=0.25)

    # Gols
    gm = AVAI_2026["gols_marc"]; gs = AVAI_2026["gols_sof"]
    gol_data = [
        ("GOLS\nMARCADOS", str(gm),   YELLOW),
        ("SALDO\nDE GOLS",  f"+{gm-gs}" if gm>gs else str(gm-gs), GREEN if gm>gs else RED),
        ("GOLS\nSOFRIDOS",  str(gs),   RED),
    ]
    for (lbl, val, color), x in zip(gol_data, xs):
        ax.text(x, 0.484, val, color=color, fontsize=40,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.418, lbl, color=GRAY, fontsize=8.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4, linespacing=1.4)

    _hline(ax, 0.385, alpha=0.25)

    # Competições
    comps = [
        ("Catarinense", "11 jogos"),
        ("Copa do Brasil", "2 jogos"),
        ("Copa Sul-Sud.", "6 jogos"),
        ("Série B",    "3 jogos"),
    ]
    cx = [0.15, 0.39, 0.63, 0.86]
    for (comp, n), x in zip(comps, cx):
        ax.text(x, 0.348, n, color=YELLOW, fontsize=14,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.312, comp, color=GRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.285, alpha=0.18)

    # Callout Série B
    ax.add_patch(FancyBboxPatch((0.07, 0.182), 0.86, 0.092,
                                boxstyle="round,pad=0.01",
                                facecolor=CARD2, edgecolor=BLUE,
                                linewidth=1.5, zorder=3))
    sb = AVAI_2026
    ax.text(0.50, 0.238,
            f"SÉRIE B: {sb['sb_v']}V {sb['sb_e']}E {sb['sb_d']}D  "
            f"— {sb['sb_pts']} pts  ·  {sb['sb_aprov']}% aproveitamento",
            color=WHITE, fontsize=9.5, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.200,
            f"GM {sb['sb_gm']}  GS {sb['sb_gs']}  ·  invictos na B",
            color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax)
    _add_srl_logo(fig)
    _save(fig, "02_campanha.png")


# ─── Card 03 — MANDANTE vs VISITANTE ────────────────────────────────────────

def card_mandante_vis():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.916), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.956, "MANDANTE vs VISITANTE  ·  2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.892, "AVAÍ FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.852, "Sport recebe em Ilha da Saudade — como o Leão se sai fora?",
           color=GRAY, size=9.5, family=FONT_BODY)
    _hline(ax, 0.828)

    xs = [0.27, 0.73]
    labels = ["MANDANTE", "VISITANTE"]
    colors_label = [GREEN, YELLOW]
    sections = [
        {
            "aprov": AVAI_2026["home_aprov"], "j": AVAI_2026["home_j"],
            "v": AVAI_2026["home_v"], "e": AVAI_2026["home_e"], "d": AVAI_2026["home_d"],
            "gm": AVAI_2026["home_gm"], "gs": AVAI_2026["home_gs"],
            "color": GREEN,
        },
        {
            "aprov": AVAI_2026["away_aprov"], "j": AVAI_2026["away_j"],
            "v": AVAI_2026["away_v"], "e": AVAI_2026["away_e"], "d": AVAI_2026["away_d"],
            "gm": AVAI_2026["away_gm"], "gs": AVAI_2026["away_gs"],
            "color": YELLOW,
        },
    ]

    # Divisor vertical
    ax.plot([0.50, 0.50], [0.12, 0.82], color=DGRAY, lw=0.8,
            transform=ax.transAxes, zorder=2)

    for (x, lbl, clr_lbl, sec) in zip(xs, labels, colors_label, sections):
        # Label de seção
        ax.add_patch(FancyBboxPatch((x - 0.195, 0.775), 0.390, 0.042,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=sec["color"],
                                    linewidth=1.5, zorder=2))
        _label(ax, x, 0.795, lbl, color=clr_lbl, size=11, weight="bold",
               family=FONT_TITLE)

        # Aproveitamento
        ax.text(x, 0.714, f"{sec['aprov']}%",
                color=sec["color"], fontsize=56, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        _label(ax, x, 0.663, f"APROVEITAMENTO  ·  {sec['j']} JOGOS",
               color=GRAY, size=8.5, family=FONT_BODY)

        _hline(ax, 0.641, x0=x - 0.20, x1=x + 0.20, alpha=0.4)

        # V/E/D
        veds = [(str(sec["v"]), GREEN), (str(sec["e"]), YELLOW), (str(sec["d"]), RED)]
        for i, (val, col) in enumerate(veds):
            vx = x + (i - 1) * 0.135
            ax.text(vx, 0.592, val, color=col, fontsize=34,
                    fontweight="black", fontfamily=FONT_TITLE,
                    ha="center", va="center", transform=ax.transAxes, zorder=4)

        _label(ax, x - 0.135, 0.552, "V", color=GREEN, size=8, family=FONT_BODY)
        _label(ax, x,         0.552, "E", color=YELLOW, size=8, family=FONT_BODY)
        _label(ax, x + 0.135, 0.552, "D", color=RED,   size=8, family=FONT_BODY)

        _hline(ax, 0.530, x0=x - 0.20, x1=x + 0.20, alpha=0.3)

        # Gols
        saldo = sec["gm"] - sec["gs"]
        gols_cols = [
            (str(sec["gm"]), "MARCADOS", YELLOW),
            (f"+{saldo}" if saldo >= 0 else str(saldo), "SALDO", GREEN if saldo >= 0 else RED),
            (str(sec["gs"]), "SOFRIDOS", RED),
        ]
        for i, (val, glbl, col) in enumerate(gols_cols):
            gx = x + (i - 1) * 0.135
            ax.text(gx, 0.480, val, color=col, fontsize=28,
                    fontweight="black", fontfamily=FONT_TITLE,
                    ha="center", va="center", transform=ax.transAxes, zorder=4)
            _label(ax, gx, 0.448, glbl, color=GRAY, size=7.5, family=FONT_BODY)

        _hline(ax, 0.425, x0=x - 0.20, x1=x + 0.20, alpha=0.25)

        # Médias por jogo
        gm_pg = sec["gm"] / sec["j"] if sec["j"] else 0
        gs_pg = sec["gs"] / sec["j"] if sec["j"] else 0
        meds = [
            (f"{gm_pg:.1f}", "GM/JOGO"),
            (f"{gs_pg:.1f}", "GS/JOGO"),
        ]
        for i, (val, mlbl) in enumerate(meds):
            mx = x + (i - 0.5) * 0.16
            ax.text(mx, 0.384, val, color=LGRAY, fontsize=22,
                    fontweight="black", fontfamily=FONT_TITLE,
                    ha="center", va="center", transform=ax.transAxes, zorder=4)
            _label(ax, mx, 0.350, mlbl, color=GRAY, size=7.5, family=FONT_BODY)

    _hline(ax, 0.320, alpha=0.18)

    # Callout insight
    ax.add_patch(FancyBboxPatch((0.07, 0.175), 0.86, 0.130,
                                boxstyle="round,pad=0.01",
                                facecolor=CARD2, edgecolor=BLUE,
                                linewidth=1.2, zorder=3))
    ax.text(0.50, 0.258,
            "Forte em casa (70%), fragil fora (40%) — 6 derrotas como visitante",
            color=LGRAY, fontsize=9.5, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.218,
            "Em Recife, contexto favorável ao Sport — Avaí perde 60% dos jogos fora",
            color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.192,
            "Serie B: nenhuma derrota ainda (2V 1E fora = CRB e empate vs Operário)",
            color=GRAY, fontsize=7.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax)
    _add_srl_logo(fig)
    _save(fig, "03_mandante_vis.png")


# ─── Card 04 — ÚLTIMOS 5 ─────────────────────────────────────────────────────

def card_ultimos5():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.916), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.956, "FORMA RECENTE  ·  ÚLTIMOS 5 JOGOS",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.892, "AVAÍ FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _hline(ax, 0.862)

    row_h = 0.128
    y_top = 0.840

    for i, g in enumerate(LAST_5):
        y = y_top - i * row_h
        outcome = g["outcome"]
        color = _result_color(outcome)
        badge = _result_label(outcome)
        is_home = g["is_home"]

        # Badge V/E/D
        ax.add_patch(FancyBboxPatch((0.065, y - 0.058), 0.068, 0.062,
                                    boxstyle="round,pad=0.01",
                                    facecolor=color, edgecolor="none",
                                    alpha=0.15, zorder=2))
        ax.text(0.099, y - 0.026, badge,
                color=color, fontsize=22, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        # Placar e times
        home_col = YELLOW if is_home else WHITE
        away_col = YELLOW if not is_home else WHITE

        ax.text(0.158, y - 0.014, g["date"],
                color=GRAY, fontsize=7.5, fontfamily=FONT_BODY,
                ha="left", va="center", transform=ax.transAxes)
        ax.text(0.158, y - 0.038, g["comp"],
                color=DGRAY, fontsize=7, fontfamily=FONT_BODY,
                ha="left", va="center", transform=ax.transAxes)

        ax.text(0.415, y - 0.026, g["home"],
                color=home_col, fontsize=9.5, fontweight="bold",
                fontfamily=FONT_TITLE, ha="right", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(0.500, y - 0.026, f"{g['hs']}–{g['as_']}",
                color=WHITE, fontsize=13, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(0.585, y - 0.026, g["away"],
                color=away_col, fontsize=9.5, fontweight="bold",
                fontfamily=FONT_TITLE, ha="left", va="center",
                transform=ax.transAxes, zorder=4)

        if i < len(LAST_5) - 1:
            _hline(ax, y - 0.070, x0=0.07, x1=0.93, color=DGRAY, lw=0.4, alpha=0.8)

    _hline(ax, 0.188, alpha=0.2)

    # Forma resumida
    form_str = "".join(_result_label(g["outcome"]) for g in LAST_5)
    _label(ax, 0.50, 0.167, f"Sequência:  {form_str}",
           color=LGRAY, size=10, weight="bold", family=FONT_TITLE)

    # Mini callout
    last_sb = [g for g in LAST_5 if "Série B" in g["comp"]]
    if last_sb:
        sb_form = "  ".join(_result_label(g["outcome"]) for g in last_sb)
        _label(ax, 0.50, 0.138, f"Na Série B: {sb_form}",
               color=GRAY, size=9, family=FONT_BODY)

    _footer(ax)
    _add_srl_logo(fig)
    _save(fig, "04_ultimos5.png")


# ─── Card 05 — xG / PERFIL OFENSIVO ─────────────────────────────────────────

def card_xg():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.916), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.956, "PERFIL OFENSIVO  ·  SÉRIE B 2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.892, "AVAÍ FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.852, "Média por partida — base: 3 jogos Série B",
           color=GRAY, size=9, family=FONT_BODY)
    _hline(ax, 0.828)

    p = XG_PROFILE

    # xG destaque
    ax.add_patch(FancyBboxPatch((0.07, 0.710), 0.86, 0.110,
                                boxstyle="round,pad=0.01",
                                facecolor=CARD2, edgecolor=BLUE,
                                linewidth=1.8, zorder=2))
    ax.text(0.50, 0.777, f"{p['xg_per_game']:.2f}".replace('.', ','),
            color=YELLOW, fontsize=48, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4)
    _label(ax, 0.50, 0.724, "xG POR PARTIDA  (gols esperados)",
           color=GRAY, size=9, family=FONT_BODY)

    _hline(ax, 0.700, alpha=0.25)

    # Métricas em grid 2×3
    metrics = [
        ("Posse de bola",      f"{p['possession']:.0f}%",   YELLOW),
        ("Chutes/jogo",        f"{p['shots_total']:.1f}",   LGRAY),
        ("No alvo",            f"{p['shots_on_target']:.1f}", GREEN),
        ("Fora da área",       f"{p['shots_outside_box']:.1f}/j",  RED),
        ("Ent. último terço",  f"{p['final_third_entries']:.0f}/j", LGRAY),
        ("Bolas longas",       f"{p['long_balls_pct']:.1f}%",      LGRAY),
    ]
    cols = [0.195, 0.500, 0.800]
    rows_y = [0.632, 0.528]
    for i, (lbl, val, color) in enumerate(metrics):
        gx = cols[i % 3]
        gy = rows_y[i // 3]
        ax.add_patch(FancyBboxPatch((gx - 0.135, gy - 0.048), 0.270, 0.092,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=DGRAY,
                                    linewidth=0.5, zorder=2))
        ax.text(gx, gy + 0.020, val, color=color, fontsize=20,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(gx, gy - 0.020, lbl, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.474, alpha=0.25)

    # Zona de ataque (barra horizontal — centro dominante)
    _label(ax, 0.50, 0.448, "ZONA DE FINALIZAÇÃO",
           color=LGRAY, size=9, weight="bold", family=FONT_TITLE)

    zones = [("ESQ", 11.5, LGRAY), ("CENTRO", 77.0, BLUE), ("DIR", 11.5, LGRAY)]
    bx0, bw, by, bh = 0.07, 0.86, 0.388, 0.038
    total = sum(p for _, p, _ in zones)
    x_cur = bx0
    for lbl, pct, col in zones:
        w = bw * pct / total
        ax.add_patch(patches.Rectangle((x_cur, by), w, bh,
                                       facecolor=col, alpha=0.85,
                                       edgecolor="none", zorder=3))
        if pct > 10:
            ax.text(x_cur + w / 2, by + bh / 2, f"{lbl}  {pct:.0f}%",
                    color=WHITE, fontsize=8.5, fontweight="bold",
                    fontfamily=FONT_BODY, ha="center", va="center",
                    transform=ax.transAxes, zorder=5)
        x_cur += w

    _hline(ax, 0.368, alpha=0.2)

    # Padrões detectados
    patterns_text = [
        "Equipe reativa — cede posse (42%) e joga em contra-ataque",
        "77% dos chutes originam-se pelo corredor central",
        "Frequencia de finalizações de fora da area (50% dos chutes)",
        "Baixo volume no ultimo terco — apenas 10 entradas por jogo",
    ]
    icons = ["\u25cf", "\u2666", "\u25b2", "\u25c4"]
    y0 = 0.345
    for icon, txt in zip(icons, patterns_text):
        ax.text(0.080, y0, icon, color=YELLOW, fontsize=8,
                fontfamily=FONT_BODY, ha="left", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(0.110, y0, txt, color=LGRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="left", va="center",
                transform=ax.transAxes, zorder=4)
        y0 -= 0.060

    _footer(ax)
    _add_srl_logo(fig)
    _save(fig, "05_xg.png")


# ─── Card 06 — JOGADORES-CHAVE ────────────────────────────────────────────────

def card_jogadores():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.916), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.956, "JOGADORES-CHAVE  ·  TEMPORADA 2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.892, "AVAÍ FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.852, "Ranking por média de rating — mínimo 5 partidas",
           color=GRAY, size=9, family=FONT_BODY)
    _hline(ax, 0.828)

    # Header de coluna
    _label(ax, 0.08, 0.806, "#",     color=DGRAY, size=8, family=FONT_TITLE)
    _label(ax, 0.22, 0.806, "JOGADOR",color=DGRAY, size=8, family=FONT_TITLE, ha="left")
    _label(ax, 0.52, 0.806, "POS",   color=DGRAY, size=8, family=FONT_TITLE)
    _label(ax, 0.65, 0.806, "JOGOS", color=DGRAY, size=8, family=FONT_TITLE)
    _label(ax, 0.80, 0.806, "RATING",color=DGRAY, size=8, family=FONT_TITLE)
    _hline(ax, 0.796, color=DGRAY, alpha=0.6)

    row_h = 0.096
    y_top = 0.772

    for i, p in enumerate(TOP_PLAYERS):
        y = y_top - i * row_h
        is_top = i == 0
        txt_color = YELLOW if is_top else WHITE
        bg_color  = CARD2

        ax.add_patch(FancyBboxPatch((0.065, y - 0.054), 0.870, 0.070,
                                    boxstyle="round,pad=0.005",
                                    facecolor=bg_color,
                                    edgecolor=BLUE if is_top else DGRAY,
                                    linewidth=1.8 if is_top else 0.4, zorder=2))

        # Rank
        ax.text(0.085, y - 0.018, str(i + 1),
                color=YELLOW if is_top else GRAY, fontsize=14 if is_top else 11,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

        # Nome
        ax.text(0.215, y - 0.018, p["name"],
                color=txt_color, fontsize=10 if is_top else 9,
                fontweight="bold", fontfamily=FONT_TITLE,
                ha="left", va="center", transform=ax.transAxes, zorder=4)

        # Posição
        pos_colors = {"GOL": "#88AAFF", "ZAG": "#AAAAAA", "MEI": GREEN, "ATA": RED}
        pcol = pos_colors.get(p["pos"], LGRAY)
        ax.add_patch(FancyBboxPatch((0.488, y - 0.036), 0.072, 0.038,
                                    boxstyle="round,pad=0.01",
                                    facecolor=pcol, alpha=0.2,
                                    edgecolor=pcol, linewidth=0.8, zorder=3))
        ax.text(0.524, y - 0.018, p["pos"],
                color=pcol, fontsize=8, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=5)

        # Jogos
        ax.text(0.648, y - 0.018, str(p["j"]),
                color=LGRAY, fontsize=10, fontweight="bold",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        # Rating bar
        bar_w = 0.18
        bar_x = 0.740
        rating_pct = (p["rating"] - 6.0) / 2.0   # 6–8 scale
        ax.add_patch(patches.Rectangle((bar_x, y - 0.030), bar_w, 0.022,
                                       facecolor=DGRAY, edgecolor="none",
                                       transform=ax.transAxes, zorder=3))
        ax.add_patch(patches.Rectangle((bar_x, y - 0.030), bar_w * rating_pct, 0.022,
                                       facecolor=YELLOW if is_top else BLUE,
                                       edgecolor="none",
                                       transform=ax.transAxes, zorder=4))
        ax.text(bar_x + bar_w + 0.015, y - 0.018, f"{p['rating']:.2f}",
                color=txt_color, fontsize=9.5, fontweight="bold",
                fontfamily=FONT_TITLE, ha="left", va="center",
                transform=ax.transAxes, zorder=5)

        # Info extra (shots/assists) para os 3 primeiros
        if i < 3 and (p["shots"] or p["assists"]):
            extras = []
            if p["shots"]: extras.append(f"{p['shots']} chutes")
            if p["assists"]: extras.append(f"{p['assists']} assist.")
            if extras:
                ax.text(0.215, y - 0.042, "  ·  ".join(extras),
                        color=GRAY, fontsize=7, fontfamily=FONT_BODY,
                        ha="left", va="center", transform=ax.transAxes, zorder=4)

    _hline(ax, y_top - len(TOP_PLAYERS) * row_h + 0.018, color=DGRAY, alpha=0.4)

    # Nota
    _label(ax, 0.50, 0.108,
           "Jean Lucas lidera em chutes (28) e minutos (1043). "
           "Thayllon tem 3 assist. na temporada.",
           color=GRAY, size=7.5, family=FONT_BODY)

    _footer(ax)
    _add_srl_logo(fig)
    _save(fig, "06_jogadores.png")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Gerando cards Raio-X: Avaí FC...")
    card_cover()
    card_campanha()
    card_mandante_vis()
    card_ultimos5()
    card_xg()
    card_jogadores()
    print("Pronto.")


if __name__ == "__main__":
    main()
