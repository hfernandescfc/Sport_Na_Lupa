"""
Post único resumo — Sport 3×0 Retrô · Copa do Nordeste R3 · 08/04/2026
Layout: Header/stats + xG timeline + shotmap (metade do campo)
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.gridspec import GridSpec
import numpy as np
from mplsoccer import Pitch
from PIL import Image

# ─── Paleta ──────────────────────────────────────────────────────────────────
BG          = "#0d0d0d"
PITCH_COLOR = "#0e3d1f"
LINE_COLOR  = "#2a7a3a"
YELLOW      = "#F5C400"
BLUE        = "#4A90D9"
LGRAY       = "#AAAAAA"
DGRAY       = "#1A1A1A"
WHITE       = "#FFFFFF"
ACCENT      = "#E8B84B"  # dourado Sport
C_AWAY      = "#5B9BD5"  # azul Retrô
GRAY        = "#444444"

LOGO_PATH = Path(__file__).parent / "sportrecifelab_avatar.png"

# ─── Dados da partida ─────────────────────────────────────────────────────────
MATCH = {
    "home_team":   "SPORT",
    "away_team":   "RETRÔ",
    "score":       [3, 0],
    "date":        "08.04.2026",
    "round":       "R3",
    "competition": "COPA DO NORDESTE",
    "home_logo":   "data/cache/logos/1959.png",
    "away_logo":   "data/cache/logos/324839.png",
    "stats": {
        "possession":      [64.0, 36.0],
        "xg":              [2.29, 0.47],
        "shots_total":     [19,   4],
        "shots_on_target": [6,    0],
        "corners":         [8,    0],
        "passes_accuracy": [88.0, 82.0],
    },
    "shots": [
        {"team": "home", "player": "Perotti",        "minute": 5,  "type": "save",  "xg": 0.1752, "coord": (6,  59)},
        {"team": "home", "player": "Felipinho",      "minute": 11, "type": "save",  "xg": 0.0511, "coord": (23, 33)},
        {"team": "home", "player": "Perotti",        "minute": 11, "type": "miss",  "xg": 0.0188, "coord": (29, 68)},
        {"team": "home", "player": "Clayson",        "minute": 13, "type": "block", "xg": 0.0099, "coord": (21, 25)},
        {"team": "home", "player": "C. Barletta",    "minute": 33, "type": "miss",  "xg": 0.0041, "coord": (15, 73)},
        {"team": "home", "player": "Perotti",        "minute": 59, "type": "miss",  "xg": 0.1792, "coord": (8,  50)},
        {"team": "home", "player": "Carlos De Pena", "minute": 60, "type": "save",  "xg": 0.0769, "coord": (20, 35)},
        {"team": "home", "player": "Iury Castilho",  "minute": 60, "type": "goal",  "xg": 0.7745, "coord": (5,  52)},
        {"team": "home", "player": "Zé Lucas",       "minute": 66, "type": "miss",  "xg": 0.0396, "coord": (19, 60)},
        {"team": "home", "player": "Yago Felipe",    "minute": 68, "type": "miss",  "xg": 0.3074, "coord": (7,  44)},
        {"team": "home", "player": "Iury Castilho",  "minute": 73, "type": "miss",  "xg": 0.1129, "coord": (15, 50)},
        {"team": "home", "player": "Carlos De Pena", "minute": 73, "type": "miss",  "xg": 0.0009, "coord": (22, 24)},
        {"team": "home", "player": "C. Barletta",    "minute": 74, "type": "goal",  "xg": 0.2052, "coord": (8,  64)},
        {"team": "home", "player": "Carlos De Pena", "minute": 77, "type": "miss",  "xg": 0.1390, "coord": (6,  34)},
        {"team": "home", "player": "Habraão",        "minute": 77, "type": "goal",  "xg": 0.0779, "coord": (10, 56)},
        {"team": "home", "player": "Felipinho",      "minute": 81, "type": "miss",  "xg": 0.0009, "coord": (25, 46)},
        {"team": "home", "player": "Carlos De Pena", "minute": 86, "type": "block", "xg": 0.0602, "coord": (15, 49)},
        {"team": "home", "player": "Carlos De Pena", "minute": 86, "type": "block", "xg": 0.0084, "coord": (14, 52)},
        {"team": "home", "player": "Edson Lucas",    "minute": 90, "type": "block", "xg": 0.0486, "coord": (8,  36)},
        {"team": "away", "player": "D. Matos",       "minute": 12, "type": "miss",  "xg": 0.0054, "coord": (29, 50)},
        {"team": "away", "player": "Sillas",         "minute": 29, "type": "block", "xg": 0.0049, "coord": (22, 66)},
        {"team": "away", "player": "D. Matos",       "minute": 45, "type": "miss",  "xg": 0.4501, "coord": (4,  46)},
        {"team": "away", "player": "Kadi",           "minute": 63, "type": "miss",  "xg": 0.0046, "coord": (18, 51)},
    ],
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _to_sb_home(x, y):
    return 120 - (x / 100 * 120), (y / 100 * 80)

def _to_sb_away(x, y):
    return x / 100 * 120, (100 - y) / 100 * 80

def _load_logo(path: str, size: int = 52) -> np.ndarray | None:
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((size, size), Image.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset = ((size - img.width) // 2, (size - img.height) // 2)
        canvas.alpha_composite(img, offset)
        return np.array(canvas)
    except Exception:
        return None

def _step_xy(shots, team, x_max=90):
    """Constrói série cumulativa de xG para step chart."""
    events = sorted(
        [(s["minute"], s.get("xg") or 0) for s in shots if s["team"] == team],
        key=lambda t: t[0]
    )
    xs, ys, acc = [0], [0.0], 0.0
    for m, xg in events:
        xs.append(m); ys.append(acc)
        acc += xg
        xs.append(m); ys.append(acc)
    if not xs or xs[-1] < x_max:
        xs.append(x_max); ys.append(acc)
    return xs, ys


# ─── Seção 1: Header com placar + logos + stats highlight ────────────────────

def _draw_header(fig, ax_hdr, md):
    ax_hdr.set_xlim(0, 1)
    ax_hdr.set_ylim(0, 1)
    ax_hdr.axis("off")
    ax_hdr.set_facecolor(BG)

    stats = md["stats"]
    home, away = md["home_team"], md["away_team"]
    sh, sa = md["score"]

    # Faixa superior: competição
    ax_hdr.text(0.5, 0.97, f"{md['competition']}  ·  {md['round']}",
                color=YELLOW, fontsize=7.5, fontweight="bold",
                fontfamily="Franklin Gothic Heavy",
                ha="center", va="top", transform=ax_hdr.transAxes)

    # Logos
    logo_h = _load_logo(md.get("home_logo", ""), 56)
    logo_a = _load_logo(md.get("away_logo", ""), 56)
    if logo_h is not None:
        ab = AnnotationBbox(OffsetImage(logo_h, zoom=1.0),
                            (0.18, 0.62), xycoords=ax_hdr.transAxes,
                            frameon=False, zorder=5)
        ax_hdr.add_artist(ab)
    if logo_a is not None:
        ab = AnnotationBbox(OffsetImage(logo_a, zoom=1.0),
                            (0.82, 0.62), xycoords=ax_hdr.transAxes,
                            frameon=False, zorder=5)
        ax_hdr.add_artist(ab)

    # Nomes dos times
    ax_hdr.text(0.18, 0.28, home, color=ACCENT, fontsize=8,
                fontfamily="Franklin Gothic Heavy", fontweight="bold",
                ha="center", va="center", transform=ax_hdr.transAxes)
    ax_hdr.text(0.82, 0.28, away, color=C_AWAY, fontsize=8,
                fontfamily="Franklin Gothic Heavy", fontweight="bold",
                ha="center", va="center", transform=ax_hdr.transAxes)

    # Placar enorme
    ax_hdr.text(0.5, 0.68, f"{sh}  ×  {sa}",
                color=WHITE, fontsize=36, fontweight="black",
                fontfamily="Franklin Gothic Heavy",
                ha="center", va="center", transform=ax_hdr.transAxes,
                path_effects=[pe.withStroke(linewidth=3, foreground=BG)])

    # Data
    ax_hdr.text(0.5, 0.46, md["date"],
                color=LGRAY, fontsize=7, fontfamily="Arial",
                ha="center", va="center", transform=ax_hdr.transAxes)

    # ── Pills de estatísticas chave ──────────────────────────────────────────
    pill_data = [
        ("POSSE",    f"{stats['possession'][0]:.0f}%",   f"{stats['possession'][1]:.0f}%"),
        ("xG",       f"{stats['xg'][0]:.2f}",            f"{stats['xg'][1]:.2f}"),
        ("CHUTES",   f"{stats['shots_total'][0]}",        f"{stats['shots_total'][1]}"),
        ("NO ALVO",  f"{stats['shots_on_target'][0]}",    f"{stats['shots_on_target'][1]}"),
        ("ESCANTEIOS", f"{stats['corners'][0]}",          f"{stats['corners'][1]}"),
    ]

    n = len(pill_data)
    pill_w = 1.0 / n
    y_pill = 0.17

    for i, (label, v_home, v_away) in enumerate(pill_data):
        cx = (i + 0.5) * pill_w

        # Separador vertical (exceto primeiro)
        if i > 0:
            ax_hdr.axvline(i * pill_w, ymin=0.02, ymax=0.35,
                           color=GRAY, linewidth=0.5)

        ax_hdr.text(cx, y_pill + 0.14, v_home,
                    color=ACCENT, fontsize=11, fontweight="black",
                    fontfamily="Franklin Gothic Heavy",
                    ha="center", va="center", transform=ax_hdr.transAxes)
        ax_hdr.text(cx, y_pill, label,
                    color=LGRAY, fontsize=6, fontfamily="Arial",
                    ha="center", va="center", transform=ax_hdr.transAxes)
        ax_hdr.text(cx, y_pill - 0.14, v_away,
                    color=C_AWAY, fontsize=11, fontweight="black",
                    fontfamily="Franklin Gothic Heavy",
                    ha="center", va="center", transform=ax_hdr.transAxes)

    # Linha divisória inferior
    ax_hdr.axhline(0.03, color=GRAY, linewidth=0.5)


# ─── Seção 2: xG acumulado ────────────────────────────────────────────────────

def _draw_xg(ax, shots):
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(colors=LGRAY, labelsize=6.5)
    ax.xaxis.label.set_color(LGRAY)
    ax.yaxis.label.set_color(LGRAY)

    x_max = 90
    hx, hy = _step_xy(shots, "home", x_max)
    ax_, ay = _step_xy(shots, "away", x_max)

    ax.fill_between(hx, hy, alpha=0.18, color=ACCENT, step=None)
    ax.plot(hx, hy, color=ACCENT, linewidth=2.0, label="Sport", zorder=4)

    ax.fill_between(ax_, ay, alpha=0.12, color=C_AWAY, step=None)
    ax.plot(ax_, ay, color=C_AWAY, linewidth=1.5, linestyle="--", label="Retrô", zorder=3)

    # Marcadores de gol
    goals = [s for s in shots if s["team"] == "home" and s["type"] == "goal"]
    acc = 0.0
    xg_at_goal = {}
    for s in sorted(shots, key=lambda x: x["minute"]):
        if s["team"] == "home":
            acc += s.get("xg") or 0
            if s["type"] == "goal":
                xg_at_goal[s["minute"]] = acc

    goal_labels = {60: "Iury\nCastilho", 74: "C.\nBarletta", 77: "Habraão"}
    offsets = {60: (2, 0.08, "bottom"), 74: (-2, -0.15, "top"), 77: (2, 0.08, "bottom")}

    for m, yv in xg_at_goal.items():
        ax.scatter(m, yv, s=200, marker="*", color=YELLOW,
                   edgecolors=WHITE, linewidths=0.5, zorder=6)
        lbl = goal_labels.get(m, f"{m}'")
        dx, dy, va = offsets.get(m, (2, 0.08, "bottom"))
        ax.text(m + dx, yv + dy, f"{m}'  {lbl}",
                color=YELLOW, fontsize=6, fontfamily="Arial",
                ha="left" if dx >= 0 else "right", va=va, linespacing=1.3,
                path_effects=[pe.withStroke(linewidth=1.8, foreground=BG)], zorder=7)

    # Linha xG=1
    ax.axhline(1.0, color=GRAY, linewidth=0.6, linestyle=":", zorder=1)
    ax.text(91, 1.02, "1 xG", color=GRAY, fontsize=5.5, va="bottom", ha="left")

    # Linha meio tempo
    ax.axvline(45, color=GRAY, linewidth=0.5, linestyle="--", alpha=0.5, zorder=1)
    ax.text(45.5, 0.02, "HT", color=GRAY, fontsize=5.5, va="bottom")

    ax.set_xlim(0, x_max + 1)
    ax.set_ylim(0, None)
    ax.set_xticks([0, 15, 30, 45, 60, 75, 90])
    ax.set_xticklabels(["0", "15'", "30'", "45'", "60'", "75'", "90'"])
    ax.set_ylabel("xG ACUMULADO", fontsize=6, color=LGRAY, fontfamily="Arial",
                  labelpad=4)

    # Label final
    hfinal = hy[-1]
    afinal = ay[-1]
    ax.text(x_max + 0.5, hfinal, f"xG {hfinal:.2f}",
            color=ACCENT, fontsize=7, fontweight="bold", va="center", ha="left",
            fontfamily="Franklin Gothic Heavy")
    ax.text(x_max + 0.5, afinal - 0.04, f"xG {afinal:.2f}",
            color=C_AWAY, fontsize=7, fontweight="bold", va="top", ha="left",
            fontfamily="Franklin Gothic Heavy")

    # Título interno
    ax.text(0.02, 0.96, "xG ACUMULADO POR FINALIZAÇÃO",
            transform=ax.transAxes, color=LGRAY, fontsize=6.5,
            fontfamily="Arial", va="top")

    # Legenda mínima
    legend_items = [
        Line2D([0],[0], color=ACCENT, linewidth=2, label="Sport"),
        Line2D([0],[0], color=C_AWAY,  linewidth=1.5, linestyle="--", label="Retrô"),
        Line2D([0],[0], marker="*", color="w", markerfacecolor=YELLOW,
               markersize=8, linestyle="None", label="Gol"),
    ]
    ax.legend(handles=legend_items, loc="upper left", fontsize=6,
              framealpha=0.2, facecolor=BG, labelcolor=LGRAY,
              edgecolor=GRAY, borderpad=0.5, handlelength=1.2)


# ─── Seção 3: Shotmap (meia-cancha) ──────────────────────────────────────────

def _draw_shotmap(ax, shots):
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color=PITCH_COLOR,
        line_color=LINE_COLOR,
        linewidth=0.8,
        goal_type="box",
        corner_arcs=True,
        half=True,
    )
    pitch.draw(ax=ax)
    ax.set_xlim(55, 122)
    ax.set_ylim(-4, 84)

    XG_SCALE = 7
    SCATTER_SCALE = 750

    for s in shots:
        if s["team"] == "home":
            sx, sy = _to_sb_home(*s["coord"])
        else:
            sx, sy = _to_sb_away(*s["coord"])
            # Espelha para mostrar no mesmo lado (ataque direito)
            sx = 120 - sx

        xg  = s.get("xg") or 0.01
        stype = s["type"]
        is_goal = stype == "goal"
        team = s["team"]

        color = ACCENT if team == "home" else C_AWAY
        alpha_fill = 0.20 if not is_goal else 0.35
        r = xg * XG_SCALE

        circle = plt.Circle((sx, sy), r, color=color, alpha=alpha_fill,
                             linewidth=0, zorder=3)
        ax.add_patch(circle)
        circle_edge = plt.Circle((sx, sy), r, color=color, alpha=0.45,
                                  fill=False, linewidth=0.8, zorder=4)
        ax.add_patch(circle_edge)

        if is_goal:
            ax.scatter(sx, sy, s=SCATTER_SCALE * 0.55, marker="*",
                       color=color, edgecolors=WHITE, linewidths=0.5, zorder=6)
        else:
            ax.scatter(sx, sy, s=30, marker="o",
                       color=color, alpha=0.7, edgecolors="none", zorder=5)

    # Título interno
    ax.text(0.02, 0.97, "MAPA DE FINALIZAÇÕES",
            transform=ax.transAxes, color=LGRAY, fontsize=6.5,
            fontfamily="Arial", va="top",
            path_effects=[pe.withStroke(linewidth=2, foreground=PITCH_COLOR)])

    # Legenda
    legend_items = [
        Line2D([0],[0], marker="o", color="w", markerfacecolor=ACCENT,
               markersize=7, linestyle="None", label="Sport"),
        Line2D([0],[0], marker="o", color="w", markerfacecolor=C_AWAY,
               markersize=7, linestyle="None", label="Retrô"),
        Line2D([0],[0], marker="*", color="w", markerfacecolor=YELLOW,
               markersize=10, linestyle="None", label="Gol"),
    ]
    ax.legend(handles=legend_items, loc="lower left",
              bbox_to_anchor=(0.0, 0.0), ncol=3,
              fontsize=6, framealpha=0.25, facecolor=BG,
              labelcolor=LGRAY, edgecolor=GRAY,
              handlelength=0.8, borderpad=0.6, columnspacing=0.8)

    # Nota xG
    ax.text(0.5, -0.04, "tamanho do círculo ∝ xG da finalização",
            transform=ax.transAxes, color="#555555", fontsize=5.5,
            fontfamily="Arial", ha="center", va="top")


# ─── Montagem final ───────────────────────────────────────────────────────────

def generate_post(output_path="pending_posts/2026-04-09_sport-retro-nordeste-r3/post_resumo.png"):
    fig = plt.figure(figsize=(7.0, 9.8), dpi=155)
    fig.patch.set_facecolor(BG)

    # GridSpec: header | xg | shotmap
    gs = GridSpec(
        3, 1,
        figure=fig,
        top=0.97, bottom=0.055,
        hspace=0.10,
        height_ratios=[2.2, 2.2, 3.0],
    )

    ax_hdr = fig.add_subplot(gs[0])
    ax_xg  = fig.add_subplot(gs[1])
    ax_map = fig.add_subplot(gs[2])

    _draw_header(fig, ax_hdr, MATCH)
    _draw_xg(ax_xg, MATCH["shots"])
    _draw_shotmap(ax_map, MATCH["shots"])

    # ── Footer global ─────────────────────────────────────────────────────────
    if LOGO_PATH.exists():
        logo_arr = np.array(
            Image.open(LOGO_PATH).convert("RGBA").resize((38, 38), Image.LANCZOS)
        )
        ab = AnnotationBbox(
            OffsetImage(logo_arr, zoom=1.0),
            (0.07, 0.022), xycoords="figure fraction",
            frameon=False, zorder=10,
        )
        ax_map.add_artist(ab)

    fig.text(0.14, 0.022, "@SportRecifeLab",
             color=YELLOW, fontsize=8, fontfamily="Franklin Gothic Heavy",
             fontweight="bold", ha="left", va="center")
    fig.text(0.97, 0.022, "Dados: SofaScore",
             color=LGRAY, fontsize=7, fontfamily="Arial",
             ha="right", va="center")

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out, dpi=155, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Post salvo: {out}")
    return out


if __name__ == "__main__":
    generate_post()
