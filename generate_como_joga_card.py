"""
Gera o card "Como o [TIME] Joga" — @SportRecifeLab
Otimizado para redes sociais (X/Twitter): leitura em <3s, hierarquia editorial clara.

Layout:
  ┌───────────────────────────────────────────────────────────────────┐
  │  "COMO O" (pequeno)  /  AVAI FC JOGA (dominante)   [escudo]      │
  ├─────────────────────────┬─────────────────────────────────────────┤
  │  MAPA DE ATUAÇÃO        │  ESTILO DE JOGO  (🎯⚡🚫 bullets)       │
  │  [15 zonas, contraste   │  ─────────────────────────────────────  │
  │   acentuado, tag max]   │  MÉTRICAS POR PARTIDA                   │
  │  [legenda]              │  [valor grande + acima/abaixo + barra]   │
  ├─────────────────────────┴─────────────────────────────────────────┤
  │  ▶  SÍNTESE — insight principal                                   │
  └───────────────────────────────────────────────────────────────────┘

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
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np

try:
    from mplsoccer import Pitch
    HAS_MPLSOCCER = True
except ImportError:
    HAS_MPLSOCCER = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


# ─── Paleta ───────────────────────────────────────────────────────────────────
BG      = "#0d0d0d"
CARD    = "#141414"
CARD2   = "#1a1a1a"
CARD3   = "#222222"
CARD4   = "#111820"   # resumo: azul-escuro contrastante
YELLOW  = "#F5C400"
WHITE   = "#FFFFFF"
LGRAY   = "#B0B0B0"
GRAY    = "#666666"
DGRAY   = "#333333"
GREEN   = "#2ECC71"
RED     = "#E74C3C"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"
FONT_EMOJI = "Segoe UI Emoji"      # suporte a emoji no Windows

FIG_W, FIG_H = 14.0, 7.5
DPI = 130

LOGO_SRL  = "sportrecifelab_avatar.png"
LOGOS_DIR = Path("data/cache/logos")

# Grid 5 × 3  (profundidade × lateral)
N_DEPTH = 5
N_LAT   = 3
DEPTH_LABELS = ["3º DEF", "2º DEF", "MEIO", "2º ATQ", "3º ATQ"]
LAT_LABELS   = ["ESQ", "CENTRO", "DIR"]

# Médias de referência Série B 2026
SERIE_B_AVG = {
    "possession":        50.0,
    "expected_goals":     1.10,
    "shots_outside_box":  4.8,
    "long_balls_pct":     7.5,
    "interceptions":     16.0,
    "touches_opp_box":   18.0,
}

# Ícones por bullet — renderizados sólidos em Arial (testados)
PATTERN_ICONS = ["\u25cf", "\u2666", "\u25b2", "\u25c4"]  # ● ♦ ▲ ◄


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


# ─── Análise ──────────────────────────────────────────────────────────────────

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
    """Retorna (keyword_bold, detail_text) separando em ' — ' ou ' ('."""
    if " — " in pat:
        bold, _, rest = pat.partition(" — ")
        return bold.strip(), rest.strip()
    if " (" in pat:
        bold, _, rest = pat.partition(" (")
        return bold.strip(), "(" + rest.strip()
    # fallback: primeiras palavras como keyword
    words = pat.split()
    pivot = min(4, len(words))
    return " ".join(words[:pivot]), " ".join(words[pivot:])


# ─── Card principal ───────────────────────────────────────────────────────────

def generate_como_joga_card(
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
    if attack_profile_path and Path(attack_profile_path).exists():
        with open(attack_profile_path, encoding="utf-8") as f:
            profile = json.load(f)

    resumo = _build_resumo(profile, zones)

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)

    _draw_header(fig, team_name, team_id, round_num, match_date, n_matches, season, team_color)
    _draw_pitch_panel(fig, zones, team_color)
    _draw_style_panel(fig, zones, profile, team_color)
    _draw_resumo(fig, resumo)
    _draw_footer(fig)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    fig.savefig(output_path, dpi=DPI, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  OK {output_path}")


# ─── Header ──────────────────────────────────────────────────────────────────

def _draw_header(fig, team_name, team_id, round_num, match_date,
                 n_matches, season, team_color):
    H_BOT, H_TOP = 0.870, 1.0
    ax = fig.add_axes([0.0, H_BOT, 1.0, H_TOP - H_BOT])
    ax.set_facecolor(CARD)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # Barra amarela superior — 10% da altura do header
    ax.add_patch(patches.Rectangle((0, 0.90), 1, 0.10,
        facecolor=YELLOW, edgecolor="none", transform=ax.transAxes, zorder=2))
    ax.text(0.013, 0.95, "COMO JOGA",
            color="#111111", fontsize=7.5, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=3)
    # Metadata à direita, discreto
    meta = f"Série B {season}  ·  R{round_num}  ·  {match_date}  ·  {n_matches} partidas analisadas"
    ax.text(0.987, 0.95, meta,
            color="#444444", fontsize=6.5, fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes, zorder=3)

    # "COMO O" — muito pequeno, sem peso
    ax.text(0.013, 0.62, "C O M O  O",
            color="#444444", fontsize=7.5, fontfamily=FONT_BODY,
            ha="left", va="center", transform=ax.transAxes)

    # Nome do time — dominante
    team_upper = team_name.upper()
    ax.text(0.013, 0.24, f"{team_upper}  JOGA",
            color=WHITE, fontsize=25, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes)

    # Escudo — posicionado ao lado do título
    logo = _load_logo(LOGOS_DIR / f"{team_id}.png", size=100, remove_bg=True)
    if logo is not None:
        LOGO_W = 0.072
        logo_ax = fig.add_axes([0.430, H_BOT, LOGO_W, H_TOP - H_BOT])
        logo_ax.imshow(logo); logo_ax.axis("off")


# ─── Heatmap ──────────────────────────────────────────────────────────────────

def _draw_pitch_panel(fig, zones: dict, team_color: str) -> None:
    # ── Layout constants ──────────────────────────────────────────────────────
    PITCH_LEFT = 0.010
    PITCH_BOT  = 0.155   # bottom of pitch axes
    PITCH_W    = 0.530
    PITCH_H    = 0.682   # top at 0.837
    LAX_GAP    = 0.003
    LAX_H      = 0.030   # label strip; top at 0.870 (< header H_BOT=0.872)

    # ── Tira de título — criada antes do pitch para receber depth labels depois
    lax = fig.add_axes([PITCH_LEFT, PITCH_BOT + PITCH_H + LAX_GAP, PITCH_W, LAX_H])
    lax.set_facecolor(BG); lax.axis("off")
    lax.set_xlim(0, 1); lax.set_ylim(0, 1)
    # Título no lado esquerdo do topo; depth labels irão ao fundo (y=0.25)
    lax.text(0.0, 0.96, "MAPA DE ATUAÇÃO",
             color=WHITE, fontsize=8, fontweight="bold", fontfamily=FONT_TITLE,
             ha="left", va="top", transform=lax.transAxes)

    # ── Eixo do campo ─────────────────────────────────────────────────────────
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

    # ── Gradiente ─────────────────────────────────────────────────────────────
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

    # Borda amarela + tag na zona máxima
    ax.add_patch(patches.Rectangle(
        (max_d * px_w, max_l * py_h), px_w, py_h,
        facecolor="none", edgecolor=YELLOW, linewidth=3.0, zorder=7))
    ax.text(max_d * px_w + px_w / 2, max_l * py_h + py_h * 0.13,
            "ZONA +\nUTILIZADA",
            color=YELLOW, fontsize=5.5, fontweight="bold", fontfamily=FONT_TITLE,
            ha="center", va="bottom", zorder=8,
            path_effects=[pe.withStroke(linewidth=2, foreground="#000")])

    # ── Obter limites reais do pitch (após draw) ──────────────────────────────
    y_lo, y_hi = ax.get_ylim()
    x_lo, x_hi = ax.get_xlim()
    x_span = x_hi - x_lo
    pad_x  = x_span * 0.025

    # ── Rótulos laterais — à esquerda (clip_on=False só vai para a esquerda,
    #    fora do eixo mas dentro da figura) ────────────────────────────────────
    for l in range(N_LAT):
        cy = l * py_h + py_h / 2
        is_max_row = any(grid_pcts[d][l] == max_pct for d in range(N_DEPTH))
        ax.text(x_lo - pad_x, cy,
                f"{LAT_LABELS[l]}\n{lat_pcts[l]:.0f}%",
                color=YELLOW if is_max_row else "#555555",
                fontsize=6, fontweight="bold" if is_max_row else "normal",
                fontfamily=FONT_TITLE, ha="right", va="center",
                zorder=7, clip_on=False)

    # ── Depth labels → desenhados no lax (sem escape de eixo) ────────────────
    # O centro de cada coluna no eixo do pitch mapeia para uma fração do lax.
    for d in range(N_DEPTH):
        cx     = d * px_w + px_w / 2        # coord no eixo do pitch
        lax_x  = (cx - x_lo) / x_span       # fração 0-1 dentro do lax
        is_max_col = any(grid_pcts[d][l] == max_pct for l in range(N_LAT))
        col = YELLOW if is_max_col else "#555555"
        fw  = "bold"   if is_max_col else "normal"
        lax.text(lax_x, 0.25,
                 f"{DEPTH_LABELS[d]}  {dep_pcts[d]:.0f}%",
                 color=col, fontsize=5.5, fontweight=fw, fontfamily=FONT_TITLE,
                 ha="center", va="center", transform=lax.transAxes)


def _draw_inline_legend(ax, px_w: float, n_depth: int, lo_rgb, hi_rgb):
    """Desenha legenda de intensidade como tira fina abaixo do campo (dentro do eixo do pitch)."""
    y_lo, _ = ax.get_ylim()
    x_lo, x_hi = ax.get_xlim()
    pitch_width = px_w * n_depth
    leg_h = (x_hi - x_lo) * 0.015   # proporcional ao campo
    leg_y = y_lo - leg_h * 1.6

    steps = 60
    step_w = pitch_width / steps
    for i in range(steps):
        t = i / (steps - 1)
        c = lo_rgb + t * (hi_rgb - lo_rgb)
        ax.add_patch(patches.Rectangle(
            (x_lo + i * step_w, leg_y), step_w, leg_h * 0.6,
            facecolor=c, edgecolor="none", zorder=6, clip_on=False))

    mid_x = x_lo + pitch_width / 2
    ax.text(mid_x, leg_y - leg_h * 0.3, "intensidade de presença",
            color=GRAY, fontsize=5, fontfamily=FONT_BODY,
            ha="center", va="top", zorder=6, clip_on=False)
    ax.text(x_lo - 1, leg_y + leg_h * 0.3, "baixa",
            color=GRAY, fontsize=5, fontfamily=FONT_BODY,
            ha="right", va="center", zorder=6, clip_on=False)
    ax.text(x_lo + pitch_width + 1, leg_y + leg_h * 0.3, "alta",
            color=GRAY, fontsize=5, fontfamily=FONT_BODY,
            ha="left", va="center", zorder=6, clip_on=False)


# ─── Painel direito ───────────────────────────────────────────────────────────

def _draw_style_panel(fig, zones: dict, profile: dict, team_color: str) -> None:
    tc    = team_color.lstrip("#")
    t_rgb = np.array([int(tc[i:i + 2], 16) for i in (0, 2, 4)], float) / 255

    RIGHT_LEFT = 0.560
    RIGHT_W    = 0.432

    # ── BLOCO 1: Estilo de jogo ───────────────────────────────────────────────
    STYLE_H   = 0.220   # dimensionado para header + 3 bullets com espaçamento
    STYLE_BOT = 0.867 - STYLE_H   # encosta no header (0.647)

    sax = fig.add_axes([RIGHT_LEFT, STYLE_BOT, RIGHT_W, STYLE_H])
    sax.set_facecolor(CARD2); sax.axis("off")
    sax.set_xlim(0, 1); sax.set_ylim(0, 1)

    # Header do bloco
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

    icons = PATTERN_ICONS
    y0       = 0.840
    line_h   = 0.340    # maior espaçamento → bullets preenchem o painel
    icon_x   = 0.018
    kw_x     = 0.075
    detail_x = 0.075

    for i, pat in enumerate(patterns[:3]):
        keyword, detail = _parse_pattern(pat)
        icon = icons[i] if i < len(icons) else "▶"

        # Ícone
        sax.text(icon_x, y0 - 0.012, icon,
                 color=YELLOW, fontsize=9, fontfamily=FONT_BODY,
                 ha="left", va="top", transform=sax.transAxes, zorder=5)

        # Keyword — bold, branco
        sax.text(kw_x, y0 - 0.012, keyword,
                 color=WHITE, fontsize=8, fontweight="bold", fontfamily=FONT_BODY,
                 ha="left", va="top", transform=sax.transAxes, zorder=5)

        # Detalhe — normal, cinza claro, linha abaixo
        if detail:
            for j, dline in enumerate(_wrap(detail, 48)):
                sax.text(detail_x, y0 - 0.012 - 0.048 - j * 0.038, dline,
                         color=LGRAY, fontsize=7, fontfamily=FONT_BODY,
                         ha="left", va="top", transform=sax.transAxes, zorder=5)

        y0 -= line_h

    # Linha separadora
    sax.plot([0.015, 0.985], [0.0, 0.0],
             color=DGRAY, lw=0.5, transform=sax.transAxes)

    # ── BLOCO 2: Métricas ─────────────────────────────────────────────────────
    # Ocupa o espaço entre o fundo do card e o bloco de estilo
    MET_BOT = 0.155
    MET_H   = STYLE_BOT - MET_BOT - 0.012   # gap de 12px entre blocos

    met = fig.add_axes([RIGHT_LEFT, MET_BOT, RIGHT_W, MET_H])
    met.set_facecolor(CARD2); met.axis("off")
    met.set_xlim(0, 1); met.set_ylim(0, 1)

    # Header do bloco
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
        ("Posse de bola",          avg.get("possession",         0), "%",   60,  False, "possession"),
        ("xG (gols esperados)",    avg.get("expected_goals",     0), "",    2.5, True,  "expected_goals"),
        ("Chutes fora da área",    avg.get("shots_outside_box",  0), "/j",  10,  True,  "shots_outside_box"),
        ("Bolas longas (%passes)", avg.get("long_balls_pct",     0), "%",   15,  True,  "long_balls_pct"),
        ("Interceptações",         avg.get("interceptions",      0), "/j",  20,  True,  "interceptions"),
    ]

    # Layout 2 linhas por métrica — calculado dinamicamente
    # Área de conteúdo: y=[0, 0.890] (abaixo do header)
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

        # Status
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

        # Linha 1: label (esq) · valor bold (dir)
        met.text(BX, y_row1, label,
                 color=LGRAY, fontsize=6.5, fontfamily=FONT_BODY,
                 ha="left", va="center", transform=met.transAxes)
        val_str = f"{val:.0f}%" if unit == "%" else f"{val:.1f}{unit}"
        met.text(BX + BW, y_row1, val_str,
                 color=WHITE, fontsize=8.5, fontweight="bold", fontfamily=FONT_TITLE,
                 ha="right", va="center", transform=met.transAxes)

        # Status pequeno logo abaixo do valor
        if status_txt:
            met.text(BX + BW, y_row1 - block_h * 0.24,
                     f"{arrow_g}{status_txt}",
                     color=status_col, fontsize=5.5, fontfamily=FONT_BODY,
                     ha="right", va="center", transform=met.transAxes)

        # Linha 2: barra
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

        # Separador
        if drawn < n_metrics:
            met.plot([BX, BX + BW], [bar_bot - block_h * 0.14, bar_bot - block_h * 0.14],
                     color="#2e2e2e", lw=0.4, transform=met.transAxes)


# ─── Resumo ───────────────────────────────────────────────────────────────────

def _draw_resumo(fig, resumo: str) -> None:
    """Síntese em destaque — fundo contrastante, fonte grande, leitura imediata."""
    ax = fig.add_axes([0.0, 0.058, 1.0, 0.098])
    ax.set_facecolor(CARD4); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

    # Borda superior amarela
    ax.add_patch(patches.Rectangle((0, 0.93), 1, 0.07,
        facecolor=YELLOW, edgecolor="none",
        transform=ax.transAxes, zorder=2))
    ax.text(0.014, 0.965, "SÍNTESE",
            color="#111111", fontsize=7, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=3)

    # Marcador de destaque
    ax.text(0.014, 0.44, "//",
            color=YELLOW, fontsize=10.5, fontweight="bold", fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=3)

    # Texto principal — grande, legível
    ax.text(0.048, 0.44, resumo,
            color=WHITE, fontsize=10, fontfamily=FONT_BODY, fontweight="bold",
            ha="left", va="center", transform=ax.transAxes, zorder=3)


# ─── Footer ──────────────────────────────────────────────────────────────────

def _draw_footer(fig) -> None:
    ax = fig.add_axes([0.0, 0.0, 1.0, 0.056])
    ax.set_facecolor(CARD); ax.axis("off")
    ax.plot([0, 1], [1, 1], color=DGRAY, lw=0.5, transform=ax.transAxes)
    ax.text(0.015, 0.5,
            "Dados: SofaScore  ·  Posicionamento agregado por jogador/partida  ·  @SportRecifeLab",
            color=GRAY, fontsize=6.5, fontfamily=FONT_BODY,
            ha="left", va="center", transform=ax.transAxes)
    ax.text(0.987, 0.5, "@SportRecifeLab",
            color=LGRAY, fontsize=7.5, fontweight="bold", fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes)

    srl = _load_logo(Path(LOGO_SRL), size=32)
    if srl is not None:
        srl_ax = fig.add_axes([0.001, 0.002, 0.020, 0.053])
        srl_ax.imshow(srl); srl_ax.axis("off")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _zone_patterns(zones: dict) -> list[str]:
    lat  = zones.get("lat_pcts", [34, 33, 33])
    dep  = zones.get("dep_pcts", [0] * 5)
    off  = dep[3] + dep[4]
    dom  = max(range(3), key=lambda i: lat[i])
    names = ["esquerdo", "central", "direito"]
    bullets = [f"Corredor {names[dom]} dominante — {lat[dom]:.0f}% das ações"]
    if off >= 35:
        bullets.append(f"Linha alta — {off:.0f}% das ações no campo ofensivo")
    else:
        bullets.append(f"Bloco médio — {dep[2]:.0f}% no meio-campo")
    return bullets


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

    print(f"Gerando card Como Joga para {args.team_name}...")
    generate_como_joga_card(
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
