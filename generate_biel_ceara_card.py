"""
Card de análise individual — Biel Fonseca vs Ceará
Série B 2026 | Rodada 7 — @SportRecifeLab
Mobile-first: 1080×1350px
"""

import json
import os
import datetime
from pathlib import Path
from collections import deque

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, Circle
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import matplotlib.patheffects as pe
import numpy as np
from scipy.ndimage import gaussian_filter

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from mplsoccer import VerticalPitch
    HAS_MPLSOCCER = True
except ImportError:
    HAS_MPLSOCCER = False


# ── Constantes visuais ────────────────────────────────────────────────────────
BG       = "#0d0d0d"
GOLD     = "#F5C400"
GOLD_DIM = "#C49A00"
WHITE    = "#FFFFFF"
GRAY1    = "#1a1a1a"
GRAY2    = "#2a2a2a"
GRAY3    = "#888888"
RED_ACC  = "#E63946"
FIELD_DK = "#0e3d1f"
FIELD_LT = "#2a7a3a"

DPI    = 150
W_PX   = 1080
H_PX   = 1350
W_IN   = W_PX / DPI
H_IN   = H_PX / DPI


# ── Dados do jogador ──────────────────────────────────────────────────────────
PLAYER = {
    "name": "BIEL",
    "full": "Biel Fonseca",
    "position": "MEIA",
    "jersey": "6",
    "match": "Sport Recife 1×0 Ceará",
    "competition": "Série B 2026 · Rodada 7",
    "rating": 7.2,
    "minutes": 83,
}

STATS = [
    # (label, value, unit, highlight)
    ("PRECISÃO DE PASSE",  "92%",  "24/26 passes certos",   True),
    ("TOQUES",             "42",   "no jogo",               False),
    ("RECUPERAÇÕES",       "4",    "de bola",               True),
    ("CORTES",             "5",    "defensivos",            False),
    ("DUELOS VENCIDOS",    "4",    "",                      False),
    ("CHUTES",             "1",    "",                      False),
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def _remove_bg_floodfill(img, thresh=25):
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


def _load_logo(path, size=None, remove_bg=True):
    if not HAS_PIL or not os.path.exists(path):
        return None
    img = Image.open(path).convert("RGBA")
    if remove_bg:
        img = _remove_bg_floodfill(img)
    if size:
        img = img.resize(size, Image.LANCZOS)
    return np.array(img)


def _place_image(ax, arr, xy, zoom=1.0, zorder=10):
    if arr is None:
        return
    oi = OffsetImage(arr, zoom=zoom)
    ab = AnnotationBbox(oi, xy, frameon=False, zorder=zorder,
                        box_alignment=(0.5, 0.5))
    ax.add_artist(ab)


def _star_rating(rating, ax, x, y, n=10, r=0.004, gap=0.007):
    """Desenha dots preenchidos/vazios representando o rating."""
    filled = round(rating)
    for i in range(n):
        cx = x + i * gap
        color = GOLD if i < filled else GRAY2
        circle = Circle((cx, y), r, color=color, transform=ax.transAxes,
                         zorder=12, clip_on=False)
        ax.add_patch(circle)


# ── Heatmap ───────────────────────────────────────────────────────────────────
def _draw_heatmap(ax, pts):
    """Renderiza heatmap KDE num campo vertical mplsoccer."""
    if not HAS_MPLSOCCER:
        ax.set_facecolor(FIELD_DK)
        ax.text(0.5, 0.5, "mplsoccer\nnão instalado",
                ha="center", va="center", color=GRAY3, fontsize=8,
                transform=ax.transAxes)
        return

    pitch = VerticalPitch(
        pitch_type="custom",
        pitch_length=100, pitch_width=100,
        pitch_color=FIELD_DK,
        line_color="#FFFFFF55",
        linewidth=0.9,
        goal_type="box",
        goal_alpha=0.7,
        pad_top=2, pad_bottom=2, pad_left=2, pad_right=2,
    )
    pitch.draw(ax=ax)

    # SofaScore: x=0 gol próprio→100 gol adversário; y=0 faixa direita→100 faixa esquerda
    # VerticalPitch: x=0 faixa esquerda→100 faixa direita; y=0 gol próprio→100 gol adversário
    x_pitch = np.array([p["y"] for p in pts], dtype=float)
    y_pitch = np.array([p["x"] for p in pts], dtype=float)

    # KDE com bandwidth adaptativo por ponto
    # Primeiro calcula densidade local p/ cada ponto (k-nearest neighbors proxy)
    from scipy.spatial.distance import cdist

    pts_arr = np.stack([x_pitch, y_pitch], axis=1)
    dists = cdist(pts_arr, pts_arr)
    np.fill_diagonal(dists, np.inf)
    k = 5
    knn_dist = np.sort(dists, axis=1)[:, :k].mean(axis=1)  # distância média k-NN

    # Bandwidth individual: ponto em cluster denso → sigma menor (mais preciso)
    # Ponto isolado → sigma menor que antes (não infla área vazia)
    bw_min, bw_max = 4.0, 7.0
    bw_norm = (knn_dist - knn_dist.min()) / (knn_dist.max() - knn_dist.min() + 1e-9)
    bandwidths = bw_min + bw_norm * (bw_max - bw_min)

    grid_size = 300
    xi = np.linspace(0, 100, grid_size)
    yi = np.linspace(0, 100, grid_size)
    XX, YY = np.meshgrid(xi, yi)
    Z = np.zeros_like(XX)
    for px, py, bw in zip(x_pitch, y_pitch, bandwidths):
        Z += np.exp(-((XX - px) ** 2 + (YY - py) ** 2) / (2 * bw ** 2))

    # Suavização mínima — preserva a forma dos clusters
    Z = gaussian_filter(Z, sigma=1.2)
    Z = Z / Z.max()

    # Threshold elevado: só exibe zonas com ≥35% do pico
    # Força ilhas separadas ao invés de mancha contínua
    Z[Z < 0.35] = 0.0

    from matplotlib.colors import LinearSegmentedColormap
    # Gradiente: transparente → vermelho-laranja → laranja → amarelo ouro
    # Mostra campo verde nas áreas vazias, intensidade cresce com calor
    cmap = LinearSegmentedColormap.from_list(
        "biel_heat",
        [
            (0.00, (0.0, 0.0, 0.0, 0.0)),        # transparente
            (0.01, (0.0, 0.0, 0.0, 0.0)),        # transparente (abaixo do threshold)
            (0.25, (0.80, 0.20, 0.02, 0.50)),    # laranja-avermelhado, semi-trans
            (0.55, (0.95, 0.55, 0.05, 0.72)),    # laranja-âmbar
            (0.80, (0.98, 0.78, 0.10, 0.88)),    # amarelo-ouro
            (1.00, (0.96, 0.77, 0.00, 0.96)),    # ouro vivo (#F5C400)
        ],
    )
    ax.contourf(xi, yi, Z, levels=30, cmap=cmap, zorder=4)

    # Scatter: só pontos que caem em zonas quentes
    density_at_pt = np.array([
        Z[int(py / 100 * (grid_size - 1)), int(px / 100 * (grid_size - 1))]
        for px, py in zip(x_pitch, y_pitch)
    ])
    mask_hot = density_at_pt > 0
    ax.scatter(x_pitch[mask_hot], y_pitch[mask_hot],
               s=8, color=GOLD, alpha=0.40, zorder=5, linewidths=0)

    # Centroide ponderado pelos pontos em zonas quentes
    if mask_hot.sum() > 0:
        cx = x_pitch[mask_hot].mean()
        cy = y_pitch[mask_hot].mean()
    else:
        cx, cy = x_pitch.mean(), y_pitch.mean()
    ax.scatter([cx], [cy], s=100, color=GOLD, zorder=9, linewidths=0, alpha=0.95)
    ax.scatter([cx], [cy], s=280, facecolors="none", edgecolors=GOLD,
               linewidths=1.8, zorder=9, alpha=0.55)


# ── Layout principal ──────────────────────────────────────────────────────────
def generate_card(out_path="biel_fonseca_ceara.png"):
    # Carregar logos
    sport_logo = _load_logo("data/cache/logos/1959.png", size=(140, 140))
    ceara_logo = _load_logo("data/cache/logos/2001.png", size=(100, 100))
    lab_logo   = _load_logo("sportrecifelab_avatar.png", size=(80, 80), remove_bg=False)

    # Heatmap data
    with open("data/raw/sofascore/heatmaps/player_1383112_match_15526072.json") as f:
        hm_data = json.load(f)
    pts = hm_data.get("heatmap", [])

    # ── Figura ─────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(W_IN, H_IN), dpi=DPI, facecolor=BG)

    # Grid: header | heatmap | stats | footer
    # alturas em proporção (total = 1)
    gs = fig.add_gridspec(
        4, 1,
        top=0.97, bottom=0.03, left=0.05, right=0.95,
        hspace=0.03,
        height_ratios=[0.20, 0.38, 0.35, 0.07],
    )

    ax_header = fig.add_subplot(gs[0])
    ax_pitch  = fig.add_subplot(gs[1])
    ax_stats  = fig.add_subplot(gs[2])
    ax_footer = fig.add_subplot(gs[3])

    for ax in [ax_header, ax_stats, ax_footer]:
        ax.set_facecolor(BG)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

    ax_pitch.set_facecolor(FIELD_DK)

    # ── HEADER ────────────────────────────────────────────────────────────────
    # Linha superior fina dourada
    ax_header.axhline(0.97, color=GOLD, linewidth=1.2, alpha=0.6)

    # Escudo Sport (esquerda)
    _place_image(ax_header, sport_logo, (0.10, 0.52), zoom=0.50)

    # Nome do jogador (centro)
    ax_header.text(0.50, 0.78, PLAYER["name"],
                   ha="center", va="center",
                   fontsize=34, fontweight="black",
                   color=WHITE, fontfamily="sans-serif",
                   transform=ax_header.transAxes,
                   path_effects=[pe.withStroke(linewidth=3, foreground=BG)])

    ax_header.text(0.50, 0.57, PLAYER["full"].upper(),
                   ha="center", va="center",
                   fontsize=9, color=GRAY3, fontfamily="sans-serif",
                   fontweight="bold",
                   transform=ax_header.transAxes)

    # Posição + camisa
    pos_box_w, pos_box_h = 0.13, 0.26
    pos_rect = FancyBboxPatch(
        (0.435, 0.23), pos_box_w, pos_box_h,
        boxstyle="round,pad=0.01",
        linewidth=1, edgecolor=GOLD, facecolor=GOLD + "22",
        transform=ax_header.transAxes, zorder=3,
    )
    ax_header.add_patch(pos_rect)
    ax_header.text(0.50, 0.38, f"#{PLAYER['jersey']} · {PLAYER['position']}",
                   ha="center", va="center",
                   fontsize=9, color=GOLD, fontfamily="sans-serif",
                   fontweight="bold", transform=ax_header.transAxes)

    # Jogo e competição (centro-baixo) — só até o início do rating box
    ax_header.text(0.50, 0.10, f"{PLAYER['match']}  ·  {PLAYER['competition']}",
                   ha="center", va="center",
                   fontsize=7.5, color=GRAY3, fontfamily="sans-serif",
                   transform=ax_header.transAxes, clip_on=True)

    # Rating box (direita) — colado ao escudo do Ceará
    rating_x = 0.72
    rating_bg = FancyBboxPatch(
        (rating_x - 0.055, 0.38), 0.11, 0.42,
        boxstyle="round,pad=0.01",
        linewidth=2, edgecolor=GOLD, facecolor=GOLD,
        transform=ax_header.transAxes, zorder=3,
    )
    ax_header.add_patch(rating_bg)
    ax_header.text(rating_x, 0.63, f"{PLAYER['rating']:.1f}",
                   ha="center", va="center",
                   fontsize=20, fontweight="black",
                   color=BG, fontfamily="sans-serif",
                   transform=ax_header.transAxes, zorder=4)
    ax_header.text(rating_x, 0.28, "RATING",
                   ha="center", va="center",
                   fontsize=7, color=GRAY3, fontfamily="sans-serif",
                   fontweight="bold", transform=ax_header.transAxes)

    # Minutos (acima do rating box)
    ax_header.text(rating_x, 0.88, f"{PLAYER['minutes']}'",
                   ha="center", va="center",
                   fontsize=8, color=GRAY3, fontweight="bold",
                   fontfamily="sans-serif",
                   transform=ax_header.transAxes)

    # Escudo Ceará (direita)
    _place_image(ax_header, ceara_logo, (0.90, 0.52), zoom=0.42)

    # Linha "vs" entre escudos
    ax_header.text(0.50, 0.52, "×",
                   ha="center", va="center",
                   fontsize=12, color=GRAY3,
                   transform=ax_header.transAxes)

    # ── PITCH / HEATMAP ───────────────────────────────────────────────────────
    _draw_heatmap(ax_pitch, pts)

    # Label flutuante sobre o campo
    ax_pitch.text(0.5, 0.985, "MAPA DE MOVIMENTAÇÃO",
                  ha="center", va="top",
                  fontsize=8, color=GOLD + "CC",
                  fontfamily="sans-serif", fontweight="bold",
                  transform=ax_pitch.transAxes, zorder=20)

    # Separador
    ax_pitch.axhline(y=0, color=GOLD + "33", linewidth=0.5)

    # ── STATS ─────────────────────────────────────────────────────────────────
    # Título da seção
    ax_stats.text(0.5, 0.965, "DESEMPENHO NA PARTIDA",
                  ha="center", va="top",
                  fontsize=9, color=GOLD, fontfamily="sans-serif",
                  fontweight="bold", alpha=0.8,
                  transform=ax_stats.transAxes)

    # Grid de stats: 2 colunas × 3 linhas
    cols = 2
    rows = 3
    cell_w = 1.0 / cols
    cell_h = 0.85 / rows
    top_start = 0.91

    for i, (label, value, subtext, highlight) in enumerate(STATS):
        col = i % cols
        row = i // cols
        cx = col * cell_w + cell_w / 2
        cy = top_start - row * cell_h - cell_h / 2

        # Caixa de fundo
        pad_x, pad_y = 0.02, 0.01
        rect_x = col * cell_w + pad_x
        rect_y = top_start - (row + 1) * cell_h + pad_y
        rect_w = cell_w - 2 * pad_x
        rect_h = cell_h - 2 * pad_y

        box_color = GOLD + "15" if highlight else GRAY1
        edge_color = GOLD + "88" if highlight else GRAY2
        edge_lw = 1.2 if highlight else 0.5

        stat_box = FancyBboxPatch(
            (rect_x, rect_y), rect_w, rect_h,
            boxstyle="round,pad=0.005",
            linewidth=edge_lw,
            edgecolor=edge_color,
            facecolor=box_color,
            transform=ax_stats.transAxes,
            zorder=3,
        )
        ax_stats.add_patch(stat_box)

        # Linha dourada superior se destaque
        if highlight:
            ax_stats.axhline(
                y=rect_y + rect_h, xmin=rect_x, xmax=rect_x + rect_w,
                color=GOLD, linewidth=1.5, alpha=0.7, zorder=4,
            )

        # Valor principal
        val_color = GOLD if highlight else WHITE
        ax_stats.text(cx, cy + 0.045, value,
                      ha="center", va="center",
                      fontsize=26, fontweight="black",
                      color=val_color, fontfamily="sans-serif",
                      transform=ax_stats.transAxes, zorder=5)

        # Label
        ax_stats.text(cx, cy - 0.01, label,
                      ha="center", va="center",
                      fontsize=7.5, fontweight="bold",
                      color=GRAY3, fontfamily="sans-serif",
                      transform=ax_stats.transAxes, zorder=5)

        # Subtexto
        if subtext:
            ax_stats.text(cx, cy - 0.062, subtext,
                          ha="center", va="center",
                          fontsize=7, color=GRAY3 + "99",
                          fontfamily="sans-serif",
                          transform=ax_stats.transAxes, zorder=5)

    # ── FOOTER ────────────────────────────────────────────────────────────────
    ax_footer.axhline(0.88, color=GOLD + "44", linewidth=0.8)

    _place_image(ax_footer, lab_logo, (0.06, 0.36), zoom=0.28, zorder=10)

    ax_footer.text(0.15, 0.46, "@SportRecifeLab",
                   ha="left", va="center",
                   fontsize=9, fontweight="bold",
                   color=GOLD, fontfamily="sans-serif",
                   transform=ax_footer.transAxes)

    ax_footer.text(0.15, 0.14, "Dados: SofaScore",
                   ha="left", va="center",
                   fontsize=7, color=GRAY3,
                   fontfamily="sans-serif",
                   transform=ax_footer.transAxes)

    ax_footer.text(0.98, 0.30,
                   f"Série B 2026 · R7 · {datetime.date.today().strftime('%d/%m/%Y')}",
                   ha="right", va="center",
                   fontsize=7, color=GRAY3,
                   fontfamily="sans-serif",
                   transform=ax_footer.transAxes)

    # ── Salvar ─────────────────────────────────────────────────────────────────
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=DPI, bbox_inches="tight", facecolor=BG, pil_kwargs={"optimize": True})
    plt.close(fig)
    print(f"Card salvo: {out}  ({out.stat().st_size // 1024} KB)")
    return str(out)


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "biel_fonseca_ceara.png"
    generate_card(out)
