"""
Gera os 6 cards visuais do Raio-X Fortaleza — Copa do Nordeste 2026
@SportRecifeLab

Cards:
  01_cover.png        — abertura
  02_campanha.png     — campanha geral 2026
  03_mandante.png     — Fortaleza como mandante (Sport joga lá)
  04_ultimos5.png     — últimas 5 partidas
  05_xg.png           — análise xG e perfil ofensivo
  06_jogadores.png    — destaques individuais

Fonte: data/processed/2026/opponents/fortaleza/ (pós sync-opponent)
       data/curated/opponents_2026/fortaleza/   (pós transform-opponent)
"""

import os
import datetime
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
import pandas as pd

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from collections import deque

# ── paths ─────────────────────────────────────────────────────────────────────
BASE        = os.path.dirname(os.path.abspath(__file__))
PROC_DIR    = os.path.join(BASE, "data", "processed", "2026", "opponents", "fortaleza")
CUR_DIR     = os.path.join(BASE, "data", "curated", "opponents_2026", "fortaleza")
LOGOS_DIR   = os.path.join(BASE, "data", "cache", "logos")
AVATAR      = os.path.join(BASE, "sportrecifelab_avatar.png")

TODAY       = datetime.date.today().strftime("%Y-%m-%d")
OUT_DIR     = os.path.join(BASE, "pending_posts", f"{TODAY}_raio-x-fortaleza")
FORTALEZA_ID = 2020

# ── paleta ────────────────────────────────────────────────────────────────────
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
FORD   = "#0033A0"   # azul Fortaleza
FORD2  = "#C8102E"   # vermelho Fortaleza

FIG_W, FIG_H = 9.0, 9.0
DPI          = 120
FONT_TITLE   = "Franklin Gothic Heavy"
FONT_BODY    = "Arial"


# ── background removal ────────────────────────────────────────────────────────
def _remove_bg_floodfill(img, thresh=25):
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    is_white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)
    visited = np.zeros((h, w), dtype=bool)
    queue = deque()
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


def _load_logo(team_id, size=220):
    path = os.path.join(LOGOS_DIR, f"{team_id}.png")
    if not os.path.exists(path) or not HAS_PIL:
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = _remove_bg_floodfill(img)
        img = img.resize((size, size), Image.LANCZOS)
        return img
    except Exception:
        return None


# ── data loading ──────────────────────────────────────────────────────────────
def _load_data():
    # Prefer curated if available, fallback to processed
    matches_path = (
        os.path.join(CUR_DIR, "matches.csv")
        if os.path.exists(os.path.join(CUR_DIR, "matches.csv"))
        else os.path.join(PROC_DIR, "matches.csv")
    )
    stats_path = (
        os.path.join(CUR_DIR, "team_match_stats.csv")
        if os.path.exists(os.path.join(CUR_DIR, "team_match_stats.csv"))
        else os.path.join(PROC_DIR, "team_match_stats.csv")
    )
    players_path = (
        os.path.join(CUR_DIR, "player_match_stats.csv")
        if os.path.exists(os.path.join(CUR_DIR, "player_match_stats.csv"))
        else os.path.join(PROC_DIR, "player_match_stats.csv")
    )

    matches = pd.read_csv(matches_path) if os.path.exists(matches_path) else pd.DataFrame()
    stats   = pd.read_csv(stats_path)   if os.path.exists(stats_path)   else pd.DataFrame()
    players = pd.read_csv(players_path) if os.path.exists(players_path) else pd.DataFrame()
    return matches, stats, players


def _team_outcome(row):
    """Determine Fortaleza's outcome from a match row."""
    home = str(row.get("home_team", "")).lower()
    is_home = "fortaleza" in home
    hs = row.get("home_score", 0) or 0
    as_ = row.get("away_score", 0) or 0
    if hs == as_:
        return "draw"
    if is_home:
        return "win" if hs > as_ else "loss"
    return "win" if as_ > hs else "loss"


def _result_color(outcome):
    return {"win": GREEN, "draw": YELLOW, "loss": RED}.get(outcome, GRAY)


def _result_label(outcome):
    return {"win": "V", "draw": "E", "loss": "D"}.get(outcome, "?")


def _is_fortaleza_home(row):
    return "fortaleza" in str(row.get("home_team", "")).lower()


# ── helpers de desenho ────────────────────────────────────────────────────────
def _new_fig():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _add_logo_footer(fig):
    if not HAS_PIL or not os.path.exists(AVATAR):
        return
    try:
        img = Image.open(AVATAR).convert("RGBA").resize((60, 60), Image.LANCZOS)
        ax2 = fig.add_axes([0.05, 0.025, 0.07, 0.07])
        ax2.imshow(np.array(img))
        ax2.axis("off")
    except Exception:
        pass


def _label(ax, x, y, text, color=GRAY, size=8, weight="normal", family=FONT_BODY,
           ha="center", va="center", alpha=1.0):
    ax.text(x, y, text, color=color, fontsize=size, fontweight=weight,
            fontfamily=family, ha=ha, va=va, transform=ax.transAxes, alpha=alpha)


def _hline(ax, y, x0=0.07, x1=0.93, color=YELLOW, lw=0.7, alpha=0.35):
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw, alpha=alpha,
            transform=ax.transAxes)


def _badge(ax, x, y, text, bg=YELLOW, fg="#111111", size=8.5, pad=0.3):
    ax.text(x, y, text, color=fg, fontsize=size, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            bbox=dict(boxstyle=f"round,pad={pad}", facecolor=bg,
                      edgecolor="none", alpha=0.95),
            transform=ax.transAxes)


def _footer(ax):
    ax.text(0.84, 0.038, "SofaScore · @SportRecifeLab",
            color=DGRAY, fontsize=7, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes)


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  OK {path}")


def _top_bar(ax, label):
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003,
                                   facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, label,
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)


# ─── Card 01 — COVER ──────────────────────────────────────────────────────────
def card_cover(matches):
    fig, ax = _new_fig()

    # Faixa diagonal decorativa
    poly = plt.Polygon([[0, 0.56], [0, 0.68], [0.50, 0.68], [0.60, 0.56]],
                       closed=True, facecolor=FORD, alpha=0.08, zorder=1)
    ax.add_patch(poly)

    _top_bar(ax, "COPA DO NORDESTE 2026  ·  SEMIFINAL")

    ax.text(0.50, 0.840, "RAIO-X",
            color=YELLOW, fontsize=96, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4,
            path_effects=[pe.withStroke(linewidth=4, foreground=BG)])

    ax.text(0.50, 0.728, "FORTALEZA EC",
            color=WHITE, fontsize=40, fontweight="bold",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4)

    _hline(ax, 0.692, alpha=0.55)

    _label(ax, 0.50, 0.650, "SPORT JOGA COMO VISITANTE — ARENA CASTELÃO",
           color=LGRAY, size=12, weight="bold", family=FONT_TITLE)

    # Escudo Fortaleza
    logo = _load_logo(FORTALEZA_ID, size=220)
    if logo:
        logo_ax = fig.add_axes([0.04, 0.17, 0.28, 0.28])
        logo_ax.imshow(np.array(logo))
        logo_ax.set_facecolor(BG)
        logo_ax.axis("off")
    else:
        # fallback geométrico
        ax.add_patch(patches.Circle((0.195, 0.340), 0.13,
                                    facecolor=FORD, edgecolor=YELLOW,
                                    linewidth=2, alpha=0.9,
                                    transform=ax.transAxes, zorder=3))
        ax.text(0.195, 0.340, "FEC", color=WHITE, fontsize=22,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    # Stats resumo da campanha 2026
    completed = matches[matches["status"] == "completed"] if not matches.empty else pd.DataFrame()
    if not completed.empty:
        outcomes = completed.apply(_team_outcome, axis=1)
        w = (outcomes == "win").sum()
        d = (outcomes == "draw").sum()
        l = (outcomes == "loss").sum()
        gf = completed.apply(lambda r: r["home_score"] if _is_fortaleza_home(r) else r["away_score"], axis=1).sum()
        ga = completed.apply(lambda r: r["away_score"] if _is_fortaleza_home(r) else r["home_score"], axis=1).sum()
        pts = w * 3 + d
        aprov = pts / (len(completed) * 3) * 100
        camp_str = f"{w}V  {d}E  {l}D"
        saldo_str = f"{int(gf-ga):+d}"
        aprov_str = f"{aprov:.0f}%"
    else:
        camp_str, saldo_str, aprov_str = "—", "—", "—"

    cover_stats = [
        (camp_str,  "CAMPANHA 2026",   YELLOW),
        (saldo_str, "SALDO DE GOLS",   GREEN if saldo_str.startswith("+") else RED),
        (aprov_str, "APROVEITAMENTO",  LGRAY),
    ]
    sx, sy_start, row_gap = 0.72, 0.570, 0.120
    for k, (val, lbl, color) in enumerate(cover_stats):
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
    _add_logo_footer(fig)
    _save(fig, "01_cover.png")


# ─── Card 02 — CAMPANHA GERAL ─────────────────────────────────────────────────
def card_campanha(matches):
    fig, ax = _new_fig()
    _top_bar(ax, "TEMPORADA 2026  ·  TODAS AS COMPETIÇÕES")

    _label(ax, 0.50, 0.870, "FORTALEZA EC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    completed = matches[matches["status"] == "completed"] if not matches.empty else pd.DataFrame()
    n = len(completed)
    _label(ax, 0.50, 0.828, f"{n} PARTIDAS DISPUTADAS", color=GRAY, size=10)
    _hline(ax, 0.805)

    if not completed.empty:
        outcomes = completed.apply(_team_outcome, axis=1)
        w = int((outcomes == "win").sum())
        d = int((outcomes == "draw").sum())
        l = int((outcomes == "loss").sum())
        gf = int(completed.apply(lambda r: r["home_score"] if _is_fortaleza_home(r) else r["away_score"], axis=1).fillna(0).sum())
        ga = int(completed.apply(lambda r: r["away_score"] if _is_fortaleza_home(r) else r["home_score"], axis=1).fillna(0).sum())
        pts = w * 3 + d
        aprov = pts / (n * 3) * 100 if n > 0 else 0
    else:
        w = d = l = gf = ga = pts = 0
        aprov = 0

    results = [(w, "VITÓRIAS", GREEN), (d, "EMPATES", YELLOW), (l, "DERROTAS", RED)]
    for (num, lbl, color), x in zip(results, [0.20, 0.50, 0.80]):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.60), 0.26, 0.185,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=color,
                                    linewidth=2.0, zorder=2))
        ax.text(x, 0.720, str(num), color=color, fontsize=56,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.622, lbl, color=LGRAY, fontsize=9,
                fontfamily=FONT_BODY, fontweight="bold",
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    _hline(ax, 0.590)
    _label(ax, 0.50, 0.558, f"{pts} pontos  ·  {aprov:.0f}% de aproveitamento",
           color=LGRAY, size=10.5, weight="bold")
    _hline(ax, 0.535, alpha=0.25)

    saldo = gf - ga
    gol_data = [
        ("GOLS\nMARCADOS", str(gf), YELLOW),
        ("SALDO\nDE GOLS",  f"{saldo:+d}", GREEN if saldo >= 0 else RED),
        ("GOLS\nSOFRIDOS",  str(ga), RED),
    ]
    for (lbl, val, color), x in zip(gol_data, [0.20, 0.50, 0.80]):
        ax.text(x, 0.465, val, color=color, fontsize=40,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.398, lbl, color=GRAY, fontsize=8.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4, linespacing=1.4)

    _hline(ax, 0.365, alpha=0.25)

    # Competições breakdown
    if not matches.empty and "competition_name" in matches.columns:
        comp_counts = (
            matches[matches["status"] == "completed"]
            .groupby("competition_name").size()
            .sort_values(ascending=False)
            .head(4)
        )
        comp_list = [(c, f"{v} jogo{'s' if v > 1 else ''}") for c, v in comp_counts.items()]
    else:
        comp_list = [("—", "—")] * 4

    while len(comp_list) < 4:
        comp_list.append(("", ""))

    cx_list = [0.16, 0.39, 0.62, 0.84]
    for (comp, nj), x in zip(comp_list[:4], cx_list):
        ax.text(x, 0.330, nj, color=YELLOW, fontsize=14,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        # Shorten long competition names
        short = comp.replace("Copa do ", "C. ").replace("Campeonato ", "Camp. ")
        short = short[:20] if len(short) > 20 else short
        ax.text(x, 0.293, short, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_logo_footer(fig)
    _save(fig, "02_campanha.png")


# ─── Card 03 — FORTALEZA COMO MANDANTE ────────────────────────────────────────
def card_mandante(matches, stats):
    fig, ax = _new_fig()
    _top_bar(ax, "FORTALEZA COMO MANDANTE  ·  2026")

    _label(ax, 0.50, 0.876, "FORTALEZA EC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.836, "Sport joga na Arena Castelão — como o Leão do Pici se sai em casa?",
           color=GRAY, size=9.5)
    _hline(ax, 0.812)

    # Home matches only
    if not matches.empty:
        home_m = matches[
            matches.apply(_is_fortaleza_home, axis=1) &
            (matches["status"] == "completed")
        ]
    else:
        home_m = pd.DataFrame()

    n_home = len(home_m)
    if n_home > 0:
        outcomes = home_m.apply(_team_outcome, axis=1)
        w = int((outcomes == "win").sum())
        d = int((outcomes == "draw").sum())
        l = int((outcomes == "loss").sum())
        gf = int(home_m["home_score"].fillna(0).sum())
        ga = int(home_m["away_score"].fillna(0).sum())
        pts = w * 3 + d
        aprov = pts / (n_home * 3) * 100
    else:
        w = d = l = gf = ga = pts = 0
        aprov = 0

    aprov_color = GREEN if aprov >= 60 else (YELLOW if aprov >= 45 else RED)
    ax.text(0.50, 0.738, f"{aprov:.0f}%", color=aprov_color, fontsize=80,
            fontweight="black", fontfamily=FONT_TITLE,
            ha="center", va="center", transform=ax.transAxes, zorder=4)
    _label(ax, 0.50, 0.683,
           f"APROVEITAMENTO COMO MANDANTE  ·  {n_home} JOGOS",
           color=GRAY, size=9)
    _hline(ax, 0.660, alpha=0.4)

    vxs = [0.22, 0.50, 0.78]
    for (num, lbl, color), x in zip([(w, "VITÓRIAS", GREEN), (d, "EMPATES", YELLOW), (l, "DERROTAS", RED)], vxs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.570), 0.26, 0.082,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=color,
                                    linewidth=2.0, zorder=2))
        ax.text(x, 0.622, str(num), color=color, fontsize=38,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.582, lbl, color=LGRAY, fontsize=8,
                fontweight="bold", fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    _hline(ax, 0.558, alpha=0.3)
    saldo = gf - ga
    for (val, lbl, color), x in zip([
        (str(gf),         "GOLS MARCADOS", YELLOW),
        (f"{saldo:+d}",   "SALDO",         GREEN if saldo >= 0 else RED),
        (str(ga),         "GOLS SOFRIDOS", RED),
    ], vxs):
        ax.text(x, 0.508, val, color=color, fontsize=36,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.468, lbl, color=GRAY, fontsize=8.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.446, alpha=0.3)

    # xG em casa via stats — curated uses is_home + team_name
    if not stats.empty and "expected_goals" in stats.columns:
        if "is_home" in stats.columns and "team_name" in stats.columns:
            home_stats = stats[
                stats["team_name"].str.contains("ortaleza", case=False, na=False) &
                (stats["is_home"] == True)
            ]
        elif "home_team" in stats.columns:
            home_stats = stats[
                stats.apply(lambda r: "fortaleza" in str(r.get("home_team", "")).lower(), axis=1)
            ]
        else:
            home_stats = stats
        xg_home  = home_stats["expected_goals"].mean() if len(home_stats) > 0 else None
        xga_home = None
        # xGA: opponent's xG in home matches
        match_col = "match_id" if "match_id" in stats.columns else "match_code"
        if match_col in stats.columns and not home_stats.empty:
            mc = home_stats[match_col].unique()
            opp_stats = stats[
                stats[match_col].isin(mc) &
                ~stats.apply(lambda r: "fortaleza" in str(r.get("home_team", r.get("team_name", ""))).lower(), axis=1)
            ]
            xga_home = opp_stats["expected_goals"].mean() if len(opp_stats) > 0 else None
    else:
        xg_home = xga_home = None

    gm_j = gf / n_home if n_home else 0
    gs_j = ga / n_home if n_home else 0

    for (val, lbl), x in zip([
        (f"{gm_j:.1f}", "GOLS MARC/JOGO"),
        (f"{gs_j:.1f}", "GOLS SOF/JOGO"),
        (f"{aprov:.0f}%", "APROVEITAMENTO"),
    ], vxs):
        ax.text(x, 0.408, val, color=LGRAY, fontsize=24,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.374, lbl, color=GRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.350, alpha=0.3)

    xg_str  = f"{xg_home:.2f}"  if xg_home  is not None else "—"
    xga_str = f"{xga_home:.2f}" if xga_home is not None else "—"
    for (val, lbl, color), x in zip([
        (xg_str,  "xG MÉDIO / JOGO",   YELLOW),
        (xga_str, "xG SOFRIDO / JOGO", RED),
        (f"{gm_j:.1f}", "MÉDIAS GOL/J", LGRAY),
    ], vxs):
        ax.text(x, 0.310, val, color=color, fontsize=24,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.276, lbl, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.252, alpha=0.2)

    # Callout
    callout_color = GREEN2 if aprov >= 60 else RED
    callout_txt = (
        f"Forte em casa: {aprov:.0f}% de aproveitamento em {n_home} jogos"
        if aprov >= 50
        else f"Vulnerável em casa: só {aprov:.0f}% de aproveitamento em {n_home} jogos"
    )
    ax.add_patch(FancyBboxPatch((0.07, 0.155), 0.86, 0.086,
                                boxstyle="round,pad=0.01",
                                facecolor=CARD2, edgecolor=callout_color,
                                linewidth=1.2, zorder=3))
    ax.text(0.50, 0.200, callout_txt,
            color=LGRAY, fontsize=9.5, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.168, f"Sport enfrenta {n_home} partidas em casa nas estatísticas do adversário",
            color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax)
    _add_logo_footer(fig)
    _save(fig, "03_mandante.png")


# ─── Card 04 — ÚLTIMOS 5 JOGOS ────────────────────────────────────────────────
def card_ultimos5(matches):
    fig, ax = _new_fig()
    _top_bar(ax, "FORMA RECENTE  ·  ÚLTIMOS 5 JOGOS")

    _label(ax, 0.50, 0.875, "FORTALEZA EC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _hline(ax, 0.845)

    if not matches.empty:
        completed = matches[matches["status"] == "completed"].copy()
        completed["match_date_utc"] = pd.to_datetime(completed["match_date_utc"], utc=True, errors="coerce")
        completed = completed.sort_values("match_date_utc", ascending=False).head(5)
        games = completed.to_dict("records")
    else:
        games = []

    row_h  = 0.130
    box_h  = 0.108
    half_h = box_h / 2
    y_start = 0.806

    for i, g in enumerate(games[:5]):
        y     = y_start - i * row_h
        y_bot = y - half_h
        outcome = _team_outcome(g)
        oc = _result_color(outcome)
        ol = _result_label(outcome)

        row_bg = CARD if i % 2 == 0 else CARD2
        ax.add_patch(FancyBboxPatch((0.07, y_bot), 0.86, box_h,
                                    boxstyle="round,pad=0.005",
                                    facecolor=row_bg, edgecolor="none", zorder=2))
        ax.add_patch(patches.Rectangle((0.07, y_bot), 0.012, box_h,
                                       facecolor=oc, zorder=3))
        _badge(ax, 0.906, y, ol, bg=oc,
               fg=("#111111" if outcome == "draw" else WHITE), size=11, pad=0.38)

        date_y = y + half_h * 0.38
        comp_y = y - half_h * 0.40

        raw_date = str(g.get("match_date_utc", ""))[:10]
        try:
            dt = datetime.datetime.strptime(raw_date, "%Y-%m-%d")
            date_str = dt.strftime("%d/%m")
        except Exception:
            date_str = raw_date

        comp_name = str(g.get("competition_name", ""))
        comp_short = comp_name.replace("Copa do ", "C.").replace("Campeonato ", "")[:14]
        rnd = g.get("competition_round")
        if rnd:
            comp_short += f" R{int(rnd)}"

        ax.text(0.118, date_y, date_str, color=LGRAY, fontsize=9,
                fontweight="bold", fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.118, comp_y, comp_short, color=DGRAY, fontsize=7,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        home = str(g.get("home_team", ""))
        away = str(g.get("away_team", ""))
        hs   = int(g.get("home_score") or 0)
        as_  = int(g.get("away_score") or 0)
        fort_home = _is_fortaleza_home(g)
        h_color = YELLOW if fort_home else LGRAY
        a_color = LGRAY if fort_home else YELLOW
        h_w     = "black" if fort_home else "normal"
        a_w     = "normal" if fort_home else "black"

        # Truncate long names
        home_s = home[:14] if len(home) > 14 else home
        away_s = away[:14] if len(away) > 14 else away

        ax.text(0.345, y, home_s, color=h_color, fontsize=10.5,
                fontweight=h_w, fontfamily=FONT_BODY,
                ha="right", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.500, y, f"{hs} – {as_}", color=WHITE,
                fontsize=14, fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.655, y, away_s, color=a_color, fontsize=10.5,
                fontweight=a_w, fontfamily=FONT_BODY,
                ha="left", va="center", transform=ax.transAxes, zorder=4)

    # Forma pills
    last_y = y_start - (min(len(games), 5) - 1) * row_h - half_h
    hline_y = last_y - 0.030
    pills_y = hline_y - 0.048

    _hline(ax, hline_y, alpha=0.3)
    _label(ax, 0.50, hline_y - 0.018, "FORMA NOS ÚLTIMOS 5:", color=GRAY, size=9)

    pill_xs = [0.32, 0.41, 0.50, 0.59, 0.68]
    for i, g in enumerate(games[:5]):
        outcome = _team_outcome(g)
        pc = _result_color(outcome)
        pl = _result_label(outcome)
        px = pill_xs[i]
        ax.add_patch(patches.Circle((px, pills_y), 0.030,
                                    facecolor=pc, alpha=0.20,
                                    transform=ax.transAxes, zorder=3))
        ax.text(px, pills_y, pl, color=pc, fontsize=13,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_logo_footer(fig)
    _save(fig, "04_ultimos5.png")


# ─── Card 05 — ANÁLISE xG ─────────────────────────────────────────────────────
def card_xg(matches, stats):
    fig, ax = _new_fig()
    _top_bar(ax, "ANÁLISE OFENSIVA E xG  ·  2026")

    _label(ax, 0.50, 0.880, "FORTALEZA EC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)

    n_completed = len(matches[matches["status"] == "completed"]) if not matches.empty else 0
    _label(ax, 0.50, 0.840, f"{n_completed} jogos — todas as competições",
           color=GRAY, size=9.5)
    _hline(ax, 0.815)

    # Compute from stats — find Fortaleza's own rows
    if not stats.empty and "expected_goals" in stats.columns:
        # Identify Fortaleza rows
        fort_col = None
        for col in ["team_name", "home_team"]:
            if col in stats.columns:
                fort_col = col
                break
        if fort_col:
            fort_stats = stats[stats[fort_col].str.contains("ortaleza", case=False, na=False)]
        else:
            fort_stats = stats

        xg_med    = fort_stats["expected_goals"].mean() if len(fort_stats) else None
        shots_med = fort_stats["shots_total"].mean() if "shots_total" in fort_stats.columns and len(fort_stats) else None
        if "shots_on_target_pct" in fort_stats.columns and len(fort_stats):
            sot_pct = fort_stats["shots_on_target_pct"].mean()
        elif "shots_on_target" in fort_stats.columns and "shots_total" in fort_stats.columns and len(fort_stats):
            tot = fort_stats["shots_total"].sum()
            sot_pct = (fort_stats["shots_on_target"].sum() / tot * 100) if tot else None
        else:
            sot_pct = None
        poss_med  = fort_stats["possession"].mean() if "possession" in fort_stats.columns and len(fort_stats) else None

        # xGA: opponent rows in same matches
        match_col = "match_id" if "match_id" in stats.columns else "match_code"
        if match_col in stats.columns and fort_col:
            opp_stats = stats[~stats[fort_col].str.contains("ortaleza", case=False, na=False)]
            mc_fort = fort_stats[match_col].unique() if match_col in fort_stats.columns else []
            opp_in_fort = opp_stats[opp_stats[match_col].isin(mc_fort)] if len(mc_fort) else opp_stats
            xga_med = opp_in_fort["expected_goals"].mean() if len(opp_in_fort) else None
        else:
            xga_med = None
    else:
        xg_med = xga_med = shots_med = sot_pct = poss_med = None

    def fmt(v, dec=2):
        return f"{v:.{dec}f}" if v is not None else "—"

    poss_str = f"{poss_med:.0f}%" if poss_med is not None else "—"
    metrics_top = [
        ("POSSE MÉDIA",     poss_str,        YELLOW, "controla o jogo?"),
        ("xG / JOGO",       fmt(xg_med),     RED,    "qualidade das chances"),
        ("PRECISÃO CHUTES", f"{sot_pct:.0f}%" if sot_pct else "—", LGRAY, "eficiência ofensiva"),
    ]
    for (lbl, val, color, sub), x in zip(metrics_top, [0.20, 0.50, 0.80]):
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

    # Análise narrativa baseada nos dados
    if xg_med is not None and poss_med is not None:
        if xg_med > 1.4:
            headline = "ATAQUE PRODUTIVO — CRIA MUITAS CHANCES"
            body = f"Com {fmt(xg_med)} xG/jogo, o Fortaleza é um dos ataques mais perigosos do nordeste em 2026."
        elif xg_med < 0.9:
            headline = "ATAQUE ABAIXO DO ESPERADO"
            body = f"Apenas {fmt(xg_med)} xG/jogo indica criatividade limitada — Sport pode explorar pressão alta."
        else:
            headline = "PERFIL EQUILIBRADO — ATAQUE REGULAR"
            body = f"{fmt(xg_med)} xG/jogo com {poss_str} de posse. Time consistente, sem grandes excessos."
    else:
        headline = "ANÁLISE OFENSIVA"
        body = "Dados insuficientes para análise completa."

    _label(ax, 0.50, 0.617, headline, color=LGRAY, size=12, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.583, body, color=GRAY, size=9.5)
    _hline(ax, 0.550, alpha=0.25)

    _label(ax, 0.50, 0.518, "CONTEXTO DEFENSIVO", color=GRAY, size=8.5, weight="bold")
    for (lbl, val, color), x in zip([
        ("xGA SOFRIDO / JOGO",    fmt(xga_med),                  RED),
        ("CHUTES SOFRIDOS / JOGO", fmt(stats["shots_total"].mean() if not stats.empty and "shots_total" in stats.columns else None), RED),
        ("xG SALDO / JOGO",       fmt((xg_med - xga_med) if xg_med and xga_med else None), LGRAY),
    ], [0.22, 0.50, 0.78]):
        ax.text(x, 0.472, val, color=color, fontsize=24,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(x, 0.437, lbl, color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.410, alpha=0.25)

    # Callout — oportunidade para o Sport
    xg_diff = (xg_med - xga_med) if xg_med and xga_med else None
    if xg_diff is not None and xg_diff < 0.1:
        callout_head = "ATENÇÃO: EQUILÍBRIO OFENSIVO-DEFENSIVO"
        callout_body = f"Margem xG vs xGA de apenas {fmt(xg_diff)} — jogo deve ser decidido por detalhes"
        callout_color = YELLOW
    elif xga_med is not None and xga_med > 1.3:
        callout_head = "OPORTUNIDADE PARA O SPORT"
        callout_body = f"Fortaleza cede {fmt(xga_med)} xG/jogo — pressão ofensiva do Leão pode ser decisiva"
        callout_color = GREEN
    else:
        callout_head = "CONTEXTO DO CONFRONTO"
        callout_body = "Copa do Nordeste — Sport precisa de resultado fora de casa"
        callout_color = LGRAY

    ax.add_patch(FancyBboxPatch((0.07, 0.285), 0.86, 0.103,
                                boxstyle="round,pad=0.01",
                                facecolor="#001a08", edgecolor=callout_color,
                                linewidth=1.5, zorder=3))
    ax.text(0.50, 0.340, callout_head, color=callout_color, fontsize=11.5,
            fontweight="black", fontfamily=FONT_TITLE,
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.298, callout_body, color=LGRAY, fontsize=8.8,
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)

    _footer(ax)
    _add_logo_footer(fig)
    _save(fig, "05_xg.png")


# ─── Card 06 — JOGADORES DESTAQUE ────────────────────────────────────────────
def card_jogadores(players, matches):
    fig, ax = _new_fig()
    _top_bar(ax, "FIQUE DE OLHO  ·  DESTAQUES 2026")

    _label(ax, 0.50, 0.875, "FORTALEZA EC",
           color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _hline(ax, 0.845)

    # Derive top players from player stats
    player_list = []
    if not players.empty:
        fort_players = players[
            players.apply(lambda r: "fortaleza" in str(r.get("home_team", r.get("team_name", ""))).lower(), axis=1)
        ] if any(c in players.columns for c in ["home_team", "team_name"]) else players

        if "player_name" in fort_players.columns:
            agg_cols = [c for c in ["minutes_played", "rating", "total_shots", "goal_assist", "total_pass"] if c in fort_players.columns]
            g2 = fort_players.groupby("player_name")[agg_cols].mean().reset_index()
            g2["games"] = fort_players.groupby("player_name").size().values

            # Top by rating — try min 3 games, fall back to 2 then 1
            for min_g in (3, 2, 1):
                g_filt = g2[g2["games"] >= min_g]
                if len(g_filt) >= 3:
                    g2 = g_filt.sort_values("rating", ascending=False) if "rating" in g2.columns else g_filt
                    break
            else:
                g2 = g2.sort_values("rating", ascending=False) if "rating" in g2.columns else g2

            for _, row in g2.head(3).iterrows():
                name = str(row["player_name"])
                parts = name.split()
                n1 = parts[0].upper() if parts else name.upper()
                n2 = parts[-1].upper() if len(parts) > 1 else ""
                games = int(row.get("games", 0))
                rating = row.get("rating", 0)
                shots  = row.get("total_shots", 0)
                assists = row.get("goal_assist", 0)
                passes = row.get("total_pass", 0)
                player_list.append({
                    "name1": n1, "name2": n2,
                    "pos": "—",
                    "jersey": "—",
                    "rating": f"{rating:.2f}",
                    "stats": [
                        ("JOGOS",         str(games)),
                        ("CHUTES / JOGO", f"{shots:.1f}"),
                        ("PASSES / JOGO", f"{passes:.0f}"),
                    ],
                    "label": "DESTAQUE",
                    "label_color": YELLOW,
                    "border": YELLOW,
                })

    # Pad to 3 entries
    placeholder = {"name1": "—", "name2": "", "pos": "—", "jersey": "—",
                   "rating": "—", "stats": [("—", "—"), ("—", "—"), ("—", "—")],
                   "label": "—", "label_color": GRAY, "border": DGRAY}
    while len(player_list) < 3:
        player_list.append(placeholder)

    card_xs  = [0.20, 0.50, 0.80]
    card_w   = 0.270
    card_bot = 0.140
    card_top = 0.800
    card_h   = card_top - card_bot

    border_colors = [YELLOW, FORD, LGRAY]

    for k, (p, cx) in enumerate(zip(player_list[:3], card_xs)):
        border = border_colors[k]
        p["border"] = border
        x0 = cx - card_w / 2
        x1 = cx + card_w / 2

        ax.add_patch(FancyBboxPatch((x0, card_bot), card_w, card_h,
                                    boxstyle="round,pad=0.01",
                                    facecolor=CARD2, edgecolor=border,
                                    linewidth=1.5, zorder=2))
        ax.add_patch(patches.Rectangle((x0 + 0.005, card_top - 0.038),
                                       card_w - 0.010, 0.033,
                                       facecolor=border, alpha=0.18, zorder=3))
        _badge(ax, cx, card_top - 0.022, f"#{p['jersey']}",
               bg=border, fg=WHITE if border != YELLOW else "#111111",
               size=9, pad=0.30)

        ax.text(cx, card_top - 0.075, p["name1"], color=WHITE, fontsize=15,
                fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(cx, card_top - 0.108, p["name2"], color=border, fontsize=15,
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
                                    facecolor="#111111", edgecolor=border,
                                    linewidth=0.8, zorder=3))
        ax.text(cx, r_center, f"RATING  {p['rating']}",
                color=border, fontsize=9, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(cx, r_center - 0.032, "media por jogo",
                color=DGRAY, fontsize=6.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

        sep2 = r_center - 0.052
        ax.plot([x0 + 0.018, x1 - 0.018], [sep2, sep2],
                color=DGRAY, linewidth=0.5, alpha=0.5,
                transform=ax.transAxes, zorder=3)

        stat_gap = 0.092
        stat_top = sep2 - 0.020
        for j, (lbl, val) in enumerate(p["stats"][:3]):
            val_y = stat_top - j * stat_gap
            lbl_y = val_y - 0.030
            ax.text(cx, val_y, val, color=WHITE, fontsize=16,
                    fontweight="black", fontfamily=FONT_TITLE,
                    ha="center", va="center", transform=ax.transAxes, zorder=4)
            ax.text(cx, lbl_y, lbl, color=GRAY, fontsize=7,
                    fontfamily=FONT_BODY, ha="center", va="center",
                    transform=ax.transAxes, zorder=4)
            if j < 2:
                div_y = lbl_y - 0.018
                ax.plot([x0 + 0.018, x1 - 0.018], [div_y, div_y],
                        color=DGRAY, linewidth=0.4, alpha=0.4,
                        transform=ax.transAxes, zorder=3)

        badge_y = card_bot + 0.040
        ax.add_patch(FancyBboxPatch((x0 + 0.015, badge_y - 0.020),
                                    card_w - 0.030, 0.038,
                                    boxstyle="round,pad=0.006",
                                    facecolor="#111111", edgecolor=border,
                                    linewidth=0.8, alpha=0.9, zorder=3))
        ax.text(cx, badge_y, p["label"],
                color=p["label_color"], fontsize=8, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax)
    _add_logo_footer(fig)
    _save(fig, "06_jogadores.png")


# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    os.chdir(BASE)
    print("Carregando dados do Fortaleza...")
    matches, stats, players = _load_data()
    print(f"  matches: {len(matches)} | stats: {len(stats)} | players: {len(players)}")

    print("\nGerando cards — Fortaleza EC | Copa do Nordeste 2026")
    card_cover(matches)
    card_campanha(matches)
    card_mandante(matches, stats)
    card_ultimos5(matches)
    card_xg(matches, stats)
    card_jogadores(players, matches)

    print(f"\nPronto. Cards em: {OUT_DIR}")
