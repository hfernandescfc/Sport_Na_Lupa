"""
Gera o card "Como o [TIME] Joga" v2 — @SportRecifeLab
Tactical Cartography: três painéis lendo esquerda→direita como inteligência tática.

Layout:
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │  COMO O  [TEAM NAME]  JOGA           Série B · R7 · 03/05 · N partidas     │
  ├───────────────────────┬──────────────────────┬──────────────────────────────┤
  │  MAPA DE ATUAÇÃO      │  SHOTMAP xG           │  ESTILO DE JOGO (3 bullets) │
  │  [heatmap 5×3 zonas]  │  [half-pitch, bolhas  │  ────────────────────────── │
  │                       │   tamanho∝xG,         │  MÉTRICAS                   │
  │                       │   cor=intensidade]    │  Posse / xG                 │
  │                       │  [xG/zona: box,fora]  │  Entradas3º / Bolas Longas  │
  ├───────────────────────┴──────────────────────┴──────────────────────────────┤
  │  // Síntese: insight principal do estilo de jogo                            │
  └─────────────────────────────────────────────────────────────────────────────┘

Fontes:
  data/processed/{season}/opponents/{team_key}/team_heatmap.json
  data/curated/opponents_{season}/{team_key}/attack_profile.json
"""
from __future__ import annotations

import argparse
import json
import os
from collections import deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe
import numpy as np

try:
    from mplsoccer import Pitch, VerticalPitch
    HAS_MPLSOCCER = True
except ImportError:
    HAS_MPLSOCCER = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── Paleta ───────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
CARD   = "#141414"
CARD2  = "#1a1a1a"
CARD3  = "#222222"
CARD4  = "#111820"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
LGRAY  = "#B0B0B0"
GRAY   = "#666666"
DGRAY  = "#333333"
GREEN  = "#2ECC71"
RED    = "#E74C3C"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

FIG_W, FIG_H = 14.0, 7.5
DPI = 130

LOGO_SRL  = "sportrecifelab_avatar.png"
LOGOS_DIR = Path("data/cache/logos")

# Grid heatmap 5×3
N_DEPTH = 5
N_LAT   = 3
DEPTH_LABELS = ["3º DEF", "2º DEF", "MEIO", "2º ATQ", "3º ATQ"]
LAT_LABELS   = ["ESQ", "CENTRO", "DIR"]

# Refs Série B 2026
SERIE_B_AVG = {
    "possession":          50.0,
    "expected_goals":       1.10,
    "final_third_entries": 20.0,
    "long_balls_pct":       7.5,
    "touches_opp_box":     18.0,
    "shots_outside_box":    4.8,
}

PATTERN_ICONS = ["\u25cf", "\u2666", "\u25b2"]


# ─── Logo helpers ─────────────────────────────────────────────────────────────

def _remove_bg(img: "Image.Image", thresh: int = 25) -> "Image.Image":
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)
    vis = np.zeros((h, w), bool)
    q: deque = deque()
    for y in range(h):
        for x in (0, w - 1):
            if white[y, x] and not vis[y, x]:
                vis[y, x] = True; q.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if white[y, x] and not vis[y, x]:
                vis[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft(); data[y, x, 3] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not vis[ny, nx] and white[ny, nx]:
                vis[ny, nx] = True; q.append((ny, nx))
    return Image.fromarray(data, "RGBA")


def _load_logo(path: Path, size: int, remove_bg: bool = False) -> "np.ndarray | None":
    if not HAS_PIL or not path.exists():
        return None
    try:
        img = Image.open(path).convert("RGBA")
        if remove_bg:
            img = _remove_bg(img)
        return np.array(img.resize((size, size), Image.LANCZOS))
    except Exception:
        return None


# ─── Análise heatmap ─────────────────────────────────────────────────────────

def _compute_zones(points: list[dict]) -> dict:
    valid = [p for p in points if p.get("x") is not None and p.get("y") is not None]
    total = len(valid)
    if not total:
        return {"grid_pcts": [[0.0] * N_LAT] * N_DEPTH,
                "lat_pcts": [0.0] * N_LAT, "dep_pcts": [0.0] * N_DEPTH, "total": 0}
    grid = [[0] * N_LAT for _ in range(N_DEPTH)]
    for p in valid:
        px, py = float(p["x"]), float(p["y"])
        grid[min(int(py / 20), N_DEPTH - 1)][0 if px < 33.33 else (1 if px < 66.67 else 2)] += 1
    gp = [[round(grid[d][l] / total * 100, 1) for l in range(N_LAT)] for d in range(N_DEPTH)]
    lp = [round(sum(grid[d][l] for d in range(N_DEPTH)) / total * 100, 1) for l in range(N_LAT)]
    dp = [round(sum(grid[d][l] for l in range(N_LAT)) / total * 100, 1) for d in range(N_DEPTH)]
    return {"grid_pcts": gp, "lat_pcts": lp, "dep_pcts": dp, "total": total}


# ─── Análise shotmap ──────────────────────────────────────────────────────────

def _compute_shot_zones(shots: list[dict]) -> dict:
    """Split shots into box-center, box-sides, outside-box zones with xG totals."""
    zones = {
        "box_center": {"shots": 0, "xg": 0.0},
        "box_sides":  {"shots": 0, "xg": 0.0},
        "outside":    {"shots": 0, "xg": 0.0},
    }
    for s in shots:
        px = float(s.get("player_x") or 0)
        py = float(s.get("player_y") or 50)
        xg = float(s.get("xg") or 0)
        # player_x: 0=goal line, increases toward midfield
        # player_y: 0=left flank, 100=right flank
        in_box = px <= 20 and 22 <= py <= 78  # roughly 18-yard box
        if in_box:
            if 35 <= py <= 65:
                zones["box_center"]["shots"] += 1
                zones["box_center"]["xg"]    += xg
            else:
                zones["box_sides"]["shots"] += 1
                zones["box_sides"]["xg"]    += xg
        else:
            zones["outside"]["shots"] += 1
            zones["outside"]["xg"]    += xg
    return zones


def _shot_to_statsbomb(px: float, py: float) -> tuple[float, float]:
    """Map SofaScore shot coords to StatsBomb attacking half (x 60-120, y 0-80)."""
    sb_x = max(60.0, 120.0 - px * 1.20)
    sb_y = py * 0.80
    return sb_x, sb_y


# ─── Síntese ─────────────────────────────────────────────────────────────────

def _build_resumo(profile: dict, zones: dict) -> str:
    avg = profile.get("averages", {})
    pos     = avg.get("possession", 50)
    sib_pct = avg.get("shots_inside_box_pct", 50)
    fte     = avg.get("final_third_entries", 20)
    dep     = zones.get("dep_pcts", [0] * 5)
    off_pct = dep[3] + dep[4]
    lat     = zones.get("lat_pcts", [34, 33, 33])
    dom     = max(range(3), key=lambda i: lat[i])

    style  = "Equipe reativa" if pos < 46 else ("Equipe com posse" if pos > 54 else "Equipe equilibrada")
    corr   = f"forte pelo corredor {'esquerdo' if dom == 0 else 'central' if dom == 1 else 'direito'}"
    detail = ""
    if sib_pct < 52:
        detail = "com frequência de chutes de fora da área"
    elif fte < 15:
        detail = "e baixo volume no terço final"
    elif off_pct > 38:
        detail = "com pressão alta"

    parts = [style, corr]
    if detail:
        parts.append(detail)
    return ", ".join(parts) + "."


def _parse_pattern(pat: str) -> tuple[str, str]:
    if " — " in pat:
        bold, _, rest = pat.partition(" — ")
        return bold.strip(), rest.strip()
    if " (" in pat:
        bold, _, rest = pat.partition(" (")
        return bold.strip(), "(" + rest.strip()
    words = pat.split()
    pivot = min(4, len(words))
    return " ".join(words[:pivot]), " ".join(words[pivot:])


def _wrap(text: str, width: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


# ─── Header ──────────────────────────────────────────────────────────────────

def _draw_header(fig, team_name, team_id, round_num, match_date, n_matches, season, team_color):
    H_BOT, H_TOP = 0.870, 1.0
    ax = fig.add_axes([0.0, H_BOT, 1.0, H_TOP - H_BOT])
    ax.set_facecolor(CARD); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    ax.add_patch(patches.Rectangle((0, 0.90), 1, 0.10,
        facecolor=YELLOW, edgecolor="none", transform=ax.transAxes, zorder=2))
    ax.text(0.013, 0.95, "COMO JOGA",
            color="#111111", fontsize=7.5, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=3)
    meta = f"Série B {season}  ·  R{round_num}  ·  {match_date}  ·  {n_matches} partidas analisadas"
    ax.text(0.987, 0.95, meta,
            color="#444444", fontsize=6.5, fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes, zorder=3)

    ax.text(0.013, 0.62, "C O M O  O",
            color="#444444", fontsize=7.5, fontfamily=FONT_BODY,
            ha="left", va="center", transform=ax.transAxes)
    team_upper = team_name.upper()
    ax.text(0.013, 0.24, f"{team_upper}  JOGA",
            color=WHITE, fontsize=25, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes)

    logo = _load_logo(LOGOS_DIR / f"{team_id}.png", size=100, remove_bg=True)
    if logo is not None:
        LOGO_W = 0.072
        logo_ax = fig.add_axes([0.420, H_BOT, LOGO_W, H_TOP - H_BOT])
        logo_ax.imshow(logo); logo_ax.axis("off")


# ─── Painel 1: Heatmap ───────────────────────────────────────────────────────

def _draw_heatmap_panel(fig, zones: dict, team_color: str) -> None:
    PITCH_LEFT = 0.010
    PITCH_BOT  = 0.155
    PITCH_W    = 0.430
    PITCH_H    = 0.682
    LAX_GAP    = 0.003
    LAX_H      = 0.030

    lax = fig.add_axes([PITCH_LEFT, PITCH_BOT + PITCH_H + LAX_GAP, PITCH_W, LAX_H])
    lax.set_facecolor(BG); lax.axis("off")
    lax.set_xlim(0, 1); lax.set_ylim(0, 1)
    lax.text(0.0, 0.96, "MAPA DE ATUAÇÃO",
             color=WHITE, fontsize=8, fontweight="bold", fontfamily=FONT_TITLE,
             ha="left", va="top", transform=lax.transAxes)

    ax = fig.add_axes([PITCH_LEFT, PITCH_BOT, PITCH_W, PITCH_H])

    grid_pcts = zones.get("grid_pcts", [[0.0] * N_LAT] * N_DEPTH)
    lat_pcts  = zones.get("lat_pcts",  [0.0] * N_LAT)
    dep_pcts  = zones.get("dep_pcts",  [0.0] * N_DEPTH)
    all_pcts  = [grid_pcts[d][l] for d in range(N_DEPTH) for l in range(N_LAT)]
    max_pct   = max(all_pcts) or 1.0
    max_d, max_l = next(
        (d, l) for d in range(N_DEPTH) for l in range(N_LAT)
        if grid_pcts[d][l] == max_pct
    )

    if HAS_MPLSOCCER:
        pitch = Pitch(pitch_type="statsbomb",
                      pitch_color="#EBEBEB", line_color="#AAAAAA",
                      linewidth=0.7, goal_type="box", corner_arcs=True)
        pitch.draw(ax=ax)
    else:
        ax.set_facecolor("#EBEBEB")
        ax.set_xlim(0, 120); ax.set_ylim(0, 80); ax.axis("off")

    tc     = team_color.lstrip("#")
    hi_rgb = np.array([int(tc[i:i + 2], 16) for i in (0, 2, 4)], float) / 255
    lo_rgb = np.array([0.96, 0.97, 1.00])

    px_w = 24.0
    py_h = 80.0 / N_LAT

    for d in range(N_DEPTH):
        for l in range(N_LAT):
            pct   = grid_pcts[d][l]
            t     = (pct / max_pct) ** 2.0
            alpha = 0.18 + 0.82 * t
            color = lo_rgb + t * (hi_rgb - lo_rgb)
            px0, py0 = d * px_w, l * py_h

            ax.add_patch(patches.Rectangle(
                (px0, py0), px_w, py_h,
                facecolor=color, alpha=alpha,
                edgecolor="#C8C8C8", linewidth=0.5, zorder=3))

            is_max  = (d == max_d and l == max_l)
            txt_col = WHITE if t > 0.55 else "#111111"
            ax.text(px0 + px_w / 2, py0 + py_h / 2,
                    f"{pct:.0f}%",
                    color=txt_col,
                    fontsize=11 if is_max else 7.5,
                    fontweight="bold" if is_max else "normal",
                    fontfamily=FONT_TITLE, ha="center", va="center", zorder=6,
                    path_effects=[pe.withStroke(linewidth=2.5,
                                                foreground="#000" if t > 0.55 else "#FFF")])

    ax.add_patch(patches.Rectangle(
        (max_d * px_w, max_l * py_h), px_w, py_h,
        facecolor="none", edgecolor=YELLOW, linewidth=3.0, zorder=7))
    ax.text(max_d * px_w + px_w / 2, max_l * py_h + py_h * 0.13,
            "ZONA +\nUTILIZADA",
            color=YELLOW, fontsize=5.5, fontweight="bold", fontfamily=FONT_TITLE,
            ha="center", va="bottom", zorder=8,
            path_effects=[pe.withStroke(linewidth=2, foreground="#000")])

    y_lo, y_hi = ax.get_ylim()
    x_lo, x_hi = ax.get_xlim()
    x_span = x_hi - x_lo
    pad_x  = x_span * 0.025

    for l in range(N_LAT):
        cy = l * py_h + py_h / 2
        is_max_row = any(grid_pcts[d][l] == max_pct for d in range(N_DEPTH))
        ax.text(x_lo - pad_x, cy,
                f"{LAT_LABELS[l]}\n{lat_pcts[l]:.0f}%",
                color=YELLOW if is_max_row else "#555555",
                fontsize=6, fontweight="bold" if is_max_row else "normal",
                fontfamily=FONT_TITLE, ha="right", va="center",
                zorder=7, clip_on=False)

    for d in range(N_DEPTH):
        cx     = d * px_w + px_w / 2
        lax_x  = (cx - x_lo) / x_span
        is_max_col = any(grid_pcts[d][l] == max_pct for l in range(N_LAT))
        col = YELLOW if is_max_col else "#555555"
        fw  = "bold"  if is_max_col else "normal"
        lax.text(lax_x, 0.25,
                 f"{DEPTH_LABELS[d]}  {dep_pcts[d]:.0f}%",
                 color=col, fontsize=5.5, fontweight=fw, fontfamily=FONT_TITLE,
                 ha="center", va="center", transform=lax.transAxes)


# ─── Painel 2: Shotmap xG ────────────────────────────────────────────────────

def _draw_shotmap_panel(fig, shots: list[dict], team_color: str) -> None:
    SHOT_LEFT = 0.455
    SHOT_BOT  = 0.155
    SHOT_W    = 0.220
    SHOT_H    = 0.682
    LAX_GAP   = 0.003
    LAX_H     = 0.030

    # Título
    lax = fig.add_axes([SHOT_LEFT, SHOT_BOT + SHOT_H + LAX_GAP, SHOT_W, LAX_H])
    lax.set_facecolor(BG); lax.axis("off")
    lax.set_xlim(0, 1); lax.set_ylim(0, 1)
    lax.text(0.0, 0.96, "SHOTMAP  xG",
             color=WHITE, fontsize=8, fontweight="bold", fontfamily=FONT_TITLE,
             ha="left", va="top", transform=lax.transAxes)

    ax = fig.add_axes([SHOT_LEFT, SHOT_BOT, SHOT_W, SHOT_H])

    # Half-pitch orientado verticalmente (attacking end no topo)
    if HAS_MPLSOCCER:
        pitch = VerticalPitch(
            pitch_type="statsbomb",
            pitch_color="#1a1a1a", line_color="#444444",
            linewidth=0.6, goal_type="box", corner_arcs=True,
            half=True,
        )
        pitch.draw(ax=ax)
    else:
        ax.set_facecolor("#1a1a1a")
        ax.set_xlim(0, 80); ax.set_ylim(60, 120); ax.axis("off")

    if not shots:
        ax.text(0.5, 0.5, "Sem dados\nde shotmap",
                color=GRAY, fontsize=8, ha="center", va="center",
                transform=ax.transAxes)
        return

    tc     = team_color.lstrip("#")
    hi_rgb = np.array([int(tc[i:i + 2], 16) for i in (0, 2, 4)], float) / 255

    xg_vals = [float(s.get("xg") or 0) for s in shots]
    max_xg  = max(xg_vals) if xg_vals else 1.0

    xs, ys, sizes, colors_rgba = [], [], [], []
    for s, xg in zip(shots, xg_vals):
        px = float(s.get("player_x") or 0)
        py = float(s.get("player_y") or 50)
        sb_x, sb_y = _shot_to_statsbomb(px, py)

        # VerticalPitch: x→y, y→x
        xs.append(sb_y)
        ys.append(sb_x)

        t = (xg / max_xg) ** 0.6
        size = 15 + t * 220
        sizes.append(size)

        alpha = 0.25 + 0.60 * t
        col   = hi_rgb * t + np.array([0.18, 0.18, 0.18]) * (1 - t)
        colors_rgba.append((*col, alpha))

    # Sombra (blur effect via camadas)
    ax.scatter(xs, ys, s=[sz * 3.5 for sz in sizes],
               c=[[*hi_rgb, 0.04] for _ in xs],
               edgecolors="none", zorder=3)
    ax.scatter(xs, ys, s=sizes,
               c=colors_rgba,
               edgecolors=[[1, 1, 1, 0.25] for _ in xs],
               linewidths=0.5, zorder=5)

    # Gols — anel extra
    for s in shots:
        if s.get("shot_type") in ("goal", "Goal"):
            px = float(s.get("player_x") or 0)
            py = float(s.get("player_y") or 50)
            sb_x, sb_y = _shot_to_statsbomb(px, py)
            ax.scatter([sb_y], [sb_x], s=140, c="none",
                       edgecolors=YELLOW, linewidths=1.8, zorder=7)

    # Zonas de xG — rótulos compactos no campo
    shot_zones = _compute_shot_zones(shots)
    zone_labels = [
        (116, 40, "ÁREA\nCENTRAL", shot_zones["box_center"]),
        (108, 16, "ÁREA\nLATERAL",  shot_zones["box_sides"]),
        ( 87, 40, "FORA DA\nÁREA",  shot_zones["outside"]),
    ]
    for sx, sy, lbl, zdata in zone_labels:
        if zdata["shots"] == 0:
            continue
        xg_z  = zdata["xg"]
        n_z   = zdata["shots"]
        # VerticalPitch: plot with x=sy, y=sx
        ax.text(sy, sx, f"{lbl}\n{n_z}ch · {xg_z:.2f}xG",
                color=LGRAY, fontsize=4.2, fontfamily=FONT_BODY,
                ha="center", va="center", zorder=8,
                path_effects=[pe.withStroke(linewidth=2.0, foreground="#111111")])

    # Legenda xG (tamanho de bolha)
    _draw_xg_legend(ax, max_xg, hi_rgb)


def _draw_xg_legend(ax, max_xg: float, hi_rgb):
    """Mini legenda com 3 tamanhos representativos de xG."""
    try:
        y_lo, y_hi = ax.get_ylim()
        x_lo, x_hi = ax.get_xlim()
    except Exception:
        return

    legend_xg = [0.05, 0.20, max_xg * 0.85]
    label_txt  = ["baixo", "médio", "alto"]
    x_step     = (x_hi - x_lo) * 0.22
    cx_start   = x_lo + (x_hi - x_lo) * 0.18
    cy         = y_lo + (y_hi - y_lo) * 0.085

    for i, (xg_ref, lbl) in enumerate(zip(legend_xg, label_txt)):
        t    = (xg_ref / max_xg) ** 0.6
        size = 15 + t * 220
        col  = hi_rgb * t + np.array([0.18, 0.18, 0.18]) * (1 - t)
        cx   = cx_start + i * x_step
        ax.scatter([cx], [cy], s=size, c=[(*col, 0.75)],
                   edgecolors=[[1, 1, 1, 0.3]], linewidths=0.4, zorder=9)
        ax.text(cx, cy - (y_hi - y_lo) * 0.030, lbl,
                color=GRAY, fontsize=4.0, fontfamily=FONT_BODY,
                ha="center", va="top", zorder=9)

    ax.text(cx_start + x_step, cy + (y_hi - y_lo) * 0.060,
            "● tamanho ∝ xG",
            color=GRAY, fontsize=4.0, fontfamily=FONT_BODY,
            ha="center", va="bottom", zorder=9)


# ─── Painel 3: Estilo + Métricas ─────────────────────────────────────────────

def _draw_right_panel(fig, zones: dict, profile: dict, team_color: str) -> None:
    tc    = team_color.lstrip("#")
    t_rgb = np.array([int(tc[i:i + 2], 16) for i in (0, 2, 4)], float) / 255

    RIGHT_LEFT = 0.690
    RIGHT_W    = 0.305

    # ── BLOCO 1: Estilo de jogo ──────────────────────────────────────────────
    STYLE_H   = 0.210
    STYLE_BOT = 0.867 - STYLE_H

    sax = fig.add_axes([RIGHT_LEFT, STYLE_BOT, RIGHT_W, STYLE_H])
    sax.set_facecolor(CARD2); sax.axis("off")
    sax.set_xlim(0, 1); sax.set_ylim(0, 1)

    sax.add_patch(patches.Rectangle((0, 0.880), 1, 0.120,
        facecolor=CARD3, edgecolor="none", transform=sax.transAxes, zorder=2))
    sax.add_patch(patches.Rectangle((0, 0.880), 0.005, 0.120,
        facecolor=YELLOW, edgecolor="none", transform=sax.transAxes, zorder=3))
    sax.text(0.030, 0.940, "ESTILO DE JOGO",
             color=WHITE, fontsize=8.5, fontweight="bold", fontfamily=FONT_TITLE,
             ha="left", va="center", transform=sax.transAxes, zorder=4)

    patterns = profile.get("patterns", [])
    if not patterns:
        patterns = _zone_patterns(zones)

    y0     = 0.840
    line_h = 0.330

    for i, pat in enumerate(patterns[:3]):
        keyword, detail = _parse_pattern(pat)
        icon = PATTERN_ICONS[i] if i < len(PATTERN_ICONS) else "▶"

        sax.text(0.018, y0 - 0.012, icon,
                 color=YELLOW, fontsize=9, fontfamily=FONT_BODY,
                 ha="left", va="top", transform=sax.transAxes, zorder=5)
        sax.text(0.075, y0 - 0.012, keyword,
                 color=WHITE, fontsize=7.5, fontweight="bold", fontfamily=FONT_BODY,
                 ha="left", va="top", transform=sax.transAxes, zorder=5)
        if detail:
            for j, dline in enumerate(_wrap(detail, 44)):
                sax.text(0.075, y0 - 0.012 - 0.048 - j * 0.038, dline,
                         color=LGRAY, fontsize=6.5, fontfamily=FONT_BODY,
                         ha="left", va="top", transform=sax.transAxes, zorder=5)
        y0 -= line_h

    sax.plot([0.015, 0.985], [0.0, 0.0],
             color=DGRAY, lw=0.5, transform=sax.transAxes)

    # ── BLOCO 2: Métricas ────────────────────────────────────────────────────
    MET_BOT = 0.155
    MET_H   = STYLE_BOT - MET_BOT - 0.012

    met = fig.add_axes([RIGHT_LEFT, MET_BOT, RIGHT_W, MET_H])
    met.set_facecolor(CARD2); met.axis("off")
    met.set_xlim(0, 1); met.set_ylim(0, 1)

    met.add_patch(patches.Rectangle((0, 0.900), 1, 0.100,
        facecolor=CARD3, edgecolor="none", transform=met.transAxes, zorder=2))
    met.add_patch(patches.Rectangle((0, 0.900), 0.005, 0.100,
        facecolor=YELLOW, edgecolor="none", transform=met.transAxes, zorder=3))
    met.text(0.030, 0.950, "MÉTRICAS POR PARTIDA",
             color=WHITE, fontsize=8.5, fontweight="bold", fontfamily=FONT_TITLE,
             ha="left", va="center", transform=met.transAxes, zorder=4)
    met.text(0.980, 0.950, "| ref. liga",
             color=GRAY, fontsize=5.5, fontfamily=FONT_BODY,
             ha="right", va="center", transform=met.transAxes, zorder=4)

    avg = profile.get("averages", {})
    metrics = [
        ("Posse de bola",          avg.get("possession",           0), "%",   60,   False, "possession"),
        ("xG (gols esperados)",    avg.get("expected_goals",       0), "",    2.5,  True,  "expected_goals"),
        ("Entradas no 3º terço",   avg.get("final_third_entries",  0), "/j",  35,   True,  "final_third_entries"),
        ("Bolas longas (%passes)", avg.get("long_balls_pct",       0), "%",   15,   True,  "long_balls_pct"),
        ("Toques na área adversária", avg.get("touches_opp_box",   0), "/j",  25,   True,  "touches_opp_box"),
    ]

    content_h = 0.885
    n_metrics = sum(1 for _, v, *_ in metrics if v != 0)
    block_h   = content_h / max(n_metrics, 1)
    bar_h     = min(0.036, block_h * 0.22)
    BX, BW    = 0.025, 0.950

    drawn = 0
    for label, val, unit, ref_scale, higher_is_good, ref_key in metrics:
        if val == 0:
            continue

        y_top_b = content_h - drawn * block_h
        y_row1  = y_top_b - block_h * 0.20
        y_bar   = y_top_b - block_h * 0.65
        bar_bot = y_bar - bar_h / 2
        drawn  += 1

        ref_val  = SERIE_B_AVG.get(ref_key)
        bar_fill = min(val / ref_scale, 1.0)

        status_txt = ""; status_col = GRAY; arrow_g = ""
        if ref_val:
            ratio = val / ref_val
            if ratio >= 1.10:
                status_txt = "acima"; arrow_g = "\u25b2 "
                status_col = GREEN if higher_is_good else RED
            elif ratio <= 0.90:
                status_txt = "abaixo"; arrow_g = "\u25bc "
                status_col = RED if higher_is_good else GREEN
            else:
                status_txt = "na média"; arrow_g = "\u2248 "
                status_col = GRAY

        met.text(BX, y_row1, label,
                 color=LGRAY, fontsize=6.5, fontfamily=FONT_BODY,
                 ha="left", va="center", transform=met.transAxes)
        val_str = f"{val:.0f}%" if unit == "%" else f"{val:.1f}{unit}"
        met.text(BX + BW, y_row1, val_str,
                 color=WHITE, fontsize=8.5, fontweight="bold", fontfamily=FONT_TITLE,
                 ha="right", va="center", transform=met.transAxes)

        if status_txt:
            met.text(BX + BW, y_row1 - block_h * 0.24,
                     f"{arrow_g}{status_txt}",
                     color=status_col, fontsize=5.5, fontfamily=FONT_BODY,
                     ha="right", va="center", transform=met.transAxes)

        met.add_patch(patches.Rectangle(
            (BX, bar_bot), BW, bar_h,
            facecolor="#252525", edgecolor="none",
            transform=met.transAxes, zorder=2))
        fill_col = np.clip(t_rgb * bar_fill + np.array([0.12, 0.12, 0.12]) * (1 - bar_fill), 0, 1)
        met.add_patch(patches.Rectangle(
            (BX, bar_bot), BW * bar_fill, bar_h,
            facecolor=fill_col, edgecolor="none",
            transform=met.transAxes, zorder=3))
        if ref_val:
            ref_x = BX + BW * min(ref_val / ref_scale, 1.0)
            met.plot([ref_x, ref_x],
                     [bar_bot - 0.004, bar_bot + bar_h + 0.004],
                     color=YELLOW, lw=1.5, zorder=5, transform=met.transAxes)

        if drawn < n_metrics:
            met.plot([BX, BX + BW], [bar_bot - block_h * 0.14, bar_bot - block_h * 0.14],
                     color="#2e2e2e", lw=0.4, transform=met.transAxes)


# ─── Fallback padrões de zona ─────────────────────────────────────────────────

def _zone_patterns(zones: dict) -> list[str]:
    dep = zones.get("dep_pcts", [0] * N_DEPTH)
    lat = zones.get("lat_pcts", [34, 33, 33])
    bullets = []
    off_pct = dep[3] + dep[4]
    if off_pct > 35:
        bullets.append(f"Alta presença ofensiva — {off_pct:.0f}% no terço atacante")
    elif dep[2] > 38:
        bullets.append(f"Bloco médio — {dep[2]:.0f}% no meio-campo")
    else:
        bullets.append(f"Bloco baixo — {dep[0] + dep[1]:.0f}% no terço defensivo")
    dom = max(range(3), key=lambda i: lat[i])
    lat_name = ["esquerdo", "central", "direito"][dom]
    bullets.append(f"Corredor {lat_name} — {lat[dom]:.0f}% do volume posicional")
    bullets.append("Padrão calculado por zonas de posicionamento")
    return bullets


# ─── Resumo ───────────────────────────────────────────────────────────────────

def _draw_resumo(fig, resumo: str) -> None:
    ax = fig.add_axes([0.0, 0.058, 1.0, 0.098])
    ax.set_facecolor(CARD4); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    ax.add_patch(patches.Rectangle((0, 0.93), 1, 0.07,
        facecolor=YELLOW, edgecolor="none",
        transform=ax.transAxes, zorder=2))
    ax.text(0.014, 0.965, "SÍNTESE",
            color="#111111", fontsize=7, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=3)

    ax.text(0.014, 0.44, "//",
            color=YELLOW, fontsize=10.5, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=3)
    ax.text(0.048, 0.44, resumo,
            color=WHITE, fontsize=10, fontfamily=FONT_BODY, fontweight="bold",
            ha="left", va="center", transform=ax.transAxes, zorder=3)


# ─── Footer ──────────────────────────────────────────────────────────────────

def _draw_footer(fig) -> None:
    ax = fig.add_axes([0.0, 0.0, 1.0, 0.056])
    ax.set_facecolor(CARD); ax.axis("off")
    ax.plot([0, 1], [1, 1], color=DGRAY, lw=0.5, transform=ax.transAxes)
    ax.text(0.015, 0.5,
            "Dados: SofaScore  ·  Posicionamento agregado · Shotmap acumulado  ·  @SportRecifeLab",
            color=GRAY, fontsize=6.5, fontfamily=FONT_BODY,
            ha="left", va="center", transform=ax.transAxes)
    ax.text(0.987, 0.5, "@SportRecifeLab",
            color=LGRAY, fontsize=7.5, fontweight="bold", fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes)

    srl = _load_logo(Path(LOGO_SRL), size=32)
    if srl is not None:
        srl_ax = fig.add_axes([0.001, 0.002, 0.020, 0.053])
        srl_ax.imshow(srl); srl_ax.axis("off")


# ─── Função principal ─────────────────────────────────────────────────────────

def generate_como_joga_card_v2(
    heatmap_path: str | Path,
    attack_profile_path: str | Path | None,
    team_name: str,
    team_id: int,
    round_num: int,
    match_date: str,
    season: int,
    team_color: str,
    output_path: str,
) -> None:
    with open(heatmap_path, encoding="utf-8") as f:
        hm = json.load(f)
    points    = hm.get("points", [])
    n_matches = hm.get("match_count", 0)
    zones     = _compute_zones(points)

    profile: dict = {}
    shots: list[dict] = []
    if attack_profile_path and Path(attack_profile_path).exists():
        with open(attack_profile_path, encoding="utf-8") as f:
            profile = json.load(f)
        shots = profile.get("shots", [])

    resumo = _build_resumo(profile, zones)

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)

    _draw_header(fig, team_name, team_id, round_num, match_date, n_matches, season, team_color)
    _draw_heatmap_panel(fig, zones, team_color)
    _draw_shotmap_panel(fig, shots, team_color)
    _draw_right_panel(fig, zones, profile, team_color)
    _draw_resumo(fig, resumo)
    _draw_footer(fig)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  OK {output_path}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--team-key",   required=True)
    parser.add_argument("--team-name",  required=True)
    parser.add_argument("--team-id",    type=int, required=True)
    parser.add_argument("--round",      type=int, required=True, dest="round_num")
    parser.add_argument("--date",       required=True)
    parser.add_argument("--season",     type=int, default=2026)
    parser.add_argument("--team-color", default="#003DA5", dest="team_color")
    parser.add_argument("--out-dir",    default="")
    args = parser.parse_args()

    base = Path("C:/Users/compesa/Desktop/SportSofa")
    hm   = base / "data/processed" / str(args.season) / "opponents" / args.team_key / "team_heatmap.json"
    ap   = base / "data/curated" / f"opponents_{args.season}" / args.team_key / "attack_profile.json"

    if not hm.exists():
        print(f"ERRO: {hm} nao encontrado."); return

    out_dir     = args.out_dir or f"pending_posts/{args.date}_raio-x-{args.team_key}"
    output_path = os.path.join(out_dir, "07_como_joga.png")

    print(f"Gerando card Como Joga v2 para {args.team_name}...")
    generate_como_joga_card_v2(
        heatmap_path        = hm,
        attack_profile_path = ap,
        team_name           = args.team_name,
        team_id             = args.team_id,
        round_num           = args.round_num,
        match_date          = args.date,
        season              = args.season,
        team_color          = args.team_color,
        output_path         = output_path,
    )


if __name__ == "__main__":
    main()
