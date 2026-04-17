"""
Gera os cards visuais da thread "Raio-X: América Mineiro"
Série B 2026 | Rodada 5 — @SportRecifeLab

Cards produzidos:
  01_cover.png          — abertura da thread
  02_campanha.png       — temporada 2026 (campanha geral)
  03_mandante_vis.png   — América como mandante (Sport joga em BH)
  04_ultimos5.png       — últimos 5 jogos
  05_xg.png             — análise xG e perfil ofensivo
  06_jogadores.png      — destaque individual

Saída: pending_posts/2026-04-18_raio-x-america-mg/

Dados extraídos via pipeline SofaScore (sync-opponent america-mg 1973).
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from collections import deque


# ─── BFS logo background removal ────────────────────────────────────────────

def _remove_bg_floodfill(img: "Image.Image", thresh: int = 25) -> "Image.Image":
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    is_white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)
    visited = np.zeros((h, w), dtype=bool)
    queue: deque = deque()
    for y in range(h):
        for x in (0, w - 1):
            if is_white[y, x] and not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if is_white[y, x] and not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        data[y, x, 3] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))
    return Image.fromarray(data, "RGBA")


def _load_logo(team_id: int, size: int = 220) -> "np.ndarray | None":
    """Carrega escudo do cache local, remove fundo e redimensiona."""
    path = f"data/cache/logos/{team_id}.png"
    if not HAS_PIL or not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = _remove_bg_floodfill(img, thresh=25)
        img = img.resize((size, size), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None


# ─── Paleta @SportRecifeLab ──────────────────────────────────────────────────
BG     = "#0d0d0d"
CARD   = "#161616"
CARD2  = "#1c1c1c"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
LGRAY  = "#CCCCCC"
GRAY   = "#888888"
DGRAY  = "#444444"
RED    = "#CC1020"
GREEN  = "#2a9148"
GREEN2 = "#1e6b33"

# América Mineiro verde — acento sutil para o adversário
AM_GREEN = "#007A37"  # verde bandeira do América Mineiro

# ─── Layout ──────────────────────────────────────────────────────────────────
FIG_W, FIG_H = 9.0, 9.0   # 1080×1080 @ 120 dpi
DPI = 120
OUT_DIR = "pending_posts/2026-04-18_raio-x-america-mg"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

AMERICA_ID = 1973


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _new_fig():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _add_logo(fig, path="sportrecifelab_avatar.png"):
    if not HAS_PIL or not os.path.exists(path):
        return
    try:
        img = Image.open(path).convert("RGBA")
        img = img.resize((60, 60), Image.LANCZOS)
        arr = np.array(img)
        logo_ax = fig.add_axes([0.05, 0.025, 0.07, 0.07])
        logo_ax.imshow(arr)
        logo_ax.axis("off")
    except Exception:
        pass


def _label(ax, x, y, text, color=GRAY, size=8, weight="normal", family=FONT_BODY,
           ha="center", va="center", alpha=1.0, zorder=4):
    ax.text(x, y, text, color=color, fontsize=size, fontweight=weight,
            fontfamily=family, ha=ha, va=va, transform=ax.transAxes,
            alpha=alpha, zorder=zorder)


def _hline(ax, y, x0=0.07, x1=0.93, color=YELLOW, lw=0.7, alpha=0.35):
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw, alpha=alpha,
            transform=ax.transAxes, zorder=3)


def _badge(ax, x, y, text, bg=YELLOW, fg="#111111", size=8.5, pad=0.3):
    ax.text(x, y, text, color=fg, fontsize=size, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            bbox=dict(boxstyle=f"round,pad={pad}", facecolor=bg,
                      edgecolor="none", alpha=0.95),
            transform=ax.transAxes, zorder=5)


def _footer(ax, source="SofaScore · @SportRecifeLab"):
    ax.text(0.84, 0.038, source, color=DGRAY, fontsize=7,
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


def _draw_shield_placeholder(ax, cx, cy, r=0.130):
    """Escudo geométrico fallback com cores do América Mineiro."""
    shield = plt.Polygon([
        [cx,       cy + r],
        [cx + r,   cy + r * 0.55],
        [cx + r,   cy - r * 0.25],
        [cx,       cy - r],
        [cx - r,   cy - r * 0.25],
        [cx - r,   cy + r * 0.55],
    ], closed=True, facecolor=AM_GREEN, edgecolor=WHITE,
       linewidth=1.5, alpha=0.85, zorder=3, transform=ax.transAxes)
    ax.add_patch(shield)
    ax.text(cx, cy + 0.010, "AM", color=WHITE, fontsize=32,
            fontweight="black", fontfamily=FONT_TITLE,
            ha="center", va="center", transform=ax.transAxes, zorder=4)


# ─── Card 01 — COVER ─────────────────────────────────────────────────────────

def card_cover():
    fig, ax = _new_fig()

    # Faixa diagonal decorativa (verde América, bem sutil)
    poly = plt.Polygon([[0, 0.56], [0, 0.66], [0.45, 0.66], [0.55, 0.56]],
                       closed=True, facecolor=AM_GREEN, alpha=0.05, zorder=1)
    ax.add_patch(poly)

    # Borda superior amarela fina
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))

    # Label superior
    _label(ax, 0.50, 0.950, "SÉRIE B 2026  ·  RODADA 5",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    # Título RAIO-X
    ax.text(0.50, 0.840, "RAIO-X",
            color=YELLOW, fontsize=96, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4,
            path_effects=[pe.withStroke(linewidth=4, foreground="#0d0d0d")])

    # Subtítulo
    ax.text(0.50, 0.728, "AMÉRICA MINEIRO",
            color=WHITE, fontsize=36, fontweight="bold",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4)

    _hline(ax, 0.690, alpha=0.55)

    # Contexto do confronto
    _label(ax, 0.50, 0.648, "SPORT JOGA COMO VISITANTE EM BH",
           color=LGRAY, size=12.5, weight="bold", family=FONT_TITLE)

    # --- Escudo do América Mineiro ---
    logo_arr = _load_logo(AMERICA_ID, size=220)
    if logo_arr is not None:
        try:
            logo_ax = fig.add_axes([0.04, 0.17, 0.28, 0.28])
            logo_ax.imshow(logo_arr)
            logo_ax.set_facecolor(BG)
            logo_ax.axis("off")
        except Exception:
            _draw_shield_placeholder(ax, 0.195, 0.340)
    else:
        _draw_shield_placeholder(ax, 0.195, 0.340)

    # --- Stats (lado direito) ---
    # América: 16º, 1pt, xG 1.64/j mas 0V na Série B — paradoxo posse vs resultado
    stats = [
        ("16º / 1pt",   "SÉRIE B 2026",        RED),
        ("0V  1E  3D",  "CAMPANHA SÉRIE B",     RED),
        ("67%",         "POSSE MÉDIA",          LGRAY),
        ("1.64",        "xG GERADO / JOGO",     YELLOW),
    ]
    sx = 0.72
    sy_start = 0.570
    row_gap = 0.112

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
    _add_logo(fig)
    _save(fig, "01_cover.png")


# ─── Card 02 — CAMPANHA GERAL ────────────────────────────────────────────────

def card_campanha():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "TEMPORADA 2026  ·  TODAS AS COMPETIÇÕES",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.870, "AMÉRICA MINEIRO",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.828, "20 PARTIDAS DISPUTADAS",
           color=GRAY, size=10, family=FONT_BODY)

    _hline(ax, 0.805)

    # V/E/D
    results = [
        (6,  "VITÓRIAS",  GREEN,  "6V"),
        (7,  "EMPATES",   YELLOW, "7E"),
        (7,  "DERROTAS",  RED,    "7D"),
    ]
    xs = [0.20, 0.50, 0.80]
    for (n, lbl, color, badge), x in zip(results, xs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.60), 0.26, 0.185,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=color,
                                    linewidth=2.0, zorder=2))
        ax.text(x, 0.720, str(n), color=color, fontsize=56,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.622, lbl, color=LGRAY, fontsize=9,
                fontfamily=FONT_BODY, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    _hline(ax, 0.590)

    # Aproveitamento
    pts = 6 * 3 + 7  # 25
    aprov = pts / (20 * 3) * 100  # 41.7%
    _label(ax, 0.50, 0.558, f"{pts} pontos  ·  {aprov:.0f}% de aproveitamento",
           color=LGRAY, size=10.5, weight="bold", family=FONT_BODY)

    _hline(ax, 0.535, alpha=0.25)

    # Gols
    gol_data = [
        ("GOLS\nMARCADOS", "31",  YELLOW),
        ("SALDO\nDE GOLS",  "−4", RED),
        ("GOLS\nSOFRIDOS",  "35",  RED),
    ]
    for (lbl, val, color), x in zip(gol_data, xs):
        ax.text(x, 0.465, val, color=color, fontsize=40,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.398, lbl, color=GRAY, fontsize=8.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4, linespacing=1.4)

    _hline(ax, 0.365, alpha=0.25)

    # Competições disputadas
    comps = [
        ("Min. Módulo I", "11 jogos"),
        ("Copa do Brasil", "3 jogos"),
        ("Copa Sul-Sud.", "4 jogos"),
        ("Série B",        "4 jogos"),
    ]
    cx_list = [0.16, 0.39, 0.62, 0.84]
    for (comp, n), x in zip(comps, cx_list):
        ax.text(x, 0.330, n, color=YELLOW, fontsize=14,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.293, comp, color=GRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_logo(fig)
    _save(fig, "02_campanha.png")


# ─── Card 03 — MANDANTE (Sport joga em BH, América em casa) ──────────────────

def card_mandante_vis():
    """América como mandante — Sport vai a Belo Horizonte."""
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "AMÉRICA COMO MANDANTE  ·  2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.876, "AMÉRICA MINEIRO",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.836, "Sport visita o Independência — como o Coelho se sai em casa?",
           color=GRAY, size=9.5, family=FONT_BODY)

    _hline(ax, 0.812)

    cx = 0.50

    # Aproveitamento em casa: 5V 1E 4D → 16pt / 30 = 53%
    ax.text(cx, 0.738, "53%", color=YELLOW, fontsize=80,
            fontweight="black", fontfamily=FONT_TITLE,
            ha="center", va="center", transform=ax.transAxes, zorder=4)
    _label(ax, cx, 0.683, "APROVEITAMENTO COMO MANDANTE  ·  10 JOGOS",
           color=GRAY, size=9, family=FONT_BODY)

    _hline(ax, 0.660, alpha=0.4)

    # V/E/D em casa: 5V 1E 4D
    ved = [("5", "VITÓRIAS", GREEN), ("1", "EMPATE", YELLOW), ("4", "DERROTAS", RED)]
    vxs = [0.22, 0.50, 0.78]
    for (n, lbl, color), x in zip(ved, vxs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.570), 0.26, 0.082,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=color,
                                    linewidth=2.0, zorder=2))
        ax.text(x, 0.622, n, color=color, fontsize=38,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.582, lbl, color=LGRAY, fontsize=8,
                fontweight="bold", fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    _hline(ax, 0.558, alpha=0.3)

    # Gols em casa: 18 GM / 18 GC (equilíbrio)
    gol_cols = [
        ("18",  "GOLS MARCADOS",  YELLOW),
        ("18",  "GOLS SOFRIDOS",  RED),
        ("0",   "SALDO",          GRAY),
    ]
    for (val, lbl, color), x in zip(gol_cols, vxs):
        ax.text(x, 0.508, val, color=color, fontsize=36,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.468, lbl, color=GRAY, fontsize=8.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.446, alpha=0.3)

    # Métricas Série B em casa (2 jogos como mandante: R2 e R4)
    # R2: 1-2 Botafogo; R4: 0-3 Grêmio Nov → 0V 0E 2D (Série B em casa)
    med_cols = [
        ("0V 0E 2D",   "SÉRIE B EM CASA"),
        ("1",          "GOLS MARC (SérieB)"),
        ("5",          "GOLS SOF (SérieB)"),
    ]
    for (val, lbl), x in zip(med_cols, vxs):
        ax.text(x, 0.408, val, color=RED, fontsize=22,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.374, lbl, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.350, alpha=0.3)

    # xG Série B em casa
    xg_cols = [
        ("1.19",  "xG JOGO 2 (vs BFC)",   YELLOW),
        ("0.00",  "xG JOGO 4 (vs GNov)",  RED),
        ("67%",   "POSSE MÉDIA",           LGRAY),
    ]
    for (val, lbl, color), x in zip(xg_cols, vxs):
        ax.text(x, 0.310, val, color=color, fontsize=22,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.276, lbl, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.252, alpha=0.2)

    # Callout
    ax.add_patch(FancyBboxPatch((0.07, 0.155), 0.86, 0.086,
                                boxstyle="round,pad=0.01",
                                facecolor=CARD2, edgecolor=GREEN2,
                                linewidth=1.2, zorder=3))
    ax.text(cx, 0.200, "Série B em casa: 2 jogos, 2 derrotas, 5 gols sofridos",
            color=YELLOW, fontsize=9.5, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(cx, 0.168, "Domina a posse mas não converte — vulnerável a contra-ataques diretos",
            color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax)
    _add_logo(fig)
    _save(fig, "03_mandante_vis.png")


# ─── Card 04 — ÚLTIMOS 5 JOGOS ───────────────────────────────────────────────

def card_ultimos5():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "FORMA RECENTE  ·  ÚLTIMOS 5 JOGOS",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.875, "AMÉRICA MINEIRO",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _hline(ax, 0.845)

    # Mais recente → mais antigo (exibido de cima pra baixo)
    games = [
        {
            "date":    "15/04",
            "comp":    "Copa Sul-Sudeste",
            "home":    "América Mineiro",
            "hs":      2,
            "away":    "Sampaio Corrêa",
            "as_":     1,
            "is_home": True,
            "outcome": "win",
        },
        {
            "date":    "12/04",
            "comp":    "Série B R4",
            "home":    "América Mineiro",
            "hs":      0,
            "away":    "Grêmio Nov.",
            "as_":     3,
            "is_home": True,
            "outcome": "loss",
        },
        {
            "date":    "09/04",
            "comp":    "Copa Sul-Sudeste",
            "home":    "Tombense",
            "hs":      3,
            "away":    "América Mineiro",
            "as_":     3,
            "is_home": False,
            "outcome": "draw",
        },
        {
            "date":    "05/04",
            "comp":    "Série B R3",
            "home":    "Athletic Club",
            "hs":      1,
            "away":    "América Mineiro",
            "as_":     1,
            "is_home": False,
            "outcome": "draw",
        },
        {
            "date":    "01/04",
            "comp":    "Série B R2",
            "home":    "América Mineiro",
            "hs":      1,
            "away":    "Botafogo-SP",
            "as_":     2,
            "is_home": True,
            "outcome": "loss",
        },
    ]

    row_h  = 0.130
    box_h  = 0.108
    half_h = box_h / 2
    y_start = 0.806

    for i, g in enumerate(games):
        y = y_start - i * row_h
        y_bot = y - half_h
        outcome_color = _result_color(g["outcome"])
        outcome_label = _result_label(g["outcome"])

        row_bg = CARD if i % 2 == 0 else CARD2
        ax.add_patch(FancyBboxPatch((0.07, y_bot), 0.86, box_h,
                                    boxstyle="round,pad=0.005",
                                    facecolor=row_bg, edgecolor="none",
                                    zorder=2))
        ax.add_patch(patches.Rectangle((0.07, y_bot), 0.012, box_h,
                                       facecolor=outcome_color, zorder=3))

        _badge(ax, 0.906, y, outcome_label, bg=outcome_color,
               fg=("#111111" if g["outcome"] == "draw" else WHITE),
               size=11, pad=0.38)

        date_y = y + half_h * 0.38
        comp_y = y - half_h * 0.40

        ax.text(0.118, date_y, g["date"], color=LGRAY, fontsize=9,
                fontweight="bold", fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.118, comp_y, g["comp"], color=DGRAY, fontsize=7,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        am_color = YELLOW
        opp_color = LGRAY
        if g["is_home"]:
            h_color, a_color = am_color, opp_color
            h_weight, a_weight = "black", "normal"
        else:
            h_color, a_color = opp_color, am_color
            h_weight, a_weight = "normal", "black"

        ax.text(0.345, y, g["home"], color=h_color, fontsize=10.5,
                fontweight=h_weight, fontfamily=FONT_BODY,
                ha="right", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.500, y, f"{g['hs']} – {g['as_']}", color=WHITE,
                fontsize=14, fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.655, y, g["away"], color=a_color, fontsize=10.5,
                fontweight=a_weight, fontfamily=FONT_BODY,
                ha="left", va="center", transform=ax.transAxes, zorder=4)

    last_row_bot = y_start - 4 * row_h - half_h
    hline_y = last_row_bot - 0.030
    pills_y  = hline_y - 0.048
    label_y  = hline_y - 0.018

    _hline(ax, hline_y, alpha=0.3)
    _label(ax, 0.50, label_y, "FORMA NOS ÚLTIMOS 5:",
           color=GRAY, size=9, family=FONT_BODY)

    # W, L, D, D, L → mais recente primeiro
    pill_colors = [GREEN, RED, YELLOW, YELLOW, RED]
    pill_labels = ["V",   "D", "E",    "E",    "D"]
    pill_xs = [0.32, 0.41, 0.50, 0.59, 0.68]
    for px, pl, pc in zip(pill_xs, pill_labels, pill_colors):
        ax.add_patch(patches.Circle((px, pills_y), 0.030,
                                    facecolor=pc, alpha=0.20,
                                    transform=ax.transAxes, zorder=3))
        ax.text(px, pills_y, pl, color=pc, fontsize=13,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_logo(fig)
    _save(fig, "04_ultimos5.png")


# ─── Card 05 — ANÁLISE xG ────────────────────────────────────────────────────

def card_xg():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "ANÁLISE OFENSIVA E xG  ·  SÉRIE B 2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.880, "AMÉRICA MINEIRO",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.840, "4 jogos — Brasileirão Série B",
           color=GRAY, size=9.5, family=FONT_BODY)

    _hline(ax, 0.815)

    # Três métricas principais (Série B)
    xs = [0.20, 0.50, 0.80]
    metrics_top = [
        ("POSSE MÉDIA",     "67%",  YELLOW, "domina o meio"),
        ("xG / JOGO",       "1.64", RED,    "cria mas não marca"),
        ("CHUTES / JOGO",   "19.3", LGRAY,  "volume alto"),
    ]
    for (lbl, val, color, sub), x in zip(metrics_top, xs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.665), 0.26, 0.130,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=color,
                                    linewidth=1.8, zorder=2))
        ax.text(x, 0.755, val, color=color, fontsize=38,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.687, lbl, color=LGRAY, fontsize=8,
                fontfamily=FONT_BODY, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.667, sub, color=DGRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.648, alpha=0.4)

    # O paradoxo central
    _label(ax, 0.50, 0.617,
           "O PARADOXO: DOMINA A BOLA, NÃO VENCE",
           color=LGRAY, size=12, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.580,
           "67% de posse e 1.64 xG/jogo — mas 0 vitórias e 9 gols sofridos na Série B.\n"
           "Padrão de equipe que cria pela posse mas é vulnerável ao ritmo adversário.",
           color=GRAY, size=9, family=FONT_BODY)

    _hline(ax, 0.538, alpha=0.25)

    # Zonas de ataque — layout: título → percentuais → barras → labels
    zones = [
        ("ESQUERDA",  9.9,  LGRAY),
        ("CENTRO",   79.0,  RED),
        ("DIREITA",  11.0,  LGRAY),
    ]
    bar_xs = [0.18, 0.50, 0.82]
    bar_w  = 0.14

    _label(ax, 0.50, 0.510, "ZONAS DE FINALIZAÇÃO  (16 jogos)",
           color=GRAY, size=8.5, weight="bold", family=FONT_BODY)

    zone_pct_y = 0.475   # linha dos percentuais
    zone_y0    = 0.400   # base das barras
    zone_h     = 0.058

    for (zlbl, zpct, zcolor), bx in zip(zones, bar_xs):
        # Percentual
        ax.text(bx, zone_pct_y, f"{zpct:.0f}%", color=zcolor,
                fontsize=16, fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        # Fundo (vazio)
        ax.add_patch(patches.Rectangle((bx - bar_w / 2, zone_y0), bar_w, zone_h,
                                       facecolor=CARD, edgecolor=DGRAY,
                                       linewidth=0.6, zorder=2))
        # Preenchimento proporcional
        fill_w = bar_w * (zpct / 100.0)
        ax.add_patch(patches.Rectangle((bx - bar_w / 2, zone_y0), fill_w, zone_h,
                                       facecolor=zcolor, alpha=0.75, zorder=3))
        # Label — abaixo das barras
        ax.text(bx, zone_y0 - 0.020, zlbl, color=GRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.358, alpha=0.25)

    # Callout verde — oportunidade para o Sport
    ax.add_patch(FancyBboxPatch((0.07, 0.230), 0.86, 0.110,
                                boxstyle="round,pad=0.01",
                                facecolor="#001a08", edgecolor=GREEN,
                                linewidth=1.5, zorder=3))
    ax.text(0.50, 0.288, "PONTO DE ATENÇÃO PARA O SPORT",
            color=GREEN, fontsize=11.5, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.252,
            "América ataca pelo centro (79%) — bloquear o corredor central é prioridade",
            color=LGRAY, fontsize=8.8, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.232,
            "Alta posse abre espaços para contra-ataques rápidos nas laterais",
            color=GRAY, fontsize=8.2, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax)
    _add_logo(fig)
    _save(fig, "05_xg.png")


# ─── Card 06 — JOGADORES DESTAQUE ────────────────────────────────────────────

def card_jogadores():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "FIQUE DE OLHO  ·  DESTAQUES SÉRIE B",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.875, "AMÉRICA MINEIRO",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _hline(ax, 0.845)

    players = [
        {
            "name1":  "GONZALO",
            "name2":  "MASTRIANI",
            "pos":    "CENTROAVANTE",
            "jersey": "9",
            "rating": "7.22",
            "stats": [
                ("JOGOS",    "4"),
                ("CHUTES",   "8"),
                ("MINUTOS",  "360"),
            ],
            "label":       "PRINCIPAL FINALIZADOR",
            "label_color": RED,
            "border":      RED,
        },
        {
            "name1":  "FELIPE",
            "name2":  "AMARAL",
            "pos":    "MEIA ATACANTE",
            "jersey": "10",
            "rating": "6.93",
            "stats": [
                ("JOGOS",    "4"),
                ("CHUTES",   "8"),
                ("MINUTOS",  "295"),
            ],
            "label":       "CRIAÇÃO PELO CENTRO",
            "label_color": YELLOW,
            "border":      YELLOW,
        },
        {
            "name1":  "GUSTAVO",
            "name2":  "(GOLEIRO)",
            "pos":    "GOLEIRO",
            "jersey": "1",
            "rating": "6.90",
            "stats": [
                ("JOGOS",    "4"),
                ("RATING",   "6.90"),
                ("MINUTOS",  "360"),
            ],
            "label":       "LINHA DE DEFESA",
            "label_color": LGRAY,
            "border":      LGRAY,
        },
    ]

    card_xs  = [0.20, 0.50, 0.80]
    card_w   = 0.270
    card_bot = 0.140
    card_top = 0.800
    card_h   = card_top - card_bot

    for p, cx in zip(players, card_xs):
        x0 = cx - card_w / 2
        x1 = cx + card_w / 2

        ax.add_patch(FancyBboxPatch((x0, card_bot), card_w, card_h,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=p["border"],
                                    linewidth=1.5, zorder=2))
        ax.add_patch(patches.Rectangle((x0 + 0.005, card_top - 0.038),
                                       card_w - 0.010, 0.033,
                                       facecolor=p["border"], alpha=0.18,
                                       zorder=3))

        _badge(ax, cx, card_top - 0.022, f"#{p['jersey']}",
               bg=p["border"], fg=WHITE if p["border"] != YELLOW else "#111111",
               size=9, pad=0.30)

        ax.text(cx, card_top - 0.075, p["name1"], color=WHITE, fontsize=15,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(cx, card_top - 0.108, p["name2"], color=p["border"], fontsize=14,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(cx, card_top - 0.138, p["pos"], color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        sep1 = card_top - 0.156
        ax.plot([x0 + 0.018, x1 - 0.018], [sep1, sep1],
                color=DGRAY, linewidth=0.6, alpha=0.6,
                transform=ax.transAxes, zorder=3)

        r_center = sep1 - 0.040
        ax.add_patch(FancyBboxPatch((cx - 0.085, r_center - 0.022), 0.170, 0.040,
                                    boxstyle="round,pad=0.006",
                                    facecolor="#111111", edgecolor=p["border"],
                                    linewidth=0.8, zorder=3))
        ax.text(cx, r_center, f"RATING  {p['rating']}",
                color=p["border"], fontsize=9, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(cx, r_center - 0.032, "média por jogo (Série B)",
                color=DGRAY, fontsize=6.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

        sep2 = r_center - 0.052
        ax.plot([x0 + 0.018, x1 - 0.018], [sep2, sep2],
                color=DGRAY, linewidth=0.5, alpha=0.5,
                transform=ax.transAxes, zorder=3)

        stat_gap = 0.092
        stat_top = sep2 - 0.020

        for j, (lbl, val) in enumerate(p["stats"]):
            val_y = stat_top - j * stat_gap
            lbl_y = val_y - 0.030
            ax.text(cx, val_y, val, color=WHITE, fontsize=16,
                    fontweight="black", fontfamily=FONT_TITLE,
                    ha="center", va="center", transform=ax.transAxes, zorder=4)
            ax.text(cx, lbl_y, lbl, color=GRAY, fontsize=7,
                    fontfamily=FONT_BODY, ha="center", va="center",
                    transform=ax.transAxes, zorder=4)
            if j < len(p["stats"]) - 1:
                div_y = lbl_y - 0.018
                ax.plot([x0 + 0.018, x1 - 0.018], [div_y, div_y],
                        color=DGRAY, linewidth=0.4, alpha=0.4,
                        transform=ax.transAxes, zorder=3)

        badge_y = card_bot + 0.040
        ax.add_patch(FancyBboxPatch((x0 + 0.015, badge_y - 0.020),
                                    card_w - 0.030, 0.038,
                                    boxstyle="round,pad=0.006",
                                    facecolor="#111111", edgecolor=p["border"],
                                    linewidth=0.8, alpha=0.9, zorder=3))
        ax.text(cx, badge_y, p["label"],
                color=p["label_color"], fontsize=8, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_logo(fig)
    _save(fig, "06_jogadores.png")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    print("Gerando cards — América Mineiro | Série B 2026 R5")
    card_cover()
    card_campanha()
    card_mandante_vis()
    card_ultimos5()
    card_xg()
    card_jogadores()
    print(f"\nPronto. Cards em: {OUT_DIR}")
