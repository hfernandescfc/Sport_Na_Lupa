"""Generate visual card: Sport no 1º Terço — Top 5 Série B 2026."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from PIL import Image

# ── Palette ───────────────────────────────────────────────────────────────────
BG        = "#0D0D0D"
PANEL     = "#1A1A1A"
RED       = "#D00000"
RED_LIGHT = "#FF4444"
GOLD      = "#F5A623"
GREEN     = "#27AE60"
WHITE     = "#F0F0F0"
GRAY      = "#777777"
DARK_RED  = "#2A0000"
ROW_ALT   = "#141414"

FONT = "Franklin Gothic Medium"

# ── Logo map: team_key → sofascore_team_id ────────────────────────────────────
LOGO_DIR  = "data/cache/logos"
LOGO_IDS  = {
    "fortaleza": 2020,
    "sport":     1959,
    "goias":     1960,
    "ceara":     2001,
    "juventude": 1980,
}

def load_logo(team_key: str, size: int = 52) -> np.ndarray | None:
    path = f"{LOGO_DIR}/{LOGO_IDS[team_key]}.png"
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((size, size), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None

# ── Data (from real pipeline, strength-ranked) ────────────────────────────────
teams      = ["Fortaleza", "Sport",  "Goiás",  "Ceará",   "Juventude"]
team_keys  = ["fortaleza", "sport",  "goias",  "ceara",   "juventude"]
lb_acc     = [57.7,  44.0,  39.7,  46.7,  55.4]  # bola longa acc GK+D %
gk_vol     = [7.8,   10.8,  21.2,  12.2,  13.0]  # GK longo /jogo
# Índice de Retenção: média de (passes/posse%) e (proporção/posse%) normalizados 0-100
# 0 = mais progressivo, 100 = mais retentivo no campo próprio
ret_idx    = [62,    85,    0,     68,    42]     # combined retention index
own_acc    = [92.5,  92.1,  91.3,  88.7,  92.4]  # precisão próprio campo %
prog       = [200,   258,   204,   176,   254]    # progressão defensores m/jogo

SPORT_IDX = 1

# ── Figure ────────────────────────────────────────────────────────────────────
W, H = 15, 12
fig = plt.figure(figsize=(W, H), facecolor=BG)
fig.patch.set_facecolor(BG)
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")
ax.set_facecolor(BG)


def txt(x, y, s, **kw):
    kw.setdefault("color", WHITE)
    kw.setdefault("fontfamily", FONT)
    kw.setdefault("va", "center")
    kw.setdefault("ha", "left")
    ax.text(x, y, s, **kw)


def rect(x, y, w, h, color, alpha=1.0, radius=0.0):
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        linewidth=0, facecolor=color, alpha=alpha, zorder=1,
    )
    ax.add_patch(box)


def add_logo(team_key: str, cx: float, cy: float, size: int = 52):
    arr = load_logo(team_key, size)
    if arr is None:
        return
    img_box = OffsetImage(arr, zoom=1.0)
    ab = AnnotationBbox(img_box, (cx, cy), frameon=False, zorder=3)
    ax.add_artist(ab)


# ── Layout constants ──────────────────────────────────────────────────────────
LOGO_COL_W = 1.10   # width reserved for logo
NAME_COL_W = 1.55   # width for team name text
LEFT_PAD   = 0.20
DATA_X0    = LEFT_PAD + LOGO_COL_W + NAME_COL_W  # x where data columns start
DATA_W     = W - DATA_X0 - 0.20
COL_W      = DATA_W / 5
COL_CX     = [DATA_X0 + COL_W * i + COL_W / 2 for i in range(5)]

# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
HEADER_BOT = H - 1.55
rect(0, HEADER_BOT, W, 1.55, RED)
rect(0, HEADER_BOT, 0.45, 1.55, "#8B0000")
txt(W / 2, HEADER_BOT + 1.05, "SPORT NO 1º TERÇO",
    fontsize=32, fontweight="bold", ha="center")
txt(W / 2, HEADER_BOT + 0.42,
    "Dado ou Exagero?   |   Top 5 Série B 2026   |   Rodadas 1–4",
    fontsize=13, ha="center", color="#FFD0D0")

# ─────────────────────────────────────────────────────────────────────────────
# GROUP HEADERS
# ─────────────────────────────────────────────────────────────────────────────
GH_BOT = HEADER_BOT - 0.46
GH_H   = 0.36

groups = [
    (0, 2, "#3D0000", "#FF8888", "SAÍDA PELO ALTO"),
    (2, 4, "#0A1A0A", "#88CC88", "NO PRÓPRIO CAMPO"),
    (4, 5, "#0A0A1A", "#8888CC", "PROGRESSÃO"),
]
for c0, c1, bg, fg, label in groups:
    gx = COL_CX[c0] - COL_W / 2 + 0.05
    gw = COL_CX[c1 - 1] + COL_W / 2 - gx - 0.05
    rect(gx, GH_BOT, gw, GH_H, bg, radius=0.10)
    mid = (COL_CX[c0] + COL_CX[c1 - 1]) / 2
    txt(mid, GH_BOT + GH_H / 2, label,
        fontsize=9, fontweight="bold", ha="center", color=fg)

# ─────────────────────────────────────────────────────────────────────────────
# COLUMN HEADERS
# ─────────────────────────────────────────────────────────────────────────────
CH_BOT = GH_BOT - 0.74
CH_H   = 0.72
rect(0, CH_BOT, W, CH_H, DARK_RED)

txt(LEFT_PAD + LOGO_COL_W + 0.10, CH_BOT + CH_H / 2, "Clube",
    fontsize=10, fontweight="bold", color=GOLD)

col_labels = [
    "Bola Longa\n(Def+GK) %",
    "GK Longo\n/jogo",
    "Índice Retenção\nCampo Próprio*",
    "Precisão Campo\nPróprio %",
    "Progressão\nDef (m/jogo)",
]
for cx, label in zip(COL_CX, col_labels):
    ax.text(cx, CH_BOT + CH_H / 2, label,
            color=GOLD, fontfamily=FONT, fontsize=9.5, fontweight="bold",
            ha="center", va="center", linespacing=1.3)

# ─────────────────────────────────────────────────────────────────────────────
# DATA ROWS
# ─────────────────────────────────────────────────────────────────────────────
ROW_H  = 0.88
ROW_Y0 = CH_BOT - ROW_H

# (series, higher_is_better)
metrics = [
    (lb_acc,  True),   # bola longa acc — higher = better
    (gk_vol,  False),  # GK volume — lower = better
    (ret_idx, False),  # retenção — lower = better (more progressive)
    (own_acc, True),   # precisão próprio campo — higher = better
    (prog,    True),   # progressão — higher = better
]
fmts = ["{:.1f}%", "{:.1f}", "{:.0f}", "{:.1f}%", "{:.0f}m"]


def metric_color(val, series, higher_better, base):
    best  = max(series) if higher_better else min(series)
    worst = min(series) if higher_better else max(series)
    if val == best:  return GREEN
    if val == worst: return RED_LIGHT
    return base


def metric_tag(val, series, higher_better):
    best  = max(series) if higher_better else min(series)
    worst = min(series) if higher_better else max(series)
    if val == best:  return " [+]"
    if val == worst: return " [-]"
    return ""


row_vals = list(zip(teams, team_keys, lb_acc, gk_vol, ret_idx, own_acc, prog))

for i, (team, tkey, lb, gk, ridx, oacc, pr) in enumerate(row_vals):
    y = ROW_Y0 - i * ROW_H
    is_sport = (i == SPORT_IDX)

    bg = "#1E0000" if is_sport else (PANEL if i % 2 == 0 else ROW_ALT)
    rect(0, y, W, ROW_H, bg)
    if is_sport:
        rect(0, y, 0.14, ROW_H, RED)

    base  = "#FFE0E0" if is_sport else WHITE
    ncol  = RED_LIGHT if is_sport else WHITE
    fw    = "bold" if is_sport else "normal"
    fs    = 12 if is_sport else 11.5
    cy    = y + ROW_H / 2

    # Logo
    logo_cx = LEFT_PAD + LOGO_COL_W / 2
    add_logo(tkey, logo_cx, cy, size=50)

    # Team name
    txt(LEFT_PAD + LOGO_COL_W + 0.12, cy, team,
        color=ncol, fontsize=fs, fontweight=fw)

    # Data columns
    vals = [lb, gk, ridx, oacc, pr]
    for cx, val, (series, hb), fmt in zip(COL_CX, vals, metrics, fmts):
        color = metric_color(val, series, hb, base)
        tag   = metric_tag(val, series, hb)
        ax.text(cx, cy, fmt.format(val) + tag,
                color=color, fontfamily=FONT,
                fontsize=fs, fontweight=fw if is_sport else "normal",
                ha="center", va="center")

# separator below last row
sep_y = ROW_Y0 - len(teams) * ROW_H
ax.axhline(sep_y, xmin=0, xmax=1, color="#3A0000", linewidth=1.5, zorder=2)

# ─────────────────────────────────────────────────────────────────────────────
# INSIGHT BOXES
# ─────────────────────────────────────────────────────────────────────────────
BOX_TOP = sep_y - 0.18
BOX_H   = 0.82
BOX_GAP = 0.22
BOX_W   = (W - 4 * BOX_GAP) / 3

insights = [
    (RED_LIGHT, "ATENÇÃO",
     "Thiago Couto: 10,8 lançamentos/jogo — 34,9% de precisão\nMaior volume do Top 5 (Fortaleza referência: 7,8/jogo)"),
    (GOLD, "CONTEXTO",
     "Mesmo com posse semelhante ao Fortaleza, o Sport\nprende mais o jogo na zona recuada (índice 85 vs 62)"),
    (GREEN, "PONTO FORTE",
     "Quando sai jogando, avança mais: 258m/jogo de progressão\npelos defensores — melhor do Top 5"),
]

for idx, (color, title, body) in enumerate(insights):
    bx = BOX_GAP + idx * (BOX_W + BOX_GAP)
    by = BOX_TOP - BOX_H
    rect(bx, by, BOX_W, BOX_H, PANEL, radius=0.15)
    rect(bx, by, 0.12, BOX_H, color)
    ax.text(bx + 0.24, by + BOX_H - 0.22, title,
            color=color, fontfamily=FONT, fontsize=10, fontweight="bold",
            ha="left", va="center")
    ax.text(bx + 0.24, by + 0.28, body,
            color=WHITE, fontfamily=FONT, fontsize=9,
            ha="left", va="center", linespacing=1.5)

# ─────────────────────────────────────────────────────────────────────────────
# CONCLUSION
# ─────────────────────────────────────────────────────────────────────────────
concl_y = BOX_TOP - BOX_H - 0.20
rect(0.35, concl_y - 0.42, W - 0.70, 0.58, "#1A0000", radius=0.18)
ax.text(W / 2, concl_y - 0.13,
        '"O problema não é o jogo combinado — é a saída pelo alto."',
        color=GOLD, fontfamily=FONT, fontsize=12, fontweight="bold",
        ha="center", va="center", style="italic")

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
ax.text(W / 2, 0.42,
        "Dados: Sofascore  |  Série B 2026  |  Força = valor de mercado (70%) + pontos/jogo (30%)",
        color=GRAY, fontfamily=FONT, fontsize=8.5, ha="center", va="center")
ax.text(W / 2, 0.16,
        "* Índice de Retenção: 0 = mais progressivo  |  100 = mais retentivo no campo próprio  |  normalizado pela posse média",
        color=GRAY, fontfamily=FONT, fontsize=8, ha="center", va="center")

# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────
out = "sport_primeiro_terco_card.png"
fig.savefig(out, dpi=180, bbox_inches="tight", facecolor=BG, pad_inches=0.05)
plt.close(fig)
print(f"Card saved: {out}")
