"""Generate home attendance evolution card for Sport Recife — Série B 2026."""
from __future__ import annotations

import datetime
import os
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

MATCHES = [
    {"round": 2,  "opponent": "VILA NOVA",         "opponent_id": 2021,   "score": "1 × 1", "publico": 4_576,  "renda": 131_884.0},
    {"round": 4,  "opponent": "AVAÍ",               "opponent_id": 7315,   "score": "2 × 2", "publico": 10_715, "renda": 368_672.0},
    {"round": 6,  "opponent": "NOVORIZONTINO",       "opponent_id": 135514, "score": "1 × 0", "publico": 12_749, "renda": 310_220.0},
    {"round": 7,  "opponent": "CEARÁ",               "opponent_id": 2001,   "score": "2 × 0", "publico": 15_655, "renda": 519_460.0},
]

SPORT_ID = 1959
LOGO_DIR = Path("data/cache/logos")
AVATAR_PATH = Path("sportrecifelab_avatar.png")

BG       = "#0d0d0d"
GOLD     = "#F5C400"
GOLD_DIM = "#7a6200"
WHITE    = "#FFFFFF"
GRAY_LT  = "#b0a880"
GRAY_MD  = "#4a4535"
GRAY_DK  = "#1e1c15"

FONT_HEAVY  = "Franklin Gothic Heavy"
FONT_NORMAL = "Arial"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _remove_bg_floodfill(img: Image.Image, thresh: int = 30) -> Image.Image:
    img = img.convert("RGBA")
    data = np.array(img, dtype=np.uint8)
    h, w = data.shape[:2]
    white_mask = (data[:, :, 0] > 255 - thresh) & (data[:, :, 1] > 255 - thresh) & (data[:, :, 2] > 255 - thresh)
    visited = np.zeros((h, w), dtype=bool)
    alpha = data[:, :, 3].copy()
    from collections import deque
    seeds = []
    for y in range(h):
        for x in [0, w - 1]:
            if white_mask[y, x] and not visited[y, x]:
                seeds.append((y, x))
    for x in range(w):
        for y in [0, h - 1]:
            if white_mask[y, x] and not visited[y, x]:
                seeds.append((y, x))
    q = deque(seeds)
    while q:
        y, x = q.popleft()
        if visited[y, x]:
            continue
        if not white_mask[y, x]:
            continue
        visited[y, x] = True
        alpha[y, x] = 0
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                q.append((ny, nx))
    data[:, :, 3] = alpha
    return Image.fromarray(data)


def _load_logo(team_id: int, size: int = 48) -> np.ndarray | None:
    path = LOGO_DIR / f"{team_id}.png"
    if not path.exists():
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = _remove_bg_floodfill(img)
        img.thumbnail((size, size), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None


def _place_logo(ax, arr: np.ndarray, xy, zoom: float = 1.0, zorder: int = 10):
    im = OffsetImage(arr, zoom=zoom)
    ab = AnnotationBbox(im, xy, frameon=False, zorder=zorder, box_alignment=(0.5, 0.5))
    ax.add_artist(ab)


def _fmt_publico(n: int) -> str:
    return f"{n:,.0f}".replace(",", ".")


def _fmt_renda(r: float) -> str:
    return f"R$ {r:,.0f}".replace(",", ".")

# ---------------------------------------------------------------------------
# Card
# ---------------------------------------------------------------------------

def generate_card(out_path: str = "card_publico_ilha.png"):
    fig_w, fig_h = 10.5, 8.5
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=150)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    max_pub = max(m["publico"] for m in MATCHES)
    total_pub = sum(m["publico"] for m in MATCHES)
    total_renda = sum(m["renda"] for m in MATCHES)

    # --- Layout constants ---
    LEFT_MARGIN = 0.06
    RIGHT_MARGIN = 0.97
    BAR_START = 0.32
    BAR_END = 0.88
    BAR_MAX_W = BAR_END - BAR_START

    HEADER_Y = 0.93
    ROWS_TOP = 0.79
    ROW_H = 0.145
    ROW_GAP = 0.018
    FOOTER_Y = 0.035

    # =========================================================================
    # HEADER
    # =========================================================================
    # Sport logo
    sport_logo = _load_logo(SPORT_ID, size=80)
    if sport_logo is not None:
        _place_logo(ax, sport_logo, (0.085, HEADER_Y - 0.01), zoom=0.62, zorder=12)

    # Title
    ax.text(0.19, HEADER_Y + 0.005, "A ILHA VIBRA",
            fontfamily=FONT_HEAVY, fontsize=26, color=GOLD,
            fontweight="bold", va="top", ha="left", transform=ax.transAxes)
    ax.text(0.19, HEADER_Y - 0.045, "Público Pagante · Mandante · Série B 2026",
            fontfamily=FONT_NORMAL, fontsize=9.5, color=GRAY_LT,
            va="top", ha="left", transform=ax.transAxes, alpha=0.85)

    # Column headers
    header_y = ROWS_TOP + 0.022
    ax.text(LEFT_MARGIN, header_y, "RODADA", fontfamily=FONT_NORMAL, fontsize=7.2,
            color=GRAY_MD, va="bottom", ha="left", transform=ax.transAxes, alpha=0.9)
    ax.text(0.185, header_y, "ADVERSÁRIO", fontfamily=FONT_NORMAL, fontsize=7.2,
            color=GRAY_MD, va="bottom", ha="left", transform=ax.transAxes, alpha=0.9)
    ax.text(BAR_START + 0.01, header_y, "PÚBLICO PAGANTE", fontfamily=FONT_NORMAL,
            fontsize=7.2, color=GRAY_MD, va="bottom", ha="left",
            transform=ax.transAxes, alpha=0.9)
    ax.text(RIGHT_MARGIN, header_y, "RENDA BRUTA", fontfamily=FONT_NORMAL, fontsize=7.2,
            color=GRAY_MD, va="bottom", ha="right", transform=ax.transAxes, alpha=0.9)

    # Header separator
    ax.axhline(ROWS_TOP + 0.012, color=GOLD_DIM, lw=0.6, alpha=0.5,
               xmin=LEFT_MARGIN, xmax=RIGHT_MARGIN)

    # =========================================================================
    # MATCH ROWS
    # =========================================================================
    for i, m in enumerate(MATCHES):
        row_center = ROWS_TOP - i * (ROW_H + ROW_GAP) - ROW_H / 2
        row_top = row_center + ROW_H / 2
        row_bot = row_center - ROW_H / 2

        # Subtle row bg
        row_bg = FancyBboxPatch(
            (LEFT_MARGIN - 0.01, row_bot + 0.005),
            (RIGHT_MARGIN - LEFT_MARGIN + 0.02), ROW_H - 0.01,
            boxstyle="round,pad=0.005",
            facecolor=GRAY_DK, edgecolor="none", alpha=0.45, zorder=1,
            transform=ax.transAxes
        )
        ax.add_patch(row_bg)

        # --- Round badge ---
        badge_x = LEFT_MARGIN + 0.025
        badge_y = row_center + 0.005
        circle = plt.Circle((badge_x, badge_y), 0.028, color=GOLD_DIM, zorder=3,
                             transform=ax.transAxes, clip_on=False)
        ax.add_patch(circle)
        ax.text(badge_x, badge_y + 0.002, f"R{m['round']}",
                fontfamily=FONT_HEAVY, fontsize=8.5, color=GOLD,
                va="center", ha="center", zorder=4, transform=ax.transAxes)

        # --- Score ---
        ax.text(badge_x, badge_y - 0.032, m["score"],
                fontfamily=FONT_HEAVY, fontsize=7.5, color=WHITE,
                va="center", ha="center", zorder=4, transform=ax.transAxes, alpha=0.7)

        # --- Opponent logo + name ---
        opp_logo = _load_logo(m["opponent_id"], size=52)
        logo_x = 0.165
        if opp_logo is not None:
            _place_logo(ax, opp_logo, (logo_x, row_center + 0.006), zoom=0.45, zorder=5)
        # Opponent name
        ax.text(0.205, row_center + 0.018, m["opponent"],
                fontfamily=FONT_HEAVY, fontsize=9.5, color=WHITE,
                va="center", ha="left", zorder=4, transform=ax.transAxes)

        # --- Bar ---
        bar_frac = m["publico"] / max_pub
        bar_w = BAR_MAX_W * bar_frac
        bar_y = row_center - 0.01
        bar_h = 0.042

        # Bar background (track)
        track = FancyBboxPatch(
            (BAR_START, bar_y),
            BAR_MAX_W, bar_h,
            boxstyle="round,pad=0.003",
            facecolor="#1e1c15", edgecolor=GOLD_DIM, linewidth=0.5,
            alpha=0.6, zorder=3, transform=ax.transAxes
        )
        ax.add_patch(track)

        # Gold fill with gradient effect via stacked alpha bars
        n_steps = 40
        for s in range(n_steps):
            frac_s = s / n_steps
            alpha_s = 0.55 + 0.45 * frac_s
            seg_x = BAR_START + bar_w * frac_s / n_steps if bar_w > 0 else BAR_START
            seg_w = bar_w / n_steps if bar_w > 0 else 0
            seg = FancyBboxPatch(
                (BAR_START + bar_w * frac_s, bar_y + 0.003),
                bar_w / n_steps + 0.001, bar_h - 0.006,
                boxstyle="square,pad=0",
                facecolor=GOLD, edgecolor="none",
                alpha=alpha_s, zorder=4, transform=ax.transAxes
            )
            ax.add_patch(seg)

        # Número de público inside/after bar
        num_x = BAR_START + bar_w + 0.012
        if bar_frac > 0.75:
            num_x = BAR_START + bar_w - 0.01
            num_ha = "right"
            num_color = BG
        else:
            num_ha = "left"
            num_color = GOLD

        ax.text(num_x, row_center - 0.01 + bar_h / 2, _fmt_publico(m["publico"]),
                fontfamily=FONT_HEAVY, fontsize=11.5, color=num_color,
                va="center", ha=num_ha, zorder=6, transform=ax.transAxes)

        # --- Renda ---
        ax.text(RIGHT_MARGIN, row_center + 0.012, _fmt_renda(m["renda"]),
                fontfamily=FONT_HEAVY, fontsize=10.5, color=WHITE,
                va="center", ha="right", zorder=4, transform=ax.transAxes)
        ax.text(RIGHT_MARGIN, row_center - 0.02, "renda bruta",
                fontfamily=FONT_NORMAL, fontsize=6.8, color=GRAY_LT,
                va="center", ha="right", zorder=4, transform=ax.transAxes, alpha=0.65)

    # =========================================================================
    # TOTALS / SUMMARY BAND
    # =========================================================================
    summary_y = ROWS_TOP - len(MATCHES) * (ROW_H + ROW_GAP) - 0.01
    ax.axhline(summary_y, color=GOLD_DIM, lw=0.6, alpha=0.5,
               xmin=LEFT_MARGIN, xmax=RIGHT_MARGIN)

    summary_y -= 0.028
    ax.text(LEFT_MARGIN, summary_y, "4 JOGOS",
            fontfamily=FONT_HEAVY, fontsize=9, color=GRAY_LT,
            va="center", ha="left", transform=ax.transAxes, alpha=0.75)

    ax.text(BAR_START, summary_y, "TOTAL  ",
            fontfamily=FONT_NORMAL, fontsize=8, color=GRAY_LT,
            va="center", ha="left", transform=ax.transAxes, alpha=0.7)
    ax.text(BAR_START + 0.065, summary_y, _fmt_publico(total_pub),
            fontfamily=FONT_HEAVY, fontsize=12, color=GOLD,
            va="center", ha="left", transform=ax.transAxes)
    ax.text(BAR_START + 0.065 + 0.09, summary_y, "pagantes",
            fontfamily=FONT_NORMAL, fontsize=8, color=GRAY_LT,
            va="center", ha="left", transform=ax.transAxes, alpha=0.7)

    ax.text(RIGHT_MARGIN, summary_y, _fmt_renda(total_renda),
            fontfamily=FONT_HEAVY, fontsize=12, color=WHITE,
            va="center", ha="right", transform=ax.transAxes)
    ax.text(RIGHT_MARGIN - 0.001, summary_y - 0.028, "renda total",
            fontfamily=FONT_NORMAL, fontsize=6.8, color=GRAY_LT,
            va="center", ha="right", transform=ax.transAxes, alpha=0.65)

    # =========================================================================
    # FOOTER
    # =========================================================================
    ax.axhline(FOOTER_Y + 0.03, color=GOLD_DIM, lw=0.35, alpha=0.3,
               xmin=LEFT_MARGIN, xmax=RIGHT_MARGIN)

    # Avatar
    if AVATAR_PATH.exists():
        try:
            avatar = Image.open(AVATAR_PATH).convert("RGBA")
            avatar.thumbnail((48, 48), Image.LANCZOS)
            avatar_arr = np.array(avatar)
            _place_logo(ax, avatar_arr, (0.09, FOOTER_Y + 0.01), zoom=0.55, zorder=10)
        except Exception:
            pass

    ax.text(0.155, FOOTER_Y + 0.015, "@SportRecifeLab",
            fontfamily=FONT_HEAVY, fontsize=8.5, color=GOLD,
            va="center", ha="left", transform=ax.transAxes, alpha=0.85)
    ax.text(0.155, FOOTER_Y - 0.007, "Dados: CBF · Boletim Financeiro",
            fontfamily=FONT_NORMAL, fontsize=6.8, color=GRAY_LT,
            va="center", ha="left", transform=ax.transAxes, alpha=0.55)

    now_str = datetime.datetime.utcnow().strftime("%d/%m/%Y")
    ax.text(RIGHT_MARGIN, FOOTER_Y + 0.005, f"Série B 2026  ·  R{MATCHES[-1]['round']}",
            fontfamily=FONT_NORMAL, fontsize=7.5, color=GRAY_LT,
            va="center", ha="right", transform=ax.transAxes, alpha=0.5)

    # =========================================================================
    # SAVE
    # =========================================================================
    plt.tight_layout(pad=0)
    fig.savefig(out_path, dpi=150, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    print(f"Card saved: {out_path}")


if __name__ == "__main__":
    generate_card()
