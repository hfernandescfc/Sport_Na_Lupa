"""
Gera os cards visuais da thread "Raio-X: Vila Nova FC"
Série B 2026 | Rodada 2 — @SportRecifeLab

Cards produzidos:
  01_cover.png          — abertura da thread
  02_campanha.png       — temporada 2026 (campanha geral)
  03_mandante_vis.png   — mandante vs visitante
  04_ultimos5.png       — últimos 5 jogos
  05_xg.png             — análise xG e perfil ofensivo
  06_jogadores.png      — destaque individual

Saída: pending_posts/2026-04-01_raio-x-vila-nova/
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

import urllib.request
from collections import deque


def _remove_bg_floodfill(img: "Image.Image", thresh: int = 25) -> "Image.Image":
    """Remove o fundo branco de uma imagem via BFS a partir das bordas.

    Apenas pixels brancos conectados à borda da imagem são tornados
    transparentes — o conteúdo branco interno (texto, estrelas) é preservado.
    """
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]

    # Máscara: pixels considerados "brancos" (fundo candidato)
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    is_white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)

    # BFS iniciando em todos os pixels brancos da borda
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
        data[y, x, 3] = 0           # torna transparente
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True
                queue.append((ny, nx))

    return Image.fromarray(data, "RGBA")


def _download_vila_nova_logo(dest="vila_nova_logo.png"):
    """Tenta baixar o escudo do Vila Nova via SofaScore CDN."""
    if os.path.exists(dest):
        return dest
    url = "https://api.sofascore.app/api/v1/team/2021/image"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(dest, "wb") as f:
            f.write(data)
        return dest
    except Exception:
        return None

# ─── Paleta @SportRecifeLab ──────────────────────────────────────────────────
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
GREEN2  = "#1e6b33"

# ─── Layout ──────────────────────────────────────────────────────────────────
FIG_W, FIG_H = 9.0, 9.0   # polegadas — 1080×1080 @ 120 dpi
DPI = 120
OUT_DIR = "pending_posts/2026-04-01_raio-x-vila-nova"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"


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
    return {
        "win":  GREEN,
        "draw": YELLOW,
        "loss": RED,
    }.get(outcome, GRAY)


def _result_label(outcome):
    return {"win": "V", "draw": "E", "loss": "D"}.get(outcome, "?")


# ─── Card 01 — COVER ─────────────────────────────────────────────────────────

def _draw_shield_placeholder(ax, cx, cy, r=0.130):
    """Escudo geométrico simples nas cores do Vila Nova (vermelho/preto) como fallback."""
    shield = plt.Polygon([
        [cx,       cy + r],
        [cx + r,   cy + r * 0.55],
        [cx + r,   cy - r * 0.25],
        [cx,       cy - r],
        [cx - r,   cy - r * 0.25],
        [cx - r,   cy + r * 0.55],
    ], closed=True, facecolor="#8B0000", edgecolor=LGRAY,
       linewidth=1.5, alpha=0.85, zorder=3, transform=ax.transAxes)
    ax.add_patch(shield)
    ax.text(cx, cy + 0.010, "VN", color=WHITE, fontsize=32,
            fontweight="black", fontfamily=FONT_TITLE,
            ha="center", va="center", transform=ax.transAxes, zorder=4)
    ax.text(cx, cy - 0.058, "VILA NOVA", color=LGRAY, fontsize=7.5,
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=4)


def card_cover():
    fig, ax = _new_fig()

    # Faixa diagonal decorativa (amarela)
    poly = plt.Polygon([[0, 0.58], [0, 0.68], [0.45, 0.68], [0.55, 0.58]],
                       closed=True, facecolor=YELLOW, alpha=0.06, zorder=1)
    ax.add_patch(poly)

    # Borda superior amarela fina
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))

    # Label superior
    _label(ax, 0.50, 0.950, "SÉRIE B 2026  ·  RODADA 2",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    # Título RAIO-X
    ax.text(0.50, 0.840, "RAIO-X",
            color=YELLOW, fontsize=96, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4,
            path_effects=[pe.withStroke(linewidth=4, foreground="#0d0d0d")])

    # Subtítulo VILA NOVA FC
    ax.text(0.50, 0.728, "VILA NOVA FC",
            color=WHITE, fontsize=44, fontweight="bold",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4)

    _hline(ax, 0.690, alpha=0.55)

    # Contexto do confronto
    _label(ax, 0.50, 0.648, "SPORT JOGA COMO VISITANTE",
           color=LGRAY, size=12.5, weight="bold", family=FONT_TITLE)

    # --- Escudo do Vila Nova (lado esquerdo) ---
    logo_path = _download_vila_nova_logo()
    shield_cx, shield_cy = 0.195, 0.340

    if logo_path and HAS_PIL:
        try:
            img = Image.open(logo_path).convert("RGBA")
            img = _remove_bg_floodfill(img, thresh=25)
            img = img.resize((220, 220), Image.LANCZOS)
            arr = np.array(img)
            logo_ax = fig.add_axes([0.04, 0.17, 0.28, 0.28])
            logo_ax.imshow(arr)
            logo_ax.set_facecolor(BG)
            logo_ax.axis("off")
        except Exception:
            _draw_shield_placeholder(ax, shield_cx, shield_cy)
    else:
        _draw_shield_placeholder(ax, shield_cx, shield_cy)

    # --- Stats (lado direito) ---
    stats = [
        ("10V  3E  5D", "CAMPANHA 2026",   YELLOW),
        ("+15",          "SALDO DE GOLS",   GREEN),
        ("61%",          "APROVEITAMENTO",  LGRAY),
        ("0.99",         "xG / JOGO",       RED),
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

    _label(ax, 0.50, 0.870, "VILA NOVA FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.828, "18 PARTIDAS DISPUTADAS",
           color=GRAY, size=10, family=FONT_BODY)

    _hline(ax, 0.805)

    # Vitórias / Empates / Derrotas
    results = [
        (10, "VITÓRIAS",  GREEN,  "10V"),
        (3,  "EMPATES",   YELLOW, "3E"),
        (5,  "DERROTAS",  RED,    "5D"),
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
    pts = 10 * 3 + 3
    aprov = pts / (18 * 3) * 100
    _label(ax, 0.50, 0.558, f"{pts} pontos  ·  {aprov:.0f}% de aproveitamento",
           color=LGRAY, size=10.5, weight="bold", family=FONT_BODY)

    _hline(ax, 0.535, alpha=0.25)

    # Gols
    gol_data = [
        ("GOLS\nMARCADOS", "42", YELLOW),
        ("SALDO\nDE GOLS",  "+15", GREEN),
        ("GOLS\nSOFRIDOS",  "27",  RED),
    ]
    gxs = [0.20, 0.50, 0.80]
    for (lbl, val, color), x in zip(gol_data, gxs):
        ax.text(x, 0.465, val, color=color, fontsize=40,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.398, lbl, color=GRAY, fontsize=8.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4, linespacing=1.4)

    _hline(ax, 0.365, alpha=0.25)

    # Competições
    comps = [
        ("Goiano 1ª Div.", "12 jogos"),
        ("Copa do Brasil", "3 jogos"),
        ("Copa Verde",     "2 jogos"),
        ("Série B",        "1 jogo"),
    ]
    cx = [0.16, 0.39, 0.62, 0.84]
    for (comp, n), x in zip(comps, cx):
        ax.text(x, 0.330, n, color=YELLOW, fontsize=14,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.293, comp, color=GRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_logo(fig)
    _save(fig, "02_campanha.png")


# ─── Card 03 — MANDANTE (Sport joga em Goiânia) ──────────────────────────────

def card_mandante_vis():
    """Apenas dados de mandante — contexto do confronto: Sport vai a Goiânia."""
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "VILA NOVA COMO MANDANTE  ·  2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.876, "VILA NOVA FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.836, "Sport joga em Goiânia — como o Tigre se sai em casa?",
           color=GRAY, size=9.5, family=FONT_BODY)

    _hline(ax, 0.812)

    cx = 0.50

    # Aproveitamento grande
    ax.text(cx, 0.738, "60%", color=GREEN, fontsize=80,
            fontweight="black", fontfamily=FONT_TITLE,
            ha="center", va="center", transform=ax.transAxes, zorder=4)
    _label(ax, cx, 0.683, "APROVEITAMENTO COMO MANDANTE  ·  10 JOGOS",
           color=GRAY, size=9, family=FONT_BODY)

    _hline(ax, 0.660, alpha=0.4)

    # V/E/D — horizontal com espaçamento amplo
    ved = [("5", "VITÓRIAS", GREEN), ("3", "EMPATES", YELLOW), ("2", "DERROTAS", RED)]
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

    # Gols marcados / sofridos / média
    gol_cols = [
        ("30",  "GOLS MARCADOS",  YELLOW),
        ("19",  "GOLS SOFRIDOS",  RED),
        ("+11", "SALDO",          GREEN),
    ]
    for (val, lbl, color), x in zip(gol_cols, vxs):
        ax.text(x, 0.508, val, color=color, fontsize=36,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.468, lbl, color=GRAY, fontsize=8.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.446, alpha=0.3)

    # Médias por jogo
    med_cols = [
        ("3.0", "GOLS MARC/JOGO"),
        ("1.9", "GOLS SOF/JOGO"),
        ("53%", "POSSE MÉDIA"),
    ]
    for (val, lbl), x in zip(med_cols, vxs):
        ax.text(x, 0.408, val, color=LGRAY, fontsize=24,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.374, lbl, color=GRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.350, alpha=0.3)

    # xG e stats defensivos
    xg_cols = [
        ("1.63", "xG MÉDIO / JOGO",        YELLOW),
        ("1.26", "xG SOFRIDO / JOGO",      RED),
        ("54%",  "PRECISÃO DE CHUTES",     LGRAY),
    ]
    for (val, lbl, color), x in zip(xg_cols, vxs):
        ax.text(x, 0.310, val, color=color, fontsize=24,
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
    ax.text(cx, 0.200, "Forte em casa, mas não invencivel — 2 derrotas em 10 jogos",
            color=LGRAY, fontsize=9.5, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(cx, 0.168, "Jogo aberto: media de 4.9 gols por partida em Goiania",
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

    _label(ax, 0.50, 0.875, "VILA NOVA FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _hline(ax, 0.845)

    games = [
        {
            "date":   "28/03",
            "comp":   "Copa Verde",
            "home":   "Vila Nova FC",
            "hs":     6,
            "away":   "Operário-MS",
            "as_":    0,
            "is_home": True,
            "outcome": "win",
        },
        {
            "date":   "24/03",
            "comp":   "Copa Verde",
            "home":   "Rio Branco-ES",
            "hs":     1,
            "away":   "Vila Nova FC",
            "as_":    0,
            "is_home": False,
            "outcome": "loss",
        },
        {
            "date":   "21/03",
            "comp":   "Série B R1",
            "home":   "Vila Nova FC",
            "hs":     2,
            "away":   "CRB",
            "as_":    2,
            "is_home": True,
            "outcome": "draw",
        },
        {
            "date":   "18/03",
            "comp":   "Copa do Brasil",
            "home":   "Vila Nova FC",
            "hs":     3,
            "away":   "Confiança",
            "as_":    5,
            "is_home": True,
            "outcome": "loss",
        },
        {
            "date":   "12/03",
            "comp":   "Copa do Brasil",
            "home":   "Vila Nova FC",
            "hs":     6,
            "away":   "Operário-MS",
            "as_":    5,
            "is_home": True,
            "outcome": "win",
        },
    ]

    # row_h > box_h para evitar sobreposição das caixas
    row_h  = 0.130   # espaçamento entre centros das linhas
    box_h  = 0.108   # altura real da caixa
    half_h = box_h / 2  # 0.054
    y_start = 0.806

    for i, g in enumerate(games):
        y = y_start - i * row_h          # centro vertical desta linha
        y_bot = y - half_h               # topo inferior da caixa
        outcome_color = _result_color(g["outcome"])
        outcome_label = _result_label(g["outcome"])

        # Fundo da linha alternado
        row_bg = CARD if i % 2 == 0 else CARD2
        ax.add_patch(FancyBboxPatch((0.07, y_bot), 0.86, box_h,
                                    boxstyle="round,pad=0.005",
                                    facecolor=row_bg, edgecolor="none",
                                    zorder=2))

        # Borda lateral colorida (resultado)
        ax.add_patch(patches.Rectangle((0.07, y_bot), 0.012, box_h,
                                       facecolor=outcome_color, zorder=3))

        # Badge resultado (alinhado ao centro vertical da caixa)
        _badge(ax, 0.906, y, outcome_label, bg=outcome_color,
               fg=("#111111" if g["outcome"] == "draw" else WHITE),
               size=11, pad=0.38)

        # Data (linha superior dentro da caixa)
        date_y = y + half_h * 0.38
        comp_y = y - half_h * 0.40

        ax.text(0.118, date_y, g["date"], color=LGRAY, fontsize=9,
                fontweight="bold", fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.118, comp_y, g["comp"], color=DGRAY, fontsize=7,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        # Placar — Vila Nova destacado em amarelo
        vn_color = YELLOW
        opp_color = LGRAY
        if g["is_home"]:
            h_color, a_color = vn_color, opp_color
            h_weight, a_weight = "black", "normal"
        else:
            h_color, a_color = opp_color, vn_color
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

    # Sumário forma — posicionado claramente abaixo do último row
    last_row_bot = y_start - 4 * row_h - half_h   # fundo da última linha
    hline_y = last_row_bot - 0.030
    pills_y  = hline_y - 0.048
    label_y  = hline_y - 0.018

    _hline(ax, hline_y, alpha=0.3)
    _label(ax, 0.50, label_y, "FORMA NOS ÚLTIMOS 5:",
           color=GRAY, size=9, family=FONT_BODY)

    pill_colors = [GREEN, RED, YELLOW, RED, GREEN]
    pill_labels = ["V", "D", "E", "D", "V"]
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
    _label(ax, 0.50, 0.950, "ANÁLISE OFENSIVA E xG  ·  2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.880, "VILA NOVA FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.840, "18 jogos — todas as competições",
           color=GRAY, size=9.5, family=FONT_BODY)

    _hline(ax, 0.815)

    # Três métricas principais
    metrics_top = [
        ("POSSE MÉDIA",    "53%",   YELLOW, "controla o jogo"),
        ("xG / JOGO",      "0.99",  RED,    "baixa conversão"),
        ("PRECISÃO CHUTES","54%",   LGRAY,  "na direção certa"),
    ]
    xs = [0.20, 0.50, 0.80]
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

    # Barra de contexto: posse vs xG gerado
    _label(ax, 0.50, 0.617,
           "DOMINA A BOLA, MAS CRIA POUCO",
           color=LGRAY, size=12, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.583,
           "Maior posse não se converte em superioridade de xG — padrão de equipe que circula\n"
           "sem criar oportunidades claras de gol. Na Série B (1 jogo): apenas 0.47 xG.",
           color=GRAY, size=9, family=FONT_BODY)

    _hline(ax, 0.540, alpha=0.25)

    # xG sofrido — contexto defensivo
    _label(ax, 0.50, 0.508, "CONTEXTO DEFENSIVO",
           color=GRAY, size=8.5, weight="bold", family=FONT_BODY)

    def_data = [
        ("xG SOFRIDO / JOGO",    "1.26", RED),
        ("CHUTES SOFRIDOS / JOGO", "10.2", RED),
        ("POSSE CEDIDA / JOGO",   "46.6%", LGRAY),
    ]
    def_xs = [0.22, 0.50, 0.78]
    for (lbl, val, color), x in zip(def_data, def_xs):
        ax.text(x, 0.462, val, color=color, fontsize=24,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.427, lbl, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.400, alpha=0.25)

    # Callout de oportunidade para o Sport
    ax.add_patch(FancyBboxPatch((0.07, 0.285), 0.86, 0.103,
                                boxstyle="round,pad=0.01",
                                facecolor="#001a08", edgecolor=GREEN,
                                linewidth=1.5, zorder=3))
    ax.text(0.50, 0.340, "PONTO DE ATENÇÃO PARA O SPORT",
            color=GREEN, fontsize=11.5, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.298,
            "Pressão alta pode forçar erros: Vila Nova cede 1.26 xG/jogo e 46.6% de posse ao adversário",
            color=LGRAY, fontsize=8.8, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax)
    _add_logo(fig)
    _save(fig, "05_xg.png")


# ─── Card 06 — JOGADORES DESTAQUE ────────────────────────────────────────────

def card_jogadores():
    fig, ax = _new_fig()

    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "FIQUE DE OLHO  ·  DESTAQUES 2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    _label(ax, 0.50, 0.875, "VILA NOVA FC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    _hline(ax, 0.845)

    players = [
        {
            "name1": "JOÃO",
            "name2": "VIEIRA",
            "pos":   "MEIA CENTRAL",
            "jersey": "5",
            "rating": "7.80",
            "stats": [
                ("JOGOS",         "13"),
                ("ASSISTÊNCIAS",  "6"),
                ("PASSES CERTOS", "37/jogo"),
            ],
            "label": "MOTOR CRIATIVO",
            "label_color": YELLOW,
            "border": YELLOW,
        },
        {
            "name1": "DELLA-",
            "name2": "TORRE",
            "pos":   "CENTROAVANTE",
            "jersey": "49",
            "rating": "7.08",
            "stats": [
                ("JOGOS",    "14"),
                ("CHUTES",   "21"),
                ("MINUTOS",  "1247"),
            ],
            "label": "PRINCIPAL FINALIZADOR",
            "label_color": RED,
            "border": RED,
        },
        {
            "name1": "ANDRÉ",
            "name2": "LUÍS",
            "pos":   "PONTA DIREITA",
            "jersey": "7",
            "rating": "7.08",
            "stats": [
                ("JOGOS",         "13"),
                ("ASSISTÊNCIAS",  "3"),
                ("MINUTOS",       "1081"),
            ],
            "label": "PERIGO PELAS LATERAIS",
            "label_color": LGRAY,
            "border": LGRAY,
        },
    ]

    card_xs = [0.20, 0.50, 0.80]
    card_w  = 0.270
    card_bot = 0.140   # fundo dos cards
    card_top = 0.800   # topo dos cards
    card_h  = card_top - card_bot  # 0.660

    for p, cx in zip(players, card_xs):
        x0 = cx - card_w / 2
        x1 = cx + card_w / 2

        # Card background
        ax.add_patch(FancyBboxPatch((x0, card_bot), card_w, card_h,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=p["border"],
                                    linewidth=1.5, zorder=2))

        # Faixa colorida no topo do card (dentro dos limites)
        ax.add_patch(patches.Rectangle((x0 + 0.005, card_top - 0.038),
                                       card_w - 0.010, 0.033,
                                       facecolor=p["border"], alpha=0.18,
                                       zorder=3))

        # Número da camisa — pill dentro da faixa do topo
        _badge(ax, cx, card_top - 0.022, f"#{p['jersey']}",
               bg=p["border"], fg=WHITE if p["border"] != YELLOW else "#111111",
               size=9, pad=0.30)

        # ── Nome (dois blocos, dentro do card) ───────────────────────────────
        ax.text(cx, card_top - 0.075, p["name1"], color=WHITE, fontsize=15,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(cx, card_top - 0.108, p["name2"], color=p["border"], fontsize=15,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

        # Posição
        ax.text(cx, card_top - 0.138, p["pos"], color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        # Separador
        sep1 = card_top - 0.156
        ax.plot([x0 + 0.018, x1 - 0.018], [sep1, sep1],
                color=DGRAY, linewidth=0.6, alpha=0.6,
                transform=ax.transAxes, zorder=3)

        # ── Rating ───────────────────────────────────────────────────────────
        r_center = sep1 - 0.040
        ax.add_patch(FancyBboxPatch((cx - 0.085, r_center - 0.022), 0.170, 0.040,
                                    boxstyle="round,pad=0.006",
                                    facecolor="#111111", edgecolor=p["border"],
                                    linewidth=0.8, zorder=3))
        ax.text(cx, r_center, f"RATING  {p['rating']}",
                color=p["border"], fontsize=9, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        ax.text(cx, r_center - 0.032, "media por jogo",
                color=DGRAY, fontsize=6.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

        # Separador
        sep2 = r_center - 0.052
        ax.plot([x0 + 0.018, x1 - 0.018], [sep2, sep2],
                color=DGRAY, linewidth=0.5, alpha=0.5,
                transform=ax.transAxes, zorder=3)

        # ── Stats individuais (3 itens com espaçamento uniforme) ─────────────
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

        # ── Badge de papel/função — centralizado com folga acima do rodapé ───
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
    print("Gerando cards - Vila Nova FC | Serie B 2026 R2")
    card_cover()
    card_campanha()
    card_mandante_vis()
    card_ultimos5()
    card_xg()
    card_jogadores()
    print("\nPronto. Cards em:", OUT_DIR)
