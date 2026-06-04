"""
Card "Como o Fortaleza Joga" — @SportRecifeLab
Redesign v2: Tactical Cartography

Três blocos analíticos:
  1. Mapa de evolução (heatmap KDE — corredores preferidos, campo vertical)
  2. Origem dos chutes (agrupamento por situation)
  3. Bolas longas (métrica com gauge)

Formato: 1200×675px landscape
Orientação do campo: vertical, ataque para CIMA
  heatmap x = comprimento (0=def, 100=atq) → eixo Y do plot
  heatmap y = largura   (0=esq, 100=dir) → eixo X do plot
"""
from __future__ import annotations

import json
from collections import Counter, deque
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, Arc
import matplotlib.patheffects as pe
import numpy as np
from scipy.stats import gaussian_kde
from scipy.ndimage import gaussian_filter

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE = Path(__file__).parent

# ── Paleta ────────────────────────────────────────────────────────────────────
BG         = "#0d0d0d"
GOLD       = "#F5C400"
GOLD_DIM   = "#9A7B00"
FIELD_DARK = "#0a2e16"
FIELD_MID  = "#0e3d1f"
FIELD_LINE = "#1f6b38"
WHITE      = "#FFFFFF"
GRAY_L     = "#AAAAAA"
GRAY_M     = "#555555"
GRAY_D     = "#222222"

BAR_COLORS = {
    "Jogada Aberta": GOLD,
    "Bola Parada":   "#4A8FD4",
    "Contra-ataque": "#E07030",
    "Pênalti":       GRAY_M,
}

# ── I/O ───────────────────────────────────────────────────────────────────────
def load_heatmap():
    with open(BASE / "data/processed/2026/opponents/fortaleza/team_heatmap.json", encoding="utf-8") as f:
        return json.load(f)["points"]

def load_profile():
    with open(BASE / "data/curated/opponents_2026/fortaleza/attack_profile.json", encoding="utf-8") as f:
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
    h, w = img.shape[:2]
    out = img.copy()
    vis = np.zeros((h, w), bool)
    q = deque()
    for px in range(w):
        for py in [0, h - 1]:
            if not vis[py, px]:
                if all(out[py, px, c] > 255 - thresh for c in range(3)):
                    q.append((py, px)); vis[py, px] = True
    for py in range(h):
        for px in [0, w - 1]:
            if not vis[py, px]:
                if all(out[py, px, c] > 255 - thresh for c in range(3)):
                    q.append((py, px)); vis[py, px] = True
    while q:
        cy, cx = q.popleft()
        out[cy, cx, 3] = 0
        for dy, dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            ny, nx = cy+dy, cx+dx
            if 0<=ny<h and 0<=nx<w and not vis[ny,nx]:
                if all(out[ny, nx, c] > 255 - thresh for c in range(3)):
                    vis[ny,nx] = True; q.append((ny,nx))
    return out


# ── Campo vertical ─────────────────────────────────────────────────────────────
def draw_pitch_vert(ax, lc=FIELD_LINE, fc=FIELD_DARK):
    """
    Campo VERTICAL: ataque para CIMA.
    xlim = 0-100  → largura (heatmap y)
    ylim = 0-100  → comprimento (heatmap x, 0=def baixo, 100=atq cima)
    Todos os elementos trocam (x,y) → (y,x) em relação ao padrão horizontal.
    """
    ax.set_facecolor(fc)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_aspect("auto")
    ax.axis("off")

    lw = 0.7

    # Faixas de relvado verticais (ao longo do comprimento)
    for i in range(0, 100, 20):
        ax.add_patch(Rectangle((i, 0), 10, 100, fc=FIELD_MID, ec="none", alpha=0.35, zorder=1))

    # Contorno
    ax.plot([0,100,100,0,0], [0,0,100,100,0], color=lc, lw=lw, zorder=3)
    # Linha do meio (y=50)
    ax.plot([0,100], [50,50], color=lc, lw=lw, zorder=3)
    # Círculo central
    ax.add_patch(plt.Circle((50,50), 9.15, color=lc, fill=False, lw=lw, zorder=3))
    ax.plot([50],[50],"o", color=lc, ms=1.0, zorder=3)

    # Área grande defensiva (y=0..16.5), xlim 29.84..70.16
    ax.add_patch(Rectangle((29.84, 0), 40.32, 16.5, ec=lc, fc="none", lw=lw, zorder=3))
    # Área grande ataque (y=83.5..100)
    ax.add_patch(Rectangle((29.84, 83.5), 40.32, 16.5, ec=lc, fc="none", lw=lw, zorder=3))
    # Área pequena defensiva
    ax.add_patch(Rectangle((41.34, 0), 17.32, 5.5, ec=lc, fc="none", lw=lw, zorder=3))
    # Área pequena ataque
    ax.add_patch(Rectangle((41.34, 94.5), 17.32, 5.5, ec=lc, fc="none", lw=lw, zorder=3))
    # Gols (abaixo e acima)
    ax.add_patch(Rectangle((45.2, -1.5), 9.6, 1.5, ec=lc, fc="none", lw=lw, zorder=3, clip_on=False))
    ax.add_patch(Rectangle((45.2, 100), 9.6, 1.5, ec=lc, fc="none", lw=lw, zorder=3, clip_on=False))
    # Arcos
    ax.add_patch(Arc((50, 16.5), 18.3, 18.3, angle=0, theta1=37, theta2=143, color=lc, lw=lw, zorder=3))
    ax.add_patch(Arc((50, 83.5), 18.3, 18.3, angle=0, theta1=217, theta2=323, color=lc, lw=lw, zorder=3))


# ── Dados ─────────────────────────────────────────────────────────────────────
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
    del c[None]
    total = sum(c.values())
    order = ["Jogada Aberta", "Bola Parada", "Contra-ataque", "Pênalti"]
    return {g: {"n": c.get(g,0), "pct": round(c.get(g,0)/total*100) if total else 0}
            for g in order}


def kde_grid(points, n=120):
    """KDE normalizado. Retorna (z, xi, yi) onde xi=heatmap_y (largura), yi=heatmap_x (comp)."""
    hx = np.array([p["x"] for p in points], float)
    hy = np.array([p["y"] for p in points], float)
    # Para campo VERTICAL: screen_x = hy (largura), screen_y = hx (comprimento)
    xi = np.linspace(0, 100, n)   # screen x = heatmap y
    yi = np.linspace(0, 100, n)   # screen y = heatmap x
    xg, yg = np.meshgrid(xi, yi)
    # kde em espaço (screen_x=hy, screen_y=hx)
    kde = gaussian_kde(np.vstack([hy, hx]), bw_method=0.11)
    z = kde(np.vstack([xg.ravel(), yg.ravel()])).reshape(n, n)
    z = gaussian_filter(z, sigma=1.2)
    z = (z - z.min()) / (z.max() - z.min() + 1e-9)
    return z, xi, yi


def top_zones(z, xi, yi, n=2):
    from scipy.ndimage import maximum_filter
    lm = maximum_filter(z, size=14) == z
    peaks = sorted(np.argwhere(lm & (z > 0.62)),
                   key=lambda p: z[p[0], p[1]], reverse=True)
    zones, used = [], []
    for p in peaks:
        iy, ix = p
        if any(abs(iy-u[0]) < 18 and abs(ix-u[1]) < 18 for u in used):
            continue
        used.append((iy, ix))
        zones.append({"sx": float(xi[ix]), "sy": float(yi[iy]),
                       "hx": float(yi[iy]), "hy": float(xi[ix])})
        if len(zones) >= n:
            break
    return zones


def zone_label(hx, hy):
    """hx = comprimento (0=def, 100=atq), hy = largura (0=esq, 100=dir)"""
    if hx < 33:   depth = "SETOR\nDEFENSIVO"
    elif hx < 52: depth = "MEIO\nDE CAMPO"
    elif hx < 72: depth = "TERÇO\nFINAL"
    else:          depth = "ÁREA\nRIVAL"
    if hy < 30:   side = "ESQ"
    elif hy > 70: side = "DIR"
    else:          side = "CTR"
    return f"{depth}", side


# ── Card ──────────────────────────────────────────────────────────────────────
def generate_card(out="pending_posts/2026-05-02_raio-x-fortaleza/07_como_joga_v2.png"):
    pts     = load_heatmap()
    prof    = load_profile()
    shots   = prof.get("shots", [])
    avgs    = prof.get("averages", {})
    sits    = situation_groups(shots)
    z, xi, yi = kde_grid(pts)
    zones   = top_zones(z, xi, yi, n=2)
    lb_acc  = avgs.get("long_balls_accurate", 21.5)
    lb_pct  = avgs.get("long_balls_pct", 5.8)
    pss_pg  = avgs.get("passes_total", 371.8)
    pos_pct = avgs.get("possession", 50.7)

    DPI = 150
    fig = plt.figure(figsize=(1200/DPI, 675/DPI), facecolor=BG, dpi=DPI)

    # Layout: left=heatmap, mid=shots, right=metric
    gs = fig.add_gridspec(
        1, 3,
        left=0.04, right=0.975,
        top=0.885, bottom=0.09,
        wspace=0.06,
        width_ratios=[0.28, 0.40, 0.32],
    )
    ax_hm = fig.add_subplot(gs[0])
    ax_sh = fig.add_subplot(gs[1])
    ax_mt = fig.add_subplot(gs[2])

    # ─── HEADER ────────────────────────────────────────────────────────────────
    fig.text(0.04, 0.984, "COMO O  ", color=GRAY_M, fontsize=6.0,
             fontfamily="Arial", va="top", fontweight="normal")
    fig.text(0.04, 0.972, "FORTALEZA EC JOGA", color=GOLD,
             fontsize=17, fontfamily="Arial", fontweight="bold", va="top",
             path_effects=[pe.withStroke(linewidth=2.5, foreground="#000")])
    fig.text(0.848, 0.972, "Série B 2026  ·  R1–R6", color=GRAY_M,
             fontsize=6, fontfamily="Arial", va="top", ha="right")
    fig.add_artist(plt.Line2D([0.04, 0.975], [0.91, 0.91],
                               transform=fig.transFigure,
                               color=GOLD_DIM, lw=0.5, alpha=0.8))

    # Logos
    logo_ft = load_logo(str(BASE/"data/cache/logos/2020.png"), 48)
    logo_lb = load_logo(str(BASE/"sportrecifelab_avatar.png"), 34)
    if logo_ft is not None:
        logo_ft = remove_bg(logo_ft)
        axt = fig.add_axes([0.855, 0.905, 0.048, 0.088])
        axt.imshow(logo_ft); axt.axis("off")
    if logo_lb is not None:
        logo_lb = remove_bg(logo_lb)
        axb = fig.add_axes([0.932, 0.01, 0.048, 0.072])
        axb.imshow(logo_lb); axb.axis("off")

    # ─── BLOCO 1: HEATMAP VERTICAL ─────────────────────────────────────────────
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("tct", [
        (0.00, FIELD_DARK),
        (0.30, "#144a20"),
        (0.60, "#6B5200"),
        (0.82, GOLD),
        (1.00, "#FFFFFF"),
    ])
    draw_pitch_vert(ax_hm)
    ax_hm.contourf(xi, yi, z, levels=22, cmap=cmap, alpha=0.80, zorder=4,
                   vmin=0.04, vmax=1.0)

    # Seta de ataque (dentro do campo, no terço final)
    ax_hm.annotate("", xy=(50, 97), xytext=(50, 90),
                   arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=1.0,
                                   mutation_scale=6), zorder=6)
    ax_hm.text(58, 93, "ATQ", fontsize=3.8, color=GOLD_DIM, ha="left", va="center",
               fontfamily="Arial", fontweight="bold", zorder=6)

    # Labels das zonas
    for zone in zones:
        sx, sy = zone["sx"], zone["sy"]
        lbl, side = zone_label(zone["hx"], zone["hy"])
        ax_hm.scatter(sx, sy, s=45, color=GOLD, alpha=0.95, zorder=7,
                      edgecolors="#000", linewidths=0.7)
        off_x = 12 if sx < 50 else -12
        ha    = "left" if sx < 50 else "right"
        ax_hm.annotate(
            f"{lbl}\n{side}",
            xy=(sx, sy), xytext=(sx+off_x, sy),
            fontsize=4, color=GOLD, ha=ha, va="center",
            fontfamily="Arial", fontweight="bold", zorder=8,
            arrowprops=dict(arrowstyle="-", color=GOLD_DIM, lw=0.5),
        )

    ax_hm.set_title("ZONAS DE ATUAÇÃO", fontsize=6.5, color=GRAY_L,
                    fontfamily="Arial", fontweight="bold", pad=4, loc="left")
    ax_hm.text(0, -7, f"{len(pts):,} registros · {prof.get('match_count',6)} partidas",
               fontsize=3.8, color=GRAY_M, fontfamily="Arial")

    # ─── BLOCO 2: ORIGEM DOS CHUTES ────────────────────────────────────────────
    ax_sh.set_facecolor(BG)
    ax_sh.axis("off")
    ax_sh.set_xlim(0, 1)
    ax_sh.set_ylim(0, 1)

    ax_sh.text(0, 1.01, "ORIGEM DOS CHUTES", fontsize=7, color=GRAY_L,
               fontfamily="Arial", fontweight="bold", va="bottom",
               transform=ax_sh.transAxes)
    total_shots = sum(v["n"] for v in sits.values())
    ax_sh.text(0, 0.97, f"{total_shots} chutes analisados  ·  R1–R6",
               fontsize=4.5, color=GRAY_M, fontfamily="Arial", va="top",
               transform=ax_sh.transAxes)

    bar_start = 0.84
    bar_h     = 0.095
    bar_gap   = 0.185
    bar_maxw  = 0.70

    for i, (label, data) in enumerate(sits.items()):
        pct   = data["pct"]
        count = data["n"]
        color = BAR_COLORS.get(label, GRAY_M)
        y     = bar_start - i * bar_gap

        # Fundo
        ax_sh.add_patch(FancyBboxPatch((0, y), bar_maxw, bar_h,
                         boxstyle="round,pad=0.002", fc=GRAY_D, ec="none",
                         transform=ax_sh.transAxes, zorder=2))
        # Fill
        fill = max(bar_maxw * pct / 100, 0.004)
        ax_sh.add_patch(FancyBboxPatch((0, y), fill, bar_h,
                         boxstyle="round,pad=0.002", fc=color, ec="none",
                         alpha=0.88, transform=ax_sh.transAxes, zorder=3))
        # Nome
        ax_sh.text(0, y + bar_h + 0.018, label.upper(),
                   fontsize=6, color=WHITE, fontfamily="Arial", fontweight="bold",
                   va="bottom", transform=ax_sh.transAxes, zorder=4)
        # Pct
        ax_sh.text(fill + 0.014, y + bar_h * 0.55,
                   f"{pct}%", fontsize=8, color=color, fontfamily="Arial",
                   fontweight="bold", va="center", transform=ax_sh.transAxes, zorder=4)
        # Contagem
        ax_sh.text(fill + 0.014, y + 0.004,
                   f"({count})", fontsize=3.8, color=GRAY_M, fontfamily="Arial",
                   va="bottom", transform=ax_sh.transAxes, zorder=4)

    ax_sh.text(0, 0.02,
               "Jogada Aberta = jogo corrido + assistido\n"
               "Bola Parada = escanteio · falta · lateral",
               fontsize=3.8, color=GRAY_M, fontfamily="Arial", linespacing=1.4,
               va="bottom", transform=ax_sh.transAxes)

    # ─── BLOCO 3: BOLAS LONGAS ─────────────────────────────────────────────────
    ax_mt.set_facecolor(BG)
    ax_mt.axis("off")
    ax_mt.set_xlim(0, 1)
    ax_mt.set_ylim(0, 1)

    # Título
    ax_mt.text(0, 1.01, "JOGO DIRETO", fontsize=7, color=GRAY_L,
               fontfamily="Arial", fontweight="bold", va="bottom",
               transform=ax_mt.transAxes)

    # Número principal
    ax_mt.text(0.0, 0.82, f"{lb_acc:.1f}",
               fontsize=46, color=GOLD, fontfamily="Arial", fontweight="bold",
               va="center", transform=ax_mt.transAxes,
               path_effects=[pe.withStroke(linewidth=3.5, foreground="#000")])
    ax_mt.text(0.0, 0.645, "bolas longas precisas / jogo",
               fontsize=6.2, color=GRAY_L, fontfamily="Arial",
               va="center", transform=ax_mt.transAxes)
    ax_mt.text(0.0, 0.58, f"{lb_pct:.1f}% dos passes totais",
               fontsize=5.5, color=GRAY_M, fontfamily="Arial",
               va="center", transform=ax_mt.transAxes)

    # Divisor
    ax_mt.add_patch(Rectangle((0, 0.545), 1.0, 0.0015, fc=GRAY_D, ec="none",
                               transform=ax_mt.transAxes))

    # Gauge
    sc_lo, sc_hi = 5.0, 35.0
    gy, gh = 0.40, 0.050
    n_seg = 50
    for k in range(n_seg):
        t = k / n_seg
        if t < 0.4:
            r,g_c,b = int(50+t*100), int(100+t*40), int(180-t*100)
        elif t < 0.7:
            tt = (t-0.4)/0.3
            r,g_c,b = int(150+tt*60), int(140-tt*60), 80
        else:
            tt = (t-0.7)/0.3
            r,g_c,b = int(210+tt*30), int(80-tt*50), int(80-tt*50)
        ax_mt.add_patch(Rectangle((k/n_seg, gy), 1/n_seg, gh,
                         fc=(r/255,g_c/255,b/255), ec="none",
                         transform=ax_mt.transAxes, zorder=2))

    # Marcador do Fortaleza
    fp = min(max((lb_acc - sc_lo) / (sc_hi - sc_lo), 0), 1)
    ax_mt.add_patch(Rectangle((fp-0.018, gy-0.022), 0.036, gh+0.044,
                               fc=GOLD, ec="#000", lw=0.9,
                               transform=ax_mt.transAxes, zorder=4))

    # Linha de referência (média ~18)
    avgp = (18 - sc_lo) / (sc_hi - sc_lo)
    ax_mt.plot([avgp, avgp], [gy, gy+gh], color=WHITE, lw=0.9, alpha=0.55,
               zorder=3, transform=ax_mt.transAxes)
    ax_mt.text(avgp, gy-0.04, "média\nsérie b", fontsize=3.5, color=GRAY_M,
               ha="center", va="top", fontfamily="Arial",
               transform=ax_mt.transAxes)

    # Labels extremos
    ax_mt.text(0.0, gy-0.04, f"{sc_lo:.0f}", fontsize=3.8, color=GRAY_M,
               ha="left", va="top", fontfamily="Arial", transform=ax_mt.transAxes)
    ax_mt.text(1.0, gy-0.04, f"{sc_hi:.0f}", fontsize=3.8, color=GRAY_M,
               ha="right", va="top", fontfamily="Arial", transform=ax_mt.transAxes)

    # Contexto
    ax_mt.text(0.0, 0.27,
               f"{pss_pg:.0f} passes / jogo  ·  {pos_pct:.0f}% posse",
               fontsize=5.2, color=GRAY_M, fontfamily="Arial",
               va="top", transform=ax_mt.transAxes)

    ax_mt.text(0.0, 0.17,
               "Volume de bola longa acima\nda média — transição objetiva.",
               fontsize=5.8, color=GRAY_L, fontfamily="Arial", linespacing=1.6,
               va="top", transform=ax_mt.transAxes)

    # ─── FOOTER ────────────────────────────────────────────────────────────────
    fig.add_artist(plt.Line2D([0.04, 0.975], [0.088, 0.088],
                               transform=fig.transFigure, color=GRAY_D, lw=0.5))
    fig.text(0.04, 0.047,
             "Equipe de posse equilibrada (51%) que ataca principalmente pelo jogo corrido "
             "e usa bola parada como segunda fonte (30% dos chutes).",
             fontsize=5.5, color=GRAY_L, fontfamily="Arial",
             va="center", style="italic")
    fig.text(0.975, 0.028, "@SportRecifeLab", fontsize=5, color=GRAY_M,
             fontfamily="Arial", ha="right", va="center")

    # ─── Salvar ────────────────────────────────────────────────────────────────
    out_p = BASE / out
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_p, dpi=DPI, bbox_inches="tight", facecolor=BG, pad_inches=0.05)
    plt.close(fig)
    print(f"  OK {out}")
    return str(out_p)


if __name__ == "__main__":
    generate_card()
