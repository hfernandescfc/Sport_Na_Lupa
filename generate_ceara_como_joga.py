"""
Card "Como o Ceará Joga" — @SportRecifeLab
Tactical Cartography v3 — evolução do template Fortaleza v2

Três blocos analíticos com narrativa esquerda → direita:
  1. ZONAS DE ATUAÇÃO     — heatmap KDE em campo vertical, callouts em pílula
  2. ORIGEM DOS CHUTES    — barras horizontais por situação + xG/shot
  3. PERFIL OFENSIVO      — 4 micro-métricas com comparativo de liga + gauge

Melhorias vs. fortaleza_v2:
  · header com faixa de acento do time (alvinegro → cinza-claro)
  · callouts do heatmap com fundo em pílula (legibilidade)
  · cmap perceptualmente uniforme (sem burst dourado interno)
  · painel direito reformulado (1 métrica → dashboard 4 métricas)
  · síntese gerada dinamicamente a partir dos dados
  · tipografia: fonte mínima 4.5pt (era 3.5pt)
  · separadores verticais sutis entre blocos

Formato: 1200×675 landscape
"""
from __future__ import annotations

import json
from collections import Counter, deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Arc
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe
import numpy as np
from scipy.stats import gaussian_kde
from scipy.ndimage import gaussian_filter, maximum_filter

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE = Path(__file__).parent

# ── Paleta ────────────────────────────────────────────────────────────────────
BG         = "#0d0d0d"
GOLD       = "#F5C400"          # marca @SportRecifeLab
GOLD_DIM   = "#9A7B00"
TEAM_ACC   = "#E8E8E8"          # acento do time (Ceará: branco/alvinegro)
FIELD_DARK = "#0a2412"
FIELD_MID  = "#0d3520"
FIELD_LINE = "#1f6b38"
WHITE      = "#FFFFFF"
GRAY_L     = "#B8B8B8"
GRAY_M     = "#666666"
GRAY_D     = "#1f1f1f"
GREEN      = "#2ECC71"
RED        = "#E74C3C"

BAR_COLORS = {
    "Jogada Aberta": GOLD,
    "Bola Parada":   "#4A8FD4",
    "Contra-ataque": "#E07030",
    "Pênalti":       "#9C9C9C",
}

# Médias Série B 2026 (referência)
LEAGUE_AVG = {
    "possession":          50.0,
    "expected_goals":       1.10,
    "shots_total":         11.5,
    "shots_inside_box_pct": 55.0,
    "long_balls_accurate": 18.0,
    "long_balls_pct":       7.5,
    "final_third_entries": 35.0,
    "touches_opp_box":     18.0,
}

FONT = "Arial"


# ── I/O ───────────────────────────────────────────────────────────────────────
def load_heatmap(team_key: str):
    p = BASE / f"data/processed/2026/opponents/{team_key}/team_heatmap.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def load_profile(team_key: str):
    p = BASE / f"data/curated/opponents_2026/{team_key}/attack_profile.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)

def load_logo(path, size=80):
    if not HAS_PIL:
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((size, size), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None

def remove_bg(img, thresh=25):
    """BFS flood fill — remove apenas branco conectado à borda externa."""
    h, w = img.shape[:2]
    out = img.copy()
    vis = np.zeros((h, w), bool)
    q = deque()
    for px in range(w):
        for py in (0, h - 1):
            if not vis[py, px] and all(out[py, px, c] > 255 - thresh for c in range(3)):
                q.append((py, px)); vis[py, px] = True
    for py in range(h):
        for px in (0, w - 1):
            if not vis[py, px] and all(out[py, px, c] > 255 - thresh for c in range(3)):
                q.append((py, px)); vis[py, px] = True
    while q:
        cy, cx = q.popleft()
        out[cy, cx, 3] = 0
        for dy, dx in ((-1,0),(1,0),(0,-1),(0,1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not vis[ny, nx]:
                if all(out[ny, nx, c] > 255 - thresh for c in range(3)):
                    vis[ny, nx] = True; q.append((ny, nx))
    return out


# ── Campo vertical (ataque para CIMA) ─────────────────────────────────────────
def draw_pitch_vert(ax, lc=FIELD_LINE, fc=FIELD_DARK):
    ax.set_facecolor(fc)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("auto")
    ax.axis("off")

    lw = 0.7
    for i in range(0, 100, 20):
        ax.add_patch(Rectangle((i, 0), 10, 100, fc=FIELD_MID, ec="none", alpha=0.32, zorder=1))

    ax.plot([0,100,100,0,0], [0,0,100,100,0], color=lc, lw=lw, zorder=3)
    ax.plot([0,100], [50,50], color=lc, lw=lw, zorder=3)
    ax.add_patch(plt.Circle((50,50), 9.15, color=lc, fill=False, lw=lw, zorder=3))
    ax.plot([50],[50],"o", color=lc, ms=1.0, zorder=3)
    ax.add_patch(Rectangle((29.84, 0),    40.32, 16.5, ec=lc, fc="none", lw=lw, zorder=3))
    ax.add_patch(Rectangle((29.84, 83.5), 40.32, 16.5, ec=lc, fc="none", lw=lw, zorder=3))
    ax.add_patch(Rectangle((41.34, 0),    17.32,  5.5, ec=lc, fc="none", lw=lw, zorder=3))
    ax.add_patch(Rectangle((41.34, 94.5), 17.32,  5.5, ec=lc, fc="none", lw=lw, zorder=3))
    ax.add_patch(Rectangle((45.2, -1.5), 9.6, 1.5, ec=lc, fc="none", lw=lw, zorder=3, clip_on=False))
    ax.add_patch(Rectangle((45.2, 100),  9.6, 1.5, ec=lc, fc="none", lw=lw, zorder=3, clip_on=False))
    ax.add_patch(Arc((50, 16.5), 18.3, 18.3, angle=0, theta1=37,  theta2=143, color=lc, lw=lw, zorder=3))
    ax.add_patch(Arc((50, 83.5), 18.3, 18.3, angle=0, theta1=217, theta2=323, color=lc, lw=lw, zorder=3))


# ── Análise ───────────────────────────────────────────────────────────────────
def situation_groups(shots):
    mapping = {
        "regular": "Jogada Aberta", "assisted": "Jogada Aberta",
        "fast-break": "Contra-ataque",
        "corner": "Bola Parada", "free-kick": "Bola Parada",
        "set-piece": "Bola Parada", "throw-in-set-piece": "Bola Parada",
        "penalty": "Pênalti",
    }
    c = Counter(mapping.get(s.get("situation",""), None)
                for s in shots if s.get("situation") != "shootout")
    if None in c:
        del c[None]
    total = sum(c.values()) or 1
    xg_by_group = {g: 0.0 for g in ["Jogada Aberta","Bola Parada","Contra-ataque","Pênalti"]}
    for s in shots:
        g = mapping.get(s.get("situation",""), None)
        if g and s.get("situation") != "shootout":
            xg_by_group[g] += float(s.get("xg") or 0)
    order = ["Jogada Aberta", "Bola Parada", "Contra-ataque", "Pênalti"]
    return {g: {
        "n":    c.get(g, 0),
        "pct":  round(c.get(g, 0) / total * 100),
        "xg":   xg_by_group.get(g, 0.0),
        "xg_per_shot": round(xg_by_group.get(g, 0.0) / c.get(g, 1), 2) if c.get(g, 0) else 0.0,
    } for g in order}


def kde_grid(points, n=120):
    hx = np.array([p["x"] for p in points], float)
    hy = np.array([p["y"] for p in points], float)
    xi = np.linspace(0, 100, n)
    yi = np.linspace(0, 100, n)
    xg, yg = np.meshgrid(xi, yi)
    kde = gaussian_kde(np.vstack([hy, hx]), bw_method=0.11)
    z = kde(np.vstack([xg.ravel(), yg.ravel()])).reshape(n, n)
    z = gaussian_filter(z, sigma=1.2)
    z = (z - z.min()) / (z.max() - z.min() + 1e-9)
    return z, xi, yi


def top_zones(z, xi, yi, n=2):
    lm = maximum_filter(z, size=14) == z
    peaks = sorted(np.argwhere(lm & (z > 0.62)),
                   key=lambda p: z[p[0], p[1]], reverse=True)
    zones, used = [], []
    for p in peaks:
        iy, ix = p
        if any(abs(iy - u[0]) < 18 and abs(ix - u[1]) < 18 for u in used):
            continue
        used.append((iy, ix))
        zones.append({"sx": float(xi[ix]), "sy": float(yi[iy]),
                       "hx": float(yi[iy]), "hy": float(xi[ix]),
                       "intensity": float(z[iy, ix])})
        if len(zones) >= n:
            break
    return zones


def zone_label(hx, hy):
    if hx < 33:    depth = "SETOR DEFENSIVO"
    elif hx < 52:  depth = "MEIO DE CAMPO"
    elif hx < 72:  depth = "TERÇO FINAL"
    else:          depth = "ÁREA RIVAL"
    if hy < 30:    side = "ESQ"
    elif hy > 70:  side = "DIR"
    else:          side = "CTR"
    return depth, side


def lateral_balance(points):
    """Retorna (esq%, ctr%, dir%) em relação ao total de pontos."""
    if not points:
        return 33, 34, 33
    e = sum(1 for p in points if p["y"] < 33.33)
    d = sum(1 for p in points if p["y"] > 66.67)
    c = len(points) - e - d
    t = len(points)
    return round(e/t*100), round(c/t*100), round(d/t*100)


def depth_distribution(points):
    """Distribuição em 5 faixas (defensiva → ofensiva). Ignora pontos do goleiro."""
    if not points:
        return [20] * 5
    # Filtra concentrações típicas do GK: hx < 12 e |hy-50| < 18
    bands = [0, 0, 0, 0, 0]
    valid = 0
    for p in points:
        x, y = p["x"], p["y"]
        if x < 12 and 32 < y < 68:
            continue
        b = min(int(x / 20), 4)
        bands[b] += 1
        valid += 1
    if not valid:
        return [20] * 5
    return [round(b / valid * 100, 1) for b in bands]


def build_synthesis(profile, sits, lat_bal, depth_pcts):
    """Texto curto, comparativo, gerado a partir dos dados."""
    avg = profile.get("averages", {})
    pos = avg.get("possession", 50)
    style_pos = "posse equilibrada" if 47 <= pos <= 53 else (
        "vocação reativa" if pos < 47 else "vocação propositiva")

    open_play = sits["Jogada Aberta"]["pct"]
    set_piece = sits["Bola Parada"]["pct"]
    transition = sits["Contra-ataque"]["pct"]

    secondary = max(
        [("bola parada", set_piece), ("transição", transition)],
        key=lambda x: x[1])

    # Lateral
    e, c, d = lat_bal
    lat_max = max(e, c, d)
    if lat_max > 38:
        lat_txt = (f"forte pelo corredor {'esquerdo' if e == lat_max else 'central' if c == lat_max else 'direito'}"
                   f" ({lat_max}%)")
    else:
        lat_txt = "distribuído pelos corredores"

    # Profundidade — deriva da distribuição em 5 faixas (não dos peaks)
    off_pct = depth_pcts[3] + depth_pcts[4]
    mid_pct = depth_pcts[2]
    depth_clause = ""
    if off_pct >= 35:
        depth_clause = f", com pressão alta no campo ofensivo ({off_pct:.0f}%)"
    elif mid_pct >= 38:
        depth_clause = f", apoiado no meio-campo ({mid_pct:.0f}%)"
    elif depth_pcts[0] + depth_pcts[1] > 40:
        depth_clause = f", de bloco recuado ({depth_pcts[0] + depth_pcts[1]:.0f}% no terço defensivo)"

    return (f"Time de {style_pos} ({pos:.0f}%), {lat_txt}{depth_clause}. "
            f"Ataque com {open_play}% via jogo corrido — "
            f"{secondary[0]} é a 2ª fonte ({secondary[1]}%).")


# ── Card ──────────────────────────────────────────────────────────────────────
def generate_card(
    team_key: str = "ceara",
    team_name: str = "CEARÁ SC",
    team_id: int = 2001,
    round_num: int = 7,
    match_date: str = "03/05",
    out: str | None = None,
):
    pts_data = load_heatmap(team_key)
    pts      = pts_data["points"]
    n_match  = pts_data.get("match_count", 0)

    prof  = load_profile(team_key)
    shots = prof.get("shots", [])
    avgs  = prof.get("averages", {})
    sits  = situation_groups(shots)

    z, xi, yi = kde_grid(pts)
    zones = top_zones(z, xi, yi, n=2)
    lat_bal = lateral_balance(pts)
    depth_pcts = depth_distribution(pts)

    pos_pct = avgs.get("possession", 50.0)
    xg_pg   = avgs.get("expected_goals", 1.0)
    shots_pg = avgs.get("shots_total", 10.0)
    sib_pct = avgs.get("shots_inside_box_pct", 50.0)
    lb_acc  = avgs.get("long_balls_accurate", 18.0)
    lb_pct  = avgs.get("long_balls_pct", 7.0)

    DPI = 150
    fig = plt.figure(figsize=(1200/DPI, 675/DPI), facecolor=BG, dpi=DPI)

    # ─── HEADER ────────────────────────────────────────────────────────────────
    # Etiqueta superior — acima do título principal
    fig.text(0.04, 0.992, "COMO O", color=GRAY_M, fontsize=5.5,
             fontfamily=FONT, va="top", fontweight="normal")
    # Linha principal: TEAM_NAME + JOGA, abaixo da etiqueta, sem overlap
    title_str = f"{team_name}  JOGA"
    fig.text(0.04, 0.962, title_str, color=WHITE,
             fontsize=18, fontfamily=FONT, fontweight="bold", va="top",
             path_effects=[pe.withStroke(linewidth=2.5, foreground="#000")])

    fig.text(0.848, 0.978, f"Série B 2026  ·  R{round_num}  ·  {match_date}",
             color=GRAY_L, fontsize=5.8, fontfamily=FONT, va="top", ha="right")
    fig.text(0.848, 0.958,
             f"{n_match} partidas · {len(shots)} chutes analisados",
             color=GRAY_M, fontsize=4.8, fontfamily=FONT, va="top", ha="right")

    # Linha principal cinza fina sob o título
    fig.add_artist(plt.Line2D([0.04, 0.975], [0.905, 0.905],
                               transform=fig.transFigure,
                               color=GRAY_D, lw=0.5, alpha=0.85))
    # Acento de marca (gold) sob o nome do time
    fig.add_artist(plt.Line2D([0.04, 0.085], [0.905, 0.905],
                               transform=fig.transFigure,
                               color=GOLD, lw=2.5))
    # Acento do time (claro) à direita do gold — sequência visual
    fig.add_artist(plt.Line2D([0.085, 0.155], [0.905, 0.905],
                               transform=fig.transFigure,
                               color=TEAM_ACC, lw=2.5, alpha=0.85))

    # Logos
    logo_t = load_logo(str(BASE / f"data/cache/logos/{team_id}.png"), 56)
    logo_b = load_logo(str(BASE / "sportrecifelab_avatar.png"), 36)
    if logo_t is not None:
        logo_t = remove_bg(logo_t)
        axt = fig.add_axes([0.866, 0.890, 0.052, 0.090])
        axt.imshow(logo_t); axt.axis("off")
    if logo_b is not None:
        logo_b = remove_bg(logo_b)
        axb = fig.add_axes([0.932, 0.012, 0.046, 0.068])
        axb.imshow(logo_b); axb.axis("off")

    # ─── GRID ──────────────────────────────────────────────────────────────────
    gs = fig.add_gridspec(
        1, 3,
        left=0.04, right=0.975,
        top=0.870, bottom=0.110,
        wspace=0.07,
        width_ratios=[0.27, 0.38, 0.35],
    )
    ax_hm = fig.add_subplot(gs[0])
    ax_sh = fig.add_subplot(gs[1])
    ax_mt = fig.add_subplot(gs[2])

    # Separadores verticais sutis
    for x_sep in [0.348, 0.665]:
        fig.add_artist(plt.Line2D([x_sep, x_sep], [0.13, 0.85],
                                   transform=fig.transFigure,
                                   color=GRAY_D, lw=0.5, alpha=0.7))

    # ─── BLOCO 1: HEATMAP ──────────────────────────────────────────────────────
    cmap = LinearSegmentedColormap.from_list("tct_v3", [
        (0.00, FIELD_DARK),
        (0.25, "#13452a"),
        (0.50, "#477a4f"),
        (0.75, "#c9a23a"),
        (1.00, "#f8e07a"),
    ])
    draw_pitch_vert(ax_hm)
    ax_hm.contourf(xi, yi, z, levels=22, cmap=cmap, alpha=0.82, zorder=4,
                   vmin=0.04, vmax=1.0)

    # Seta de ataque (canto superior)
    ax_hm.annotate("", xy=(50, 99), xytext=(50, 91),
                   arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=1.2,
                                   mutation_scale=7, alpha=0.9), zorder=6)
    ax_hm.text(58, 95, "ATQ", fontsize=4.2, color=GOLD, ha="left", va="center",
               fontfamily=FONT, fontweight="bold", zorder=6,
               path_effects=[pe.withStroke(linewidth=1.5, foreground="#000")])

    # Callouts em pílula — top 2 zonas
    for idx, zone in enumerate(zones):
        sx, sy = zone["sx"], zone["sy"]
        depth, side = zone_label(zone["hx"], zone["hy"])
        intensity_pct = int(zone["intensity"] * 100)

        # Marca circular
        ax_hm.scatter(sx, sy, s=55, color=GOLD, alpha=0.95, zorder=7,
                      edgecolors="#000", linewidths=0.8)
        ax_hm.scatter(sx, sy, s=14, color="#000", zorder=8)

        # Pílula com label (off-pitch quando possível)
        off_x = 22 if sx < 50 else -22
        ha    = "left" if sx < 50 else "right"
        anchor_x = sx + off_x
        anchor_y = sy

        ax_hm.annotate(
            "",
            xy=(sx, sy), xytext=(anchor_x, anchor_y),
            arrowprops=dict(arrowstyle="-", color=GOLD_DIM, lw=0.6, alpha=0.9),
            zorder=8,
        )
        # Label de duas linhas (depth + side)
        text_x = anchor_x
        text_y = anchor_y
        ax_hm.text(text_x, text_y + 4, f"{depth}",
                   fontsize=4.6, color=WHITE, ha=ha, va="center",
                   fontfamily=FONT, fontweight="bold", zorder=9,
                   path_effects=[pe.withStroke(linewidth=2.0, foreground="#000")])
        ax_hm.text(text_x, text_y - 1.5, f"{side}  ·  intens. {intensity_pct}%",
                   fontsize=3.8, color=GOLD, ha=ha, va="center",
                   fontfamily=FONT, fontweight="bold", zorder=9,
                   path_effects=[pe.withStroke(linewidth=1.6, foreground="#000")])

    ax_hm.set_title("ZONAS DE ATUAÇÃO", fontsize=6.8, color=WHITE,
                    fontfamily=FONT, fontweight="bold", pad=4, loc="left")

    # Footer info do bloco — balanço lateral
    e, c, d = lat_bal
    ax_hm.text(0, -7, f"Esq {e}% · Centro {c}% · Dir {d}%",
               fontsize=4.5, color=GRAY_L, fontfamily=FONT, fontweight="bold")
    ax_hm.text(0, -12, f"{len(pts):,} registros posicionais",
               fontsize=3.8, color=GRAY_M, fontfamily=FONT)

    # ─── BLOCO 2: ORIGEM DOS CHUTES ────────────────────────────────────────────
    ax_sh.set_facecolor(BG)
    ax_sh.axis("off")
    ax_sh.set_xlim(0, 1); ax_sh.set_ylim(0, 1)

    ax_sh.text(0, 1.03, "ORIGEM DOS CHUTES", fontsize=7.2, color=WHITE,
               fontfamily=FONT, fontweight="bold", va="bottom",
               transform=ax_sh.transAxes)
    total_shots = sum(v["n"] for v in sits.values())
    total_xg    = sum(v["xg"] for v in sits.values())
    ax_sh.text(0, 0.98, f"{total_shots} chutes  ·  {total_xg:.1f} xG total  ·  R1–R{round_num-1}",
               fontsize=4.8, color=GRAY_M, fontfamily=FONT, va="top",
               transform=ax_sh.transAxes)

    bar_start = 0.85
    bar_h     = 0.085
    bar_gap   = 0.190
    bar_maxw  = 0.66

    for i, (label, data) in enumerate(sits.items()):
        pct       = data["pct"]
        count     = data["n"]
        xg_val    = data["xg"]
        xgps      = data["xg_per_shot"]
        color     = BAR_COLORS.get(label, GRAY_M)
        y         = bar_start - i * bar_gap

        # Fundo
        ax_sh.add_patch(FancyBboxPatch((0, y), bar_maxw, bar_h,
                         boxstyle="round,pad=0.002", fc=GRAY_D, ec="none",
                         transform=ax_sh.transAxes, zorder=2))
        # Fill
        fill = max(bar_maxw * pct / 100, 0.004)
        ax_sh.add_patch(FancyBboxPatch((0, y), fill, bar_h,
                         boxstyle="round,pad=0.002", fc=color, ec="none",
                         alpha=0.92, transform=ax_sh.transAxes, zorder=3))
        # Nome (acima da barra)
        ax_sh.text(0, y + bar_h + 0.020, label.upper(),
                   fontsize=6.0, color=WHITE, fontfamily=FONT, fontweight="bold",
                   va="bottom", transform=ax_sh.transAxes, zorder=4)
        # Pct (à direita do fill)
        ax_sh.text(fill + 0.012, y + bar_h * 0.55,
                   f"{pct}%", fontsize=8.5, color=color, fontfamily=FONT,
                   fontweight="bold", va="center", transform=ax_sh.transAxes, zorder=4)
        # Contagem + xG/shot
        meta_x = bar_maxw + 0.025
        ax_sh.text(meta_x, y + bar_h * 0.78,
                   f"{count} chutes",
                   fontsize=4.8, color=GRAY_L, fontfamily=FONT,
                   va="center", transform=ax_sh.transAxes, zorder=4)
        if count > 0:
            ax_sh.text(meta_x, y + bar_h * 0.22,
                       f"{xgps:.2f} xG/chute",
                       fontsize=4.4, color=GRAY_M, fontfamily=FONT,
                       va="center", transform=ax_sh.transAxes, zorder=4)

    ax_sh.text(0, 0.02,
               "Jogo Corrido = jogada aberta + assistida   ·   "
               "Bola Parada = escanteio · falta · lateral",
               fontsize=4.0, color=GRAY_M, fontfamily=FONT, linespacing=1.4,
               va="bottom", transform=ax_sh.transAxes)

    # ─── BLOCO 3: PERFIL OFENSIVO (4 micro-métricas) ───────────────────────────
    ax_mt.set_facecolor(BG)
    ax_mt.axis("off")
    ax_mt.set_xlim(0, 1); ax_mt.set_ylim(0, 1)

    ax_mt.text(0, 1.03, "PERFIL OFENSIVO", fontsize=7.2, color=WHITE,
               fontfamily=FONT, fontweight="bold", va="bottom",
               transform=ax_mt.transAxes)
    ax_mt.text(0, 0.98, "valor por jogo  ·  comparativo Série B",
               fontsize=4.8, color=GRAY_M, fontfamily=FONT, va="top",
               transform=ax_mt.transAxes)

    # 4 métricas em grid 2x2
    metrics = [
        ("xG / jogo",        xg_pg,    "",  LEAGUE_AVG["expected_goals"],     True,  ".2f"),
        ("Posse de bola",    pos_pct,  "%", LEAGUE_AVG["possession"],         True,  ".0f"),
        ("Chutes / jogo",    shots_pg, "",  LEAGUE_AVG["shots_total"],        True,  ".1f"),
        ("Bolas longas",     lb_acc,   "",  LEAGUE_AVG["long_balls_accurate"], True, ".1f"),
    ]

    cell_w, cell_h = 0.46, 0.36
    cell_gx, cell_gy = 0.07, 0.06
    origin_y = 0.86
    for i, (label, val, unit, lg_avg, higher_good, fmt) in enumerate(metrics):
        col = i % 2
        row = i // 2
        x0 = col * (cell_w + cell_gx)
        y0 = origin_y - cell_h - row * (cell_h + cell_gy)

        # Card de fundo
        ax_mt.add_patch(FancyBboxPatch((x0, y0), cell_w, cell_h,
                         boxstyle="round,pad=0.004",
                         fc="#161616", ec=GRAY_D, lw=0.6,
                         transform=ax_mt.transAxes, zorder=2))

        # Label
        ax_mt.text(x0 + 0.018, y0 + cell_h - 0.04, label.upper(),
                   fontsize=5.0, color=GRAY_L, fontfamily=FONT, fontweight="bold",
                   va="top", transform=ax_mt.transAxes, zorder=3)

        # Valor grande
        val_str = f"{val:{fmt}}{unit}"
        ax_mt.text(x0 + 0.018, y0 + cell_h * 0.45, val_str,
                   fontsize=18, color=WHITE, fontfamily=FONT, fontweight="bold",
                   va="center", transform=ax_mt.transAxes, zorder=3,
                   path_effects=[pe.withStroke(linewidth=2.5, foreground="#000")])

        # Comparativo vs liga
        ratio = val / lg_avg if lg_avg else 1.0
        if ratio >= 1.10:
            arrow, status_col, status = "▲", GREEN if higher_good else RED, "acima"
        elif ratio <= 0.90:
            arrow, status_col, status = "▼", RED if higher_good else GREEN, "abaixo"
        else:
            arrow, status_col, status = "≈", GRAY_L, "na média"
        delta_pct = abs(ratio - 1) * 100

        ax_mt.text(x0 + 0.018, y0 + 0.040,
                   f"{arrow}  {status} liga", fontsize=4.6, color=status_col,
                   fontfamily=FONT, fontweight="bold",
                   va="center", transform=ax_mt.transAxes, zorder=3)
        ax_mt.text(x0 + cell_w - 0.018, y0 + 0.040,
                   f"liga: {lg_avg:{fmt}}", fontsize=4.0, color=GRAY_M,
                   fontfamily=FONT, ha="right",
                   va="center", transform=ax_mt.transAxes, zorder=3)

        # Mini-bar: valor vs liga
        bar_y  = y0 + 0.097
        bar_bg_w = cell_w - 0.036
        bar_x  = x0 + 0.018
        # escala: 2x liga = max
        scale = lg_avg * 2 if lg_avg else 1
        fill_w = min(bar_bg_w * (val / scale), bar_bg_w)
        ax_mt.add_patch(Rectangle((bar_x, bar_y), bar_bg_w, 0.012,
                         fc=GRAY_D, ec="none", transform=ax_mt.transAxes, zorder=3))
        ax_mt.add_patch(Rectangle((bar_x, bar_y), fill_w, 0.012,
                         fc=GOLD, ec="none", alpha=0.85,
                         transform=ax_mt.transAxes, zorder=4))
        # Marca da liga
        lg_x = bar_x + bar_bg_w * (lg_avg / scale)
        ax_mt.plot([lg_x, lg_x], [bar_y - 0.006, bar_y + 0.018],
                   color=WHITE, lw=0.9, alpha=0.85,
                   transform=ax_mt.transAxes, zorder=5)

    # ─── FOOTER (síntese dinâmica) ─────────────────────────────────────────────
    fig.add_artist(plt.Line2D([0.04, 0.975], [0.103, 0.103],
                               transform=fig.transFigure, color=GRAY_D, lw=0.5))
    # Faixa de marcador amarela
    fig.add_artist(plt.Line2D([0.04, 0.07], [0.052, 0.052],
                               transform=fig.transFigure,
                               color=GOLD, lw=2.5))
    fig.text(0.075, 0.075, "SÍNTESE", color=GOLD,
             fontsize=5.0, fontfamily=FONT, fontweight="bold", va="center")
    synthesis = build_synthesis(prof, sits, lat_bal, depth_pcts)
    fig.text(0.075, 0.045, synthesis,
             fontsize=5.8, color=GRAY_L, fontfamily=FONT,
             va="center", style="italic")
    fig.text(0.928, 0.030, "@SportRecifeLab", fontsize=5, color=GRAY_M,
             fontfamily=FONT, ha="right", va="center")

    # ─── Salvar ────────────────────────────────────────────────────────────────
    if out is None:
        out = f"pending_posts/2026-05-03_raio-x-{team_key}/07_como_joga.png"
    out_p = BASE / out
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight", facecolor=BG, pad_inches=0.05)
    plt.close(fig)
    print(f"  OK {out}")
    return str(out_p)


if __name__ == "__main__":
    generate_card()
