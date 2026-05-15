# -*- coding: utf-8 -*-
"""Card: Análise Defensiva Sport Recife — Série B 2026 (R1-R8)
Otimizado para visualização mobile no X."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import os

# ── Data ──────────────────────────────────────────────────────────────────────
rounds    = [1,     2,     3,     4,     5,     6,     7,     8]
opponents = ["Cuiabá","Vila Nova","Londrina","Avaí",
             "América MG","Novorizontino","Ceará","Ponte Preta"]
locations = ["F","C","F","C","F","C","C","F"]
xg_ced    = [1.32, 1.64, 0.85, 1.79, 1.26, 0.65, 0.53, 2.15]
goals_ag  = [0,    1,    1,    2,    0,    0,    0,    1]

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0d0d0d"
GOLD    = "#F5C400"
RED     = "#E63946"
GREEN   = "#2DC653"
ORANGE  = "#FF8C00"
GRAY    = "#3A3A3A"
GRAY_MD = "#666666"
GRAY_LT = "#9A9A9A"
WHITE   = "#F5F5F5"
PANEL   = "#181818"

# ── Canvas: 1080×1350 px @100dpi ─────────────────────────────────────────────
W, H = 10.80, 13.50
fig = plt.figure(figsize=(W, H), facecolor=BG)
ax  = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

def box(x, y, w, h, fc, alpha=1.0, r=0.10, lw=0, ec="none", zorder=3):
    p = FancyBboxPatch((x, y), w, h,
                       boxstyle=f"round,pad=0,rounding_size={r}",
                       linewidth=lw, edgecolor=ec,
                       facecolor=fc, alpha=alpha, zorder=zorder)
    ax.add_patch(p)

def t(x, y, s, sz, col, fn="Franklin Gothic Heavy",
      ha="center", va="center", zorder=5, alpha=1.0):
    ax.text(x, y, s, fontsize=sz, color=col, fontname=fn,
            ha=ha, va=va, zorder=zorder, alpha=alpha)

def hline(y, x0=0.50, x1=None, col=GRAY, lw=0.4, alpha=0.5, zorder=4):
    if x1 is None: x1 = W - 0.50
    ax.plot([x0, x1], [y, y], color=col, lw=lw, alpha=alpha, zorder=zorder)

# ═════════════════════════════════════════════════════════════════════════════
# 1. HEADER (12.30 → 13.50) — 1.20 high
# ═════════════════════════════════════════════════════════════════════════════
box(0, 12.30, W, 1.20, GOLD, r=0)
t(W/2, 12.96, "ANÁLISE DEFENSIVA", 36, BG)
t(W/2, 12.50, "SPORT  ·  SÉRIE B 2026  ·  8 RODADAS", 13, BG,
  fn="Franklin Gothic Medium")

# ═════════════════════════════════════════════════════════════════════════════
# 2. HERO STAT (10.55 → 12.10) — 1.55 high
# ═════════════════════════════════════════════════════════════════════════════
HERO_TOP    = 12.10
HERO_BOTTOM = 10.55
box(0.50, HERO_BOTTOM, W-1.00, HERO_TOP-HERO_BOTTOM, PANEL, r=0.18)
ax.plot([0.50, W-0.50], [HERO_TOP, HERO_TOP],
        color=GOLD, lw=3.5, zorder=4)

# Left half — hero number
t(2.80, 11.55, "+5.19", 62, GREEN)
t(2.80, 10.92, "GOLS SALVOS", 12, WHITE)
t(2.80, 10.70, "ACIMA DO ESPERADO (xG)", 9.5, GRAY_LT,
  fn="Franklin Gothic Medium")

# Divider
ax.plot([5.30, 5.30], [10.70, 11.95], color=GRAY, lw=1.2, zorder=4)

# Right column — supporting numbers
t(7.10, 11.75, "5",    36, RED,     ha="center")
t(7.85, 11.62, "GOLS", 11, WHITE,   ha="left")
t(7.85, 11.42, "sofridos", 9.5, GRAY_LT, fn="Franklin Gothic Medium", ha="left")

t(7.10, 11.05, "10.2", 28, GOLD, ha="center")
t(7.85, 11.05, "xG", 11, WHITE, ha="left")
t(7.85, 10.85, "cedido", 9.5, GRAY_LT, fn="Franklin Gothic Medium", ha="left")

t(7.10, 10.65, "49%", 18, GRAY_LT, ha="center")
t(7.85, 10.65, "conversão adversária", 9.5, GRAY_LT,
  fn="Franklin Gothic Medium", ha="left")

# ═════════════════════════════════════════════════════════════════════════════
# 3. TABLE (3.70 → 10.30)
# ═════════════════════════════════════════════════════════════════════════════
TITLE_Y       = 10.20
HEADER_Y      = 9.84
TABLE_TOP_Y   = 9.66    # top of first row's panel
ROW_H         = 0.72
N_ROWS        = 8

# Section title (above headers)
t(0.55, TITLE_Y, "xG CEDIDO  vs  GOLS SOFRIDOS", 14, GOLD, ha="left")
t(W-0.55, TITLE_Y, "POR RODADA", 10, GRAY_LT,
  fn="Franklin Gothic Medium", ha="right")
hline(TITLE_Y - 0.16, col=GOLD, lw=0.4, alpha=0.4)

# Column positions
cx_rnd = 0.85
cx_opp = 1.55
cx_xg  = 4.45
bar_x0 = 4.95
bar_x1 = 9.25
cx_ga  = 9.95

# Column headers (between title rule and first row)
t(cx_rnd-0.05, HEADER_Y, "R",          8, GRAY_LT, fn="Franklin Gothic Medium")
t(cx_opp,      HEADER_Y, "TIME",       8, GRAY_LT, fn="Franklin Gothic Medium", ha="left")
t(cx_xg,       HEADER_Y, "xG",         8, GRAY_LT, fn="Franklin Gothic Medium")
t((bar_x0+bar_x1)/2, HEADER_Y, "xG vs GOLS", 8, GRAY_LT, fn="Franklin Gothic Medium")
t(cx_ga,       HEADER_Y, "GOLS",       8, GRAY_LT, fn="Franklin Gothic Medium")
hline(HEADER_Y - 0.15, lw=0.25, alpha=0.35)

# Rows
MAX_XG = max(xg_ced)
BAR_W  = bar_x1 - bar_x0

for i, (rnd, opp, loc, xg, ga) in enumerate(
        zip(rounds, opponents, locations, xg_ced, goals_ag)):
    panel_top    = TABLE_TOP_Y - i * ROW_H
    panel_bottom = panel_top - ROW_H + 0.06
    mid          = (panel_top + panel_bottom) / 2

    # Alternating tint
    if i % 2 == 0:
        box(0.50, panel_bottom, W-1.00, panel_top - panel_bottom,
            PANEL, r=0.06, alpha=0.50)

    # Worst-match accent (R4 Avaí: gols > xG)
    if rnd == 4:
        box(0.50, panel_bottom, W-1.00, panel_top - panel_bottom,
            RED, r=0.06, alpha=0.06)
        ax.plot([0.50, 0.50], [panel_bottom, panel_top],
                color=RED, lw=3.5, zorder=5)

    # Round number
    t(cx_rnd, mid, str(rnd), 19, GOLD)

    # Opponent + location
    opp_d = opp if len(opp) <= 13 else opp[:13]+"."
    t(cx_opp, mid+0.10, opp_d, 13, WHITE, ha="left")
    loc_col = GOLD if loc == "C" else GRAY_LT
    loc_lbl = "CASA" if loc == "C" else "FORA"
    t(cx_opp, mid-0.18, loc_lbl, 8.5, loc_col,
      fn="Franklin Gothic Medium", ha="left")

    # xG value
    xg_col = RED if xg >= 1.5 else (GOLD if xg >= 1.0 else GREEN)
    t(cx_xg, mid, f"{xg:.2f}", 14, xg_col)

    # Bars
    xg_bw = (xg / MAX_XG) * BAR_W
    bar_h = 0.32
    bar_y = mid - bar_h/2

    box(bar_x0, bar_y, BAR_W, bar_h, GRAY, r=0.05, alpha=0.22, zorder=3)
    box(bar_x0, bar_y, xg_bw, bar_h, GRAY_MD, r=0.05, alpha=0.88, zorder=4)
    if ga > 0:
        ga_bw = (ga / MAX_XG) * BAR_W
        g_col = RED if ga >= 2 else ORANGE
        box(bar_x0, bar_y, ga_bw, bar_h, g_col, r=0.05, alpha=0.97, zorder=5)

    # Goals conceded
    ga_col = GREEN if ga == 0 else (RED if ga >= 2 else ORANGE)
    t(cx_ga, mid, str(ga), 23, ga_col)

TABLE_BOTTOM_Y = TABLE_TOP_Y - N_ROWS * ROW_H + 0.06

# Legend chips
LG_Y = TABLE_BOTTOM_Y - 0.18
box(0.55, LG_Y-0.13, 0.45, 0.26, GRAY_MD, r=0.05, alpha=0.88)
t(1.13, LG_Y, "xG cedido", 9, GRAY_LT,
  fn="Franklin Gothic Medium", ha="left")
box(3.10, LG_Y-0.13, 0.45, 0.26, ORANGE, r=0.05, alpha=0.97)
t(3.68, LG_Y, "1 gol sofrido", 9, GRAY_LT,
  fn="Franklin Gothic Medium", ha="left")
box(5.85, LG_Y-0.13, 0.45, 0.26, RED, r=0.05, alpha=0.97)
t(6.43, LG_Y, "2 gols sofridos", 9, GRAY_LT,
  fn="Franklin Gothic Medium", ha="left")

# ═════════════════════════════════════════════════════════════════════════════
# 4. GAME STATE (0.85 → 3.30)
# ═════════════════════════════════════════════════════════════════════════════
GS_DIV_Y    = LG_Y - 0.45
GS_TITLE_Y  = GS_DIV_Y - 0.30
hline(GS_DIV_Y, col=GOLD, lw=0.7, alpha=0.4)

t(0.55, GS_TITLE_Y, "EM QUE SITUAÇÃO SOFREU OS GOLS", 14, GOLD, ha="left")

# Donut
PIE_CX = 2.40
PIE_CY = 1.75
PIE_R  = 0.98
PIE_W  = 0.40

w_neu = patches.Wedge((PIE_CX, PIE_CY), PIE_R,
                       90 - 4/5*360, 90,
                       width=PIE_W, facecolor=GOLD, alpha=0.95, zorder=4)
w_win = patches.Wedge((PIE_CX, PIE_CY), PIE_R,
                       90 - 360, 90 - 4/5*360,
                       width=PIE_W, facecolor=RED, alpha=0.92, zorder=4)
ax.add_patch(w_neu); ax.add_patch(w_win)

circ = plt.Circle((PIE_CX, PIE_CY), PIE_R - PIE_W - 0.08,
                   fc=BG, ec=GRAY, lw=1.0, zorder=5)
ax.add_patch(circ)
t(PIE_CX, PIE_CY + 0.18, "5", 36, WHITE)
t(PIE_CX, PIE_CY - 0.18, "GOLS",     10, GRAY_LT, fn="Franklin Gothic Medium")
t(PIE_CX, PIE_CY - 0.38, "SOFRIDOS",  8, GRAY_LT, fn="Franklin Gothic Medium")

# Right side: 3 states
ST_X = 4.40
states = [
    (GOLD,  "EMPATANDO", "4 de 5 gols (0-0)", "80%", 2.65),
    (RED,   "VENCENDO",  "1 de 5 gols",       "20%", 1.75),
    (GREEN, "PERDENDO",  "nunca aconteceu",   "0%",  0.85),
]
for col, lbl, sub, pct, py in states:
    box(ST_X, py-0.22, 0.20, 0.44, col, r=0.04, alpha=0.95)
    t(ST_X + 0.40, py + 0.12, lbl, 15, WHITE, ha="left")
    t(ST_X + 0.40, py - 0.22, sub, 10, GRAY_LT,
      fn="Franklin Gothic Medium", ha="left")
    t(W - 0.65, py, pct, 24, col, ha="right")

# ═════════════════════════════════════════════════════════════════════════════
# 5. FOOTER (0 → 0.65)
# ═════════════════════════════════════════════════════════════════════════════
hline(0.65, x0=0, x1=W, col=GOLD, lw=0.6, alpha=0.55)

logo_path = "sportrecifelab_avatar.png"
if os.path.exists(logo_path):
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    from matplotlib.image import imread
    oi = OffsetImage(imread(logo_path), zoom=0.13)
    ab = AnnotationBbox(oi, (0.80, 0.32), frameon=False, zorder=6)
    ax.add_artist(ab)

t(1.42, 0.32, "@SportRecifeLab", 12, GOLD, ha="left")
t(W - 0.50, 0.32, "Dados: SofaScore  ·  R1–R8", 9.5, GRAY_LT,
  fn="Franklin Gothic Medium", ha="right")

# ── Save ──────────────────────────────────────────────────────────────────────
out = "defesa_card.png"
fig.savefig(out, dpi=100, bbox_inches="tight",
            facecolor=BG, edgecolor="none")
plt.close(fig)
print(f"Saved: {out}")

# Diagnostics
print(f"Table top:    {TABLE_TOP_Y:.2f}")
print(f"Table bottom: {TABLE_BOTTOM_Y:.2f}")
print(f"Legend Y:     {LG_Y:.2f}")
print(f"GS title Y:   {GS_TITLE_Y:.2f}")
print(f"Pie bottom:   {PIE_CY-PIE_R:.2f}")
print(f"Pie top:      {PIE_CY+PIE_R:.2f}")
print(f"Footer top:   0.65")
