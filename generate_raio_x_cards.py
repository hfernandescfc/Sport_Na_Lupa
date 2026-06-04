"""
generate_raio_x_cards.py — Raio-X genérico para qualquer adversário do Sport
Série B 2026 | @SportRecifeLab

Uso:
  python generate_raio_x_cards.py \\
    --team-key america-mg \\
    --team-name "AMERICA MINEIRO" \\
    --team-id 1973 \\
    --round 5 \\
    --season 2026 \\
    --date 2026-04-18 \\
    --sport-role visitante \\
    [--sport-city "BH"] \\
    [--accent-color "#007A37"]

Lê dados de:
  data/curated/opponents_2026/{team-key}/matches.csv
  data/curated/opponents_2026/{team-key}/team_match_stats.csv
  data/curated/opponents_2026/{team-key}/player_match_stats.csv  (opcional)

Gera em:
  pending_posts/{date}_raio-x-{team-key}/
    01_cover.png  02_campanha.png  03_mandante_vis.png
    04_ultimos5.png  05_xg.png  06_jogadores.png
"""

import argparse
import os
import sys
from collections import deque
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── Cores por time (accent) — expandir conforme necessário ──────────────────
TEAM_ACCENT_COLORS = {
    "vila-nova":   "#8B0000",
    "america-mg":  "#007A37",
    "avai":        "#003DA5",
    "crb":         "#1A237E",
    "sport":       "#F5C400",
}

# ─── Paleta @SportRecifeLab ───────────────────────────────────────────────────
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

FIG_W, FIG_H = 9.0, 9.0
DPI = 120
FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

# preenchido em main()
OUT_DIR = ""


# ─── Carregamento de dados ────────────────────────────────────────────────────

def _load_csvs(team_key: str):
    base = f"data/curated/opponents_2026/{team_key}"
    matches = pd.read_csv(f"{base}/matches.csv")
    stats   = pd.read_csv(f"{base}/team_match_stats.csv")
    try:
        players = pd.read_csv(f"{base}/player_match_stats.csv")
    except FileNotFoundError:
        players = None
    return matches, stats, players


def _compute_season(matches: pd.DataFrame, stats: pd.DataFrame):
    """Retorna dict com estatísticas agregadas da temporada do adversário."""
    done = matches[matches["status"] == "completed"].copy()
    if done.empty:
        return {}

    done["gf"] = np.where(done["is_home_team"], done["home_score"], done["away_score"])
    done["ga"] = np.where(done["is_home_team"], done["away_score"], done["home_score"])

    # Recalcula team_outcome dos placares (mais confiável que a coluna que pode estar vazia)
    done["_outcome"] = np.where(
        done["gf"] > done["ga"], "win",
        np.where(done["gf"] == done["ga"], "draw", "loss")
    )

    wins   = int((done["_outcome"] == "win").sum())
    draws  = int((done["_outcome"] == "draw").sum())
    losses = int((done["_outcome"] == "loss").sum())
    total  = wins + draws + losses
    gf     = int(done["gf"].sum())
    ga     = int(done["ga"].sum())
    pts    = wins * 3 + draws
    aprov  = pts / (total * 3) * 100 if total else 0

    # Competições e contagens
    comp_counts = done.groupby("competition_name").size().sort_values(ascending=False)
    comps = [(name, int(n)) for name, n in comp_counts.items()]

    # Stats de time: separar linhas do adversário vs oponente em cada partida
    # is_home em team_match_stats indica se aquele time era mandante
    # is_home_team em matches indica se o adversário era mandante
    joined = stats.merge(
        done[["match_code", "is_home_team"]].rename(columns={"match_code": "match_id"}),
        on="match_id", how="inner"
    )
    own = joined[joined["is_home"] == joined["is_home_team"]]
    opp = joined[joined["is_home"] != joined["is_home_team"]]

    xg_avg   = own["expected_goals"].mean() if not own.empty else 0
    xga_avg  = opp["expected_goals"].mean() if not opp.empty else 0
    poss_avg = own["possession"].mean() if not own.empty else 50
    shots_avg = own["shots_total"].mean() if not own.empty else 0
    sot_avg   = own["shots_on_target"].mean() if not own.empty else 0
    sot_pct   = (sot_avg / shots_avg * 100) if shots_avg > 0 else 0

    # Home vs away breakdown
    home_done = done[done["is_home_team"]]
    away_done = done[~done["is_home_team"]]

    def _record(df):
        if df.empty:
            return {"w": 0, "d": 0, "l": 0, "gf": 0, "ga": 0, "n": 0}
        return {
            "w": int((df["_outcome"] == "win").sum()),
            "d": int((df["_outcome"] == "draw").sum()),
            "l": int((df["_outcome"] == "loss").sum()),
            "gf": int(df["gf"].sum()),
            "ga": int(df["ga"].sum()),
            "n": len(df),
        }

    home_rec = _record(home_done)
    away_rec = _record(away_done)

    home_pts   = home_rec["w"] * 3 + home_rec["d"]
    home_aprov = home_pts / (home_rec["n"] * 3) * 100 if home_rec["n"] else 0

    home_stats = joined[(joined["is_home"] == True) & (joined["is_home_team"] == True)]
    home_xg    = home_stats["expected_goals"].mean() if not home_stats.empty else 0
    home_xga   = joined[(joined["is_home"] == False) & (joined["is_home_team"] == True)]["expected_goals"].mean()
    home_poss  = home_stats["possession"].mean() if not home_stats.empty else 50

    return {
        "total": total, "wins": wins, "draws": draws, "losses": losses,
        "gf": gf, "ga": ga, "pts": pts, "aprov": aprov, "comps": comps,
        "xg_avg": xg_avg, "xga_avg": xga_avg, "poss_avg": poss_avg,
        "shots_avg": shots_avg, "sot_pct": sot_pct,
        "home": home_rec, "away": away_rec,
        "home_aprov": home_aprov, "home_xg": home_xg,
        "home_xga": home_xga, "home_poss": home_poss,
    }


def _last5(matches: pd.DataFrame):
    done = matches[matches["status"] == "completed"].copy()
    done["dt"] = pd.to_datetime(done["match_date_utc"], utc=True)
    done["gf"] = np.where(done["is_home_team"], done["home_score"], done["away_score"])
    done["ga"] = np.where(done["is_home_team"], done["away_score"], done["home_score"])
    done["_outcome"] = np.where(
        done["gf"] > done["ga"], "win",
        np.where(done["gf"] == done["ga"], "draw", "loss")
    )
    done = done.sort_values("dt", ascending=False).head(5)
    rows = []
    for _, r in done.iterrows():
        rows.append({
            "date":    r["dt"].strftime("%d/%m"),
            "comp":    str(r["competition_name"]).split(",")[0][:18],
            "home":    r["home_team"],
            "hs":      int(r["home_score"]) if pd.notna(r["home_score"]) else 0,
            "away":    r["away_team"],
            "as_":     int(r["away_score"]) if pd.notna(r["away_score"]) else 0,
            "is_home": bool(r["is_home_team"]),
            "outcome": str(r["_outcome"]),
        })
    return rows


def _top_players(players: pd.DataFrame, matches: pd.DataFrame, team_name_hint: str):
    """Retorna lista de até 3 jogadores destaque do adversário."""
    if players is None or players.empty:
        return []

    done = matches[matches["status"] == "completed"][["match_code", "is_home_team"]]
    pj = players.merge(
        done.rename(columns={"match_code": "match_code"}),
        left_on="match_code", right_on="match_code", how="inner"
    )

    # Filtra linhas do adversário (is_home == is_home_team)
    own = pj[pj["is_home"] == pj["is_home_team"]].copy()
    if own.empty:
        # fallback: tenta pelo nome de time
        own = pj[pj["team_name"].str.contains(team_name_hint[:6], na=False, case=False)]

    if own.empty:
        return []

    # Agrega por jogador
    agg = own.groupby(["player_id", "player_name", "position", "jersey_number"]).agg(
        apps=("minutes_played", "count"),
        minutes=("minutes_played", "sum"),
        rating=("rating", "mean"),
        shots=("total_shots", "sum"),
        assists=("goal_assist", "sum"),
        recoveries=("ball_recovery", "sum"),
        passes_acc=("accurate_pass", "sum"),
    ).reset_index()

    agg = agg[agg["apps"] >= 2].sort_values("rating", ascending=False)

    def _role(row):
        pos = str(row["position"])
        if pos == "G":
            return "GOLEIRO TITULAR", LGRAY
        if pos == "F":
            return "PRINCIPAL FINALIZADOR", RED
        if pos == "D":
            return "MURO DEFENSIVO", LGRAY
        if agg["assists"].max() > 0 and row["assists"] == agg["assists"].max():
            return "MOTOR CRIATIVO", YELLOW
        return "DESTAQUE DA TEMPORADA", YELLOW

    role_colors = [YELLOW, RED, LGRAY]
    result = []
    for i, (_, row) in enumerate(agg.head(3).iterrows()):
        label, label_color = _role(row)
        border = role_colors[i]
        parts  = str(row["player_name"]).upper().split()
        name1  = parts[0] if parts else "?"
        name2  = " ".join(parts[1:]) if len(parts) > 1 else ""

        pos_map = {"G": "GOLEIRO", "D": "DEFENSOR", "M": "MEIA", "F": "ATACANTE"}
        pos_label = pos_map.get(str(row["position"]), str(row["position"]))

        stats_list = [("JOGOS", str(int(row["apps"])))]
        if row["assists"] > 0:
            stats_list.append(("ASSISTÊNCIAS", str(int(row["assists"]))))
        elif row["shots"] > 0:
            stats_list.append(("CHUTES", str(int(row["shots"]))))
        else:
            stats_list.append(("RECUPERAÇÕES", str(int(row["recoveries"]))))
        stats_list.append(("MINUTOS", str(int(row["minutes"]))))

        result.append({
            "name1": name1, "name2": name2,
            "pos": pos_label,
            "jersey": str(int(row["jersey_number"])) if pd.notna(row["jersey_number"]) else "?",
            "rating": f"{row['rating']:.2f}",
            "stats": stats_list,
            "label": label, "label_color": label_color, "border": border,
        })
    return result


# ─── Helpers de desenho ───────────────────────────────────────────────────────

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
                visited[y, x] = True; queue.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if is_white[y, x] and not visited[y, x]:
                visited[y, x] = True; queue.append((y, x))
    while queue:
        y, x = queue.popleft()
        data[y, x, 3] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True; queue.append((ny, nx))
    return Image.fromarray(data, "RGBA")


def _load_logo(team_id: int, size: int = 220):
    path = f"data/cache/logos/{team_id}.png"
    if not HAS_PIL or not os.path.exists(path):
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = _remove_bg_floodfill(img, thresh=25)
        return np.array(img.resize((size, size), Image.LANCZOS))
    except Exception:
        return None


def _new_fig():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    return fig, ax


def _add_watermark(fig):
    if not HAS_PIL or not os.path.exists("sportrecifelab_avatar.png"):
        return
    try:
        img = Image.open("sportrecifelab_avatar.png").convert("RGBA")
        arr = np.array(img.resize((60, 60), Image.LANCZOS))
        ax = fig.add_axes([0.05, 0.025, 0.07, 0.07])
        ax.imshow(arr); ax.axis("off")
    except Exception:
        pass


def _label(ax, x, y, text, color=GRAY, size=8, weight="normal",
           family=FONT_BODY, ha="center", va="center", alpha=1.0, zorder=4):
    ax.text(x, y, text, color=color, fontsize=size, fontweight=weight,
            fontfamily=family, ha=ha, va=va, transform=ax.transAxes,
            alpha=alpha, zorder=zorder)


def _hline(ax, y, x0=0.07, x1=0.93, color=YELLOW, lw=0.7, alpha=0.35):
    ax.plot([x0, x1], [y, y], color=color, linewidth=lw, alpha=alpha,
            transform=ax.transAxes, zorder=3)


def _badge(ax, x, y, text, bg=YELLOW, fg="#111111", size=8.5, pad=0.3):
    ax.text(x, y, text, color=fg, fontsize=size, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center",
            bbox=dict(boxstyle=f"round,pad={pad}", facecolor=bg, edgecolor="none", alpha=0.95),
            transform=ax.transAxes, zorder=5)


def _footer(ax):
    ax.text(0.84, 0.038, "SofaScore · @SportRecifeLab", color=DGRAY, fontsize=7,
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=4)


def _save(fig, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, name)
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"  OK {path}")


def _result_color(outcome):
    return {"win": GREEN, "draw": YELLOW, "loss": RED}.get(outcome, GRAY)


def _result_label(outcome):
    return {"win": "V", "draw": "E", "loss": "D"}.get(outcome, "?")


def _shield_placeholder(ax, team_name: str, accent: str, cx=0.195, cy=0.340, r=0.130):
    shield = plt.Polygon([
        [cx, cy + r], [cx + r, cy + r * 0.55], [cx + r, cy - r * 0.25],
        [cx, cy - r], [cx - r, cy - r * 0.25], [cx - r, cy + r * 0.55],
    ], closed=True, facecolor=accent, edgecolor=LGRAY,
       linewidth=1.5, alpha=0.85, zorder=3, transform=ax.transAxes)
    ax.add_patch(shield)
    initials = "".join(w[0] for w in team_name.split()[:2])
    ax.text(cx, cy, initials, color=WHITE, fontsize=32, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4)


# ─── Card 01 — COVER ─────────────────────────────────────────────────────────

def card_cover(cfg: dict, s: dict):
    fig, ax = _new_fig()

    poly = plt.Polygon([[0, 0.58], [0, 0.68], [0.45, 0.68], [0.55, 0.58]],
                       closed=True, facecolor=cfg["accent"], alpha=0.06, zorder=1)
    ax.add_patch(poly)
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003, facecolor=YELLOW, zorder=3))

    _label(ax, 0.50, 0.950, f"SÉRIE B 2026  ·  RODADA {cfg['round']}",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)

    ax.text(0.50, 0.840, "RAIO-X", color=YELLOW, fontsize=96, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center", transform=ax.transAxes, zorder=4,
            path_effects=[pe.withStroke(linewidth=4, foreground=BG)])

    # Ajusta fontsize para nomes longos
    tname_fs = 44 if len(cfg["team_name"]) <= 12 else (34 if len(cfg["team_name"]) <= 16 else 26)
    ax.text(0.50, 0.728, cfg["team_name"], color=WHITE, fontsize=tname_fs, fontweight="bold",
            fontfamily=FONT_TITLE, ha="center", va="center", transform=ax.transAxes, zorder=4)

    _hline(ax, 0.690, alpha=0.55)
    role_txt = "VISITANTE" if cfg["sport_role"] == "visitante" else "MANDANTE"
    city_txt = f" EM {cfg['sport_city'].upper()}" if cfg.get("sport_city") else ""
    _label(ax, 0.50, 0.648, f"SPORT JOGA COMO {role_txt}{city_txt}",
           color=LGRAY, size=12.5, weight="bold", family=FONT_TITLE)

    logo_arr = _load_logo(cfg["team_id"])
    if logo_arr is not None:
        try:
            logo_ax = fig.add_axes([0.04, 0.17, 0.28, 0.28])
            logo_ax.imshow(logo_arr); logo_ax.set_facecolor(BG); logo_ax.axis("off")
        except Exception:
            _shield_placeholder(ax, cfg["team_name"], cfg["accent"])
    else:
        _shield_placeholder(ax, cfg["team_name"], cfg["accent"])

    # Stats: campanha (todas comps), saldo, aproveitamento, xG/jogo
    saldo = s["gf"] - s["ga"]
    saldo_str = f"+{saldo}" if saldo >= 0 else str(saldo)
    saldo_color = GREEN if saldo >= 0 else RED
    xg_color = GREEN if s.get("xg_avg", 0) >= 1.5 else (YELLOW if s.get("xg_avg", 0) >= 1.0 else RED)
    stats_boxes = [
        (f"{s['wins']}V  {s['draws']}E  {s['losses']}D", "CAMPANHA 2026",   YELLOW),
        (saldo_str,                                        "SALDO DE GOLS",   saldo_color),
        (f"{s['aprov']:.0f}%",                            "APROVEITAMENTO",  LGRAY),
        (f"{s.get('xg_avg', 0):.2f}",                    "xG / JOGO",       xg_color),
    ]
    sx, sy_start, row_gap = 0.72, 0.570, 0.112
    for k, (val, lbl, color) in enumerate(stats_boxes):
        sy = sy_start - k * row_gap
        ax.add_patch(FancyBboxPatch((sx - 0.21, sy - 0.044), 0.42, 0.086,
                                    boxstyle="round,pad=0.01", facecolor=CARD2,
                                    edgecolor=DGRAY, linewidth=0.6, zorder=2))
        ax.text(sx, sy + 0.010, val, color=color, fontsize=18, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(sx, sy - 0.025, lbl, color=GRAY, fontsize=7.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

    _footer(ax); _add_watermark(fig)
    _save(fig, "01_cover.png")


# ─── Card 02 — CAMPANHA ───────────────────────────────────────────────────────

def card_campanha(cfg: dict, s: dict):
    fig, ax = _new_fig()
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003, facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "TEMPORADA 2026  ·  TODAS AS COMPETIÇÕES",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.870, cfg["team_name"], color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.828, f"{s['total']} PARTIDAS DISPUTADAS", color=GRAY, size=10, family=FONT_BODY)
    _hline(ax, 0.805)

    results = [
        (s["wins"],   "VITÓRIAS",  GREEN, "V"),
        (s["draws"],  "EMPATES",   YELLOW, "E"),
        (s["losses"], "DERROTAS",  RED, "D"),
    ]
    xs = [0.20, 0.50, 0.80]
    for (n, lbl, color, _), x in zip(results, xs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.60), 0.26, 0.185,
                                    boxstyle="round,pad=0.01", facecolor=CARD2,
                                    edgecolor=color, linewidth=2.0, zorder=2))
        ax.text(x, 0.720, str(n), color=color, fontsize=56, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.622, lbl, color=LGRAY, fontsize=9, fontfamily=FONT_BODY,
                fontweight="bold", ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _hline(ax, 0.590)
    _label(ax, 0.50, 0.558,
           f"{s['pts']} pontos  ·  {s['aprov']:.0f}% de aproveitamento",
           color=LGRAY, size=10.5, weight="bold", family=FONT_BODY)
    _hline(ax, 0.535, alpha=0.25)

    saldo = s["gf"] - s["ga"]
    gol_data = [
        ("GOLS\nMARCADOS", str(s["gf"]),  YELLOW),
        ("SALDO\nDE GOLS",  f"+{saldo}" if saldo >= 0 else str(saldo), GREEN if saldo >= 0 else RED),
        ("GOLS\nSOFRIDOS",  str(s["ga"]),  RED),
    ]
    for (lbl, val, color), x in zip(gol_data, xs):
        ax.text(x, 0.465, val, color=color, fontsize=40, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.398, lbl, color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4, linespacing=1.4)

    _hline(ax, 0.365, alpha=0.25)

    comps = s.get("comps", [])[:4]
    if comps:
        cx_list = [0.16, 0.39, 0.62, 0.84][:len(comps)]
        for (comp, n), x in zip(comps, cx_list):
            ax.text(x, 0.330, f"{n}j", color=YELLOW, fontsize=14, fontweight="black",
                    fontfamily=FONT_TITLE, ha="center", va="center",
                    transform=ax.transAxes, zorder=4)
            comp_short = comp[:16]
            ax.text(x, 0.293, comp_short, color=GRAY, fontsize=8, fontfamily=FONT_BODY,
                    ha="center", va="center", transform=ax.transAxes, zorder=4)

    _footer(ax); _add_watermark(fig)
    _save(fig, "02_campanha.png")


# ─── Card 03 — MANDANTE / VISITANTE ──────────────────────────────────────────

def card_mandante_vis(cfg: dict, s: dict):
    fig, ax = _new_fig()
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003, facecolor=YELLOW, zorder=3))

    # Se Sport joga visitante, o adversário é mandante → mostramos stats como mandante
    if cfg["sport_role"] == "visitante":
        rec = s["home"]
        label_ctx = "COMO MANDANTE"
        aprov_pct = s["home_aprov"]
        xg_show   = s["home_xg"]
        xga_show  = s["home_xga"]
        poss_show  = s["home_poss"]
        city_note  = f"em {cfg['sport_city']}" if cfg.get("sport_city") else "em casa"
        sub_note   = f"Sport joga {city_note} — como o adversário se sai em casa?"
    else:
        rec = s["away"]
        label_ctx = "COMO VISITANTE"
        aprov_away = (rec["w"] * 3 + rec["d"]) / (rec["n"] * 3) * 100 if rec["n"] else 0
        aprov_pct  = aprov_away
        # stats visitante: usamos médias gerais como proxy (away não tem xG separado ainda)
        xg_show    = s["xg_avg"]
        xga_show   = s["xga_avg"]
        poss_show  = s["poss_avg"]
        sub_note   = "Sport recebe o adversário — como ele se sai como visitante?"

    _label(ax, 0.50, 0.950, f"{cfg['team_name']} {label_ctx}  ·  2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.876, cfg["team_name"], color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.836, sub_note, color=GRAY, size=9.5, family=FONT_BODY)
    _hline(ax, 0.812)

    aprov_color = GREEN if aprov_pct >= 60 else (YELLOW if aprov_pct >= 40 else RED)
    ax.text(0.50, 0.738, f"{aprov_pct:.0f}%", color=aprov_color, fontsize=80,
            fontweight="black", fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=4)
    _label(ax, 0.50, 0.683,
           f"APROVEITAMENTO {label_ctx}  ·  {rec['n']} JOGOS",
           color=GRAY, size=9, family=FONT_BODY)
    _hline(ax, 0.660, alpha=0.4)

    vxs = [0.22, 0.50, 0.78]
    ved = [(str(rec["w"]), "VITÓRIAS", GREEN), (str(rec["d"]), "EMPATES", YELLOW),
           (str(rec["l"]), "DERROTAS", RED)]
    for (n, lbl, color), x in zip(ved, vxs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.570), 0.26, 0.082,
                                    boxstyle="round,pad=0.01", facecolor=CARD2,
                                    edgecolor=color, linewidth=2.0, zorder=2))
        ax.text(x, 0.622, n, color=color, fontsize=38, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.582, lbl, color=LGRAY, fontsize=8, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
    _hline(ax, 0.558, alpha=0.3)

    saldo = rec["gf"] - rec["ga"]
    gol_cols = [
        (str(rec["gf"]),  "GOLS MARCADOS", YELLOW),
        (str(rec["ga"]),  "GOLS SOFRIDOS", RED),
        (f"+{saldo}" if saldo >= 0 else str(saldo), "SALDO", GREEN if saldo >= 0 else RED),
    ]
    for (val, lbl, color), x in zip(gol_cols, vxs):
        ax.text(x, 0.508, val, color=color, fontsize=36, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.468, lbl, color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
    _hline(ax, 0.446, alpha=0.3)

    gf_per = rec["gf"] / rec["n"] if rec["n"] else 0
    ga_per = rec["ga"] / rec["n"] if rec["n"] else 0
    med_cols = [
        (f"{gf_per:.1f}", "GOLS MARC/JOGO"),
        (f"{ga_per:.1f}", "GOLS SOF/JOGO"),
        (f"{poss_show:.0f}%", "POSSE MÉDIA"),
    ]
    for (val, lbl), x in zip(med_cols, vxs):
        ax.text(x, 0.408, val, color=LGRAY, fontsize=24, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.374, lbl, color=GRAY, fontsize=8, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
    _hline(ax, 0.350, alpha=0.3)

    xg_color = GREEN if xg_show >= 1.5 else (YELLOW if xg_show >= 1.0 else RED)
    xga_color = RED if xga_show >= 1.5 else (YELLOW if xga_show >= 1.0 else GREEN)
    xg_cols = [
        (f"{xg_show:.2f}",  "xG MÉDIO / JOGO",   xg_color),
        (f"{xga_show:.2f}", "xG SOFRIDO / JOGO",  xga_color),
        (f"{s['sot_pct']:.0f}%", "PRECISÃO CHUTES", LGRAY),
    ]
    for (val, lbl, color), x in zip(xg_cols, vxs):
        ax.text(x, 0.310, val, color=color, fontsize=24, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.276, lbl, color=GRAY, fontsize=7.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
    _hline(ax, 0.252, alpha=0.2)

    # Callout automático
    if xga_show >= 1.3 and rec["n"] >= 2:
        callout1 = "DEFESA VULNERÁVEL — OPORTUNIDADE PARA O SPORT"
        callout2 = f"Adversário cede {xga_show:.2f} xG/jogo {label_ctx.lower()} — pressão pode ser decisiva"
        call_color = GREEN
    else:
        total_goals = rec["gf"] + rec["ga"]
        avg_goals   = total_goals / rec["n"] if rec["n"] else 0
        callout1 = f"MÉDIA DE {avg_goals:.1f} GOLS POR JOGO {label_ctx}"
        callout2 = f"{rec['n']} partidas com {total_goals} gols no total — jogo pode ser movimentado"
        call_color = YELLOW

    ax.add_patch(FancyBboxPatch((0.07, 0.155), 0.86, 0.086,
                                boxstyle="round,pad=0.01", facecolor=CARD2,
                                edgecolor=call_color, linewidth=1.2, zorder=3))
    ax.text(0.50, 0.200, callout1, color=call_color, fontsize=9.5, fontweight="bold",
            fontfamily=FONT_BODY, ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.168, callout2, color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax); _add_watermark(fig)
    _save(fig, "03_mandante_vis.png")


# ─── Card 04 — ÚLTIMOS 5 ─────────────────────────────────────────────────────

def card_ultimos5(cfg: dict, games: list):
    fig, ax = _new_fig()
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003, facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "FORMA RECENTE  ·  ÚLTIMOS 5 JOGOS",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.875, cfg["team_name"], color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _hline(ax, 0.845)

    row_h = 0.130; box_h = 0.108; half_h = box_h / 2; y_start = 0.806
    for i, g in enumerate(games[:5]):
        y = y_start - i * row_h
        y_bot = y - half_h
        outcome_color = _result_color(g["outcome"])
        outcome_label = _result_label(g["outcome"])
        row_bg = CARD if i % 2 == 0 else CARD2
        ax.add_patch(FancyBboxPatch((0.07, y_bot), 0.86, box_h,
                                    boxstyle="round,pad=0.005", facecolor=row_bg,
                                    edgecolor="none", zorder=2))
        ax.add_patch(patches.Rectangle((0.07, y_bot), 0.012, box_h,
                                       facecolor=outcome_color, zorder=3))
        _badge(ax, 0.906, y, outcome_label, bg=outcome_color,
               fg=("#111111" if g["outcome"] == "draw" else WHITE), size=11, pad=0.38)

        date_y = y + half_h * 0.38; comp_y = y - half_h * 0.40
        ax.text(0.118, date_y, g["date"], color=LGRAY, fontsize=9, fontweight="bold",
                fontfamily=FONT_BODY, ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.118, comp_y, g["comp"], color=DGRAY, fontsize=7, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)

        h_color = YELLOW if g["is_home"] else LGRAY
        a_color = LGRAY if g["is_home"] else YELLOW
        h_weight = "black" if g["is_home"] else "normal"
        a_weight = "normal" if g["is_home"] else "black"

        ax.text(0.345, y, g["home"], color=h_color, fontsize=10.5, fontweight=h_weight,
                fontfamily=FONT_BODY, ha="right", va="center", transform=ax.transAxes, zorder=4)
        ax.text(0.500, y, f"{g['hs']} – {g['as_']}", color=WHITE, fontsize=14,
                fontweight="black", fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(0.655, y, g["away"], color=a_color, fontsize=10.5, fontweight=a_weight,
                fontfamily=FONT_BODY, ha="left", va="center", transform=ax.transAxes, zorder=4)

    last_bot = y_start - min(len(games), 5) * row_h + row_h - half_h
    hline_y = last_bot - 0.030
    pills_y = hline_y - 0.048
    _hline(ax, hline_y, alpha=0.3)
    _label(ax, 0.50, hline_y - 0.018, "FORMA NOS ÚLTIMOS 5:", color=GRAY, size=9, family=FONT_BODY)

    pill_colors = [_result_color(g["outcome"]) for g in games[:5]]
    pill_labels = [_result_label(g["outcome"]) for g in games[:5]]
    pill_xs = [0.32, 0.41, 0.50, 0.59, 0.68][:len(games)]
    for px, pl, pc in zip(pill_xs, pill_labels, pill_colors):
        ax.add_patch(patches.Circle((px, pills_y), 0.030, facecolor=pc, alpha=0.20,
                                    transform=ax.transAxes, zorder=3))
        ax.text(px, pills_y, pl, color=pc, fontsize=13, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax); _add_watermark(fig)
    _save(fig, "04_ultimos5.png")


# ─── Card 05 — ANÁLISE xG ────────────────────────────────────────────────────

def card_xg(cfg: dict, s: dict):
    fig, ax = _new_fig()
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003, facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "ANÁLISE OFENSIVA E xG  ·  2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.880, cfg["team_name"], color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.840, f"{s['total']} jogos — todas as competições",
           color=GRAY, size=9.5, family=FONT_BODY)
    _hline(ax, 0.815)

    poss_color = GREEN if s["poss_avg"] >= 55 else (YELLOW if s["poss_avg"] >= 45 else RED)
    xg_color   = GREEN if s["xg_avg"] >= 1.5 else (YELLOW if s["xg_avg"] >= 1.0 else RED)
    sot_color  = GREEN if s["sot_pct"] >= 40 else (YELLOW if s["sot_pct"] >= 30 else RED)

    metrics_top = [
        ("POSSE MÉDIA",     f"{s['poss_avg']:.0f}%", poss_color,
         "controla o jogo" if s["poss_avg"] >= 52 else "disputa equilibrada"),
        ("xG / JOGO",       f"{s['xg_avg']:.2f}",    xg_color,
         "eficiente" if s["xg_avg"] >= 1.5 else "baixa criação"),
        ("PRECISÃO CHUTES", f"{s['sot_pct']:.0f}%",  sot_color,
         "na direção certa" if s["sot_pct"] >= 35 else "impreciso"),
    ]
    xs = [0.20, 0.50, 0.80]
    for (lbl, val, color, sub), x in zip(metrics_top, xs):
        ax.add_patch(FancyBboxPatch((x - 0.13, 0.665), 0.26, 0.130,
                                    boxstyle="round,pad=0.01", facecolor=CARD2,
                                    edgecolor=color, linewidth=1.8, zorder=2))
        ax.text(x, 0.755, val, color=color, fontsize=38, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.687, lbl, color=LGRAY, fontsize=8, fontfamily=FONT_BODY,
                fontweight="bold", ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.667, sub, color=DGRAY, fontsize=7.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
    _hline(ax, 0.648, alpha=0.4)

    # Narrativa ofensiva automática
    if s["poss_avg"] >= 55 and s["xg_avg"] < 1.2:
        headline = "DOMINA A BOLA, MAS CRIA POUCO"
        body = f"Alta posse ({s['poss_avg']:.0f}%) não se converte em criação — apenas {s['xg_avg']:.2f} xG/jogo."
    elif s["xg_avg"] >= 1.8:
        headline = "TIME OFENSIVAMENTE PERIGOSO"
        body = f"Gera {s['xg_avg']:.2f} xG por jogo — Sport precisará de atenção defensiva."
    else:
        diff = s["xg_avg"] - s["xga_avg"]
        signal = "positivo" if diff >= 0 else "negativo"
        headline = f"SALDO xG {signal.upper()} NA TEMPORADA"
        body = f"{s['xg_avg']:.2f} xG gerado vs {s['xga_avg']:.2f} xG cedido por jogo."

    _label(ax, 0.50, 0.617, headline, color=LGRAY, size=12, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.583, body, color=GRAY, size=9, family=FONT_BODY)
    _hline(ax, 0.540, alpha=0.25)

    _label(ax, 0.50, 0.508, "CONTEXTO DEFENSIVO", color=GRAY, size=8.5, weight="bold", family=FONT_BODY)
    xga_color = RED if s["xga_avg"] >= 1.5 else (YELLOW if s["xga_avg"] >= 1.0 else GREEN)
    def_xs = [0.22, 0.50, 0.78]
    def_data = [
        (f"{s['xga_avg']:.2f}", "xG SOFRIDO / JOGO",    xga_color),
        (f"{s['shots_avg']:.1f}", "CHUTES SOFRIDOS / JOGO", RED if s["shots_avg"] >= 12 else LGRAY),
        (f"{100 - s['poss_avg']:.0f}%", "POSSE CEDIDA",  LGRAY),
    ]
    for (val, lbl, color), x in zip(def_data, def_xs):
        ax.text(x, 0.462, val, color=color, fontsize=24, fontweight="black",
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(x, 0.427, lbl, color=GRAY, fontsize=7.5, fontfamily=FONT_BODY,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
    _hline(ax, 0.400, alpha=0.25)

    # Callout Sport
    if s["xga_avg"] >= 1.3:
        c1 = "PONTO DE ATENÇÃO PARA O SPORT"
        c2 = f"Adversário cede {s['xga_avg']:.2f} xG/jogo — pressão alta pode ser eficaz"
        c_edge = GREEN; c_bg = "#001a08"
    else:
        c1 = "ADVERSÁRIO DEFENSIVAMENTE SÓLIDO"
        c2 = f"Apenas {s['xga_avg']:.2f} xG cedido/jogo — Sport precisará de paciência"
        c_edge = YELLOW; c_bg = "#1a1600"

    ax.add_patch(FancyBboxPatch((0.07, 0.285), 0.86, 0.103,
                                boxstyle="round,pad=0.01", facecolor=c_bg,
                                edgecolor=c_edge, linewidth=1.5, zorder=3))
    ax.text(0.50, 0.340, c1, color=c_edge, fontsize=11.5, fontweight="black",
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(0.50, 0.298, c2, color=LGRAY, fontsize=8.8, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _footer(ax); _add_watermark(fig)
    _save(fig, "05_xg.png")


# ─── Card 06 — JOGADORES ─────────────────────────────────────────────────────

def card_jogadores(cfg: dict, players: list):
    fig, ax = _new_fig()
    ax.add_patch(patches.Rectangle((0.05, 0.91), 0.90, 0.003, facecolor=YELLOW, zorder=3))
    _label(ax, 0.50, 0.950, "FIQUE DE OLHO  ·  DESTAQUES 2026",
           color=YELLOW, size=10.5, weight="bold", family=FONT_TITLE)
    _label(ax, 0.50, 0.875, cfg["team_name"], color=WHITE, size=28, weight="bold", family=FONT_TITLE)
    _hline(ax, 0.845)

    if not players:
        _label(ax, 0.50, 0.50, "DADOS DE JOGADORES NÃO DISPONÍVEIS",
               color=GRAY, size=14, weight="bold", family=FONT_TITLE)
        _footer(ax); _add_watermark(fig)
        _save(fig, "06_jogadores.png")
        return

    card_xs = [0.20, 0.50, 0.80]; card_w = 0.270
    card_bot = 0.140; card_top = 0.800; card_h = card_top - card_bot

    for p, cx in zip(players, card_xs):
        x0 = cx - card_w / 2; x1 = cx + card_w / 2
        ax.add_patch(FancyBboxPatch((x0, card_bot), card_w, card_h,
                                    boxstyle="round,pad=0.01", facecolor=CARD2,
                                    edgecolor=p["border"], linewidth=1.5, zorder=2))
        ax.add_patch(patches.Rectangle((x0 + 0.005, card_top - 0.038),
                                       card_w - 0.010, 0.033,
                                       facecolor=p["border"], alpha=0.18, zorder=3))
        fg = WHITE if p["border"] != YELLOW else "#111111"
        _badge(ax, cx, card_top - 0.022, f"#{p['jersey']}",
               bg=p["border"], fg=fg, size=9, pad=0.30)

        ax.text(cx, card_top - 0.075, p["name1"], color=WHITE, fontsize=15,
                fontweight="black", fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(cx, card_top - 0.108, p["name2"] or p["name1"], color=p["border"],
                fontsize=15, fontweight="black", fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=4)
        ax.text(cx, card_top - 0.138, p["pos"], color=GRAY, fontsize=7.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        sep1 = card_top - 0.156
        ax.plot([x0 + 0.018, x1 - 0.018], [sep1, sep1],
                color=DGRAY, linewidth=0.6, alpha=0.6, transform=ax.transAxes, zorder=3)

        r_center = sep1 - 0.040
        ax.add_patch(FancyBboxPatch((cx - 0.085, r_center - 0.022), 0.170, 0.040,
                                    boxstyle="round,pad=0.006", facecolor="#111111",
                                    edgecolor=p["border"], linewidth=0.8, zorder=3))
        ax.text(cx, r_center, f"RATING  {p['rating']}", color=p["border"], fontsize=9,
                fontweight="bold", fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)
        ax.text(cx, r_center - 0.032, "média por jogo", color=DGRAY, fontsize=6.5,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

        sep2 = r_center - 0.052
        ax.plot([x0 + 0.018, x1 - 0.018], [sep2, sep2],
                color=DGRAY, linewidth=0.5, alpha=0.5, transform=ax.transAxes, zorder=3)

        stat_gap = 0.092; stat_top = sep2 - 0.020
        for j, (lbl, val) in enumerate(p["stats"]):
            val_y = stat_top - j * stat_gap; lbl_y = val_y - 0.030
            ax.text(cx, val_y, val, color=WHITE, fontsize=16, fontweight="black",
                    fontfamily=FONT_TITLE, ha="center", va="center",
                    transform=ax.transAxes, zorder=4)
            ax.text(cx, lbl_y, lbl, color=GRAY, fontsize=7, fontfamily=FONT_BODY,
                    ha="center", va="center", transform=ax.transAxes, zorder=4)
            if j < len(p["stats"]) - 1:
                div_y = lbl_y - 0.018
                ax.plot([x0 + 0.018, x1 - 0.018], [div_y, div_y],
                        color=DGRAY, linewidth=0.4, alpha=0.4,
                        transform=ax.transAxes, zorder=3)

        badge_y = card_bot + 0.040
        ax.add_patch(FancyBboxPatch((x0 + 0.015, badge_y - 0.020),
                                    card_w - 0.030, 0.038,
                                    boxstyle="round,pad=0.006", facecolor="#111111",
                                    edgecolor=p["border"], linewidth=0.8, alpha=0.9, zorder=3))
        ax.text(cx, badge_y, p["label"], color=p["label_color"], fontsize=8,
                fontweight="bold", fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=4)

    _footer(ax); _add_watermark(fig)
    _save(fig, "06_jogadores.png")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    global OUT_DIR

    parser = argparse.ArgumentParser(description="Raio-X genérico — @SportRecifeLab")
    parser.add_argument("--team-key",    required=True, help="Chave do time (ex: america-mg)")
    parser.add_argument("--team-name",   required=True, help="Nome em caixa alta (ex: AMERICA MINEIRO)")
    parser.add_argument("--team-id",     required=True, type=int, help="ID SofaScore do time")
    parser.add_argument("--round",       required=True, type=int, help="Rodada da Série B")
    parser.add_argument("--season",      default=2026,  type=int)
    parser.add_argument("--date",        default=datetime.today().strftime("%Y-%m-%d"))
    parser.add_argument("--sport-role",  default="visitante", choices=["mandante", "visitante"])
    parser.add_argument("--sport-city",  default="", help="Cidade do jogo se visitante (ex: BH)")
    parser.add_argument("--accent-color", default="",
                        help="Cor acento do time (hex). Se omitido, usa TEAM_ACCENT_COLORS ou YELLOW.")
    args = parser.parse_args()

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    accent = (args.accent_color.strip()
              or TEAM_ACCENT_COLORS.get(args.team_key, YELLOW))

    OUT_DIR = f"pending_posts/{args.date}_raio-x-{args.team_key}"

    cfg = {
        "team_key":  args.team_key,
        "team_name": args.team_name.upper(),
        "team_id":   args.team_id,
        "round":     args.round,
        "season":    args.season,
        "sport_role": args.sport_role,
        "sport_city": args.sport_city,
        "accent":    accent,
    }

    print(f"Carregando dados de opponents_2026/{args.team_key}/...")
    try:
        matches, stats, players_df = _load_csvs(args.team_key)
    except FileNotFoundError as e:
        sys.exit(f"Erro: {e}\nExecute primeiro: python -m src.main sync-opponent --team-key {args.team_key} --team-id {args.team_id} --season {args.season}")

    s       = _compute_season(matches, stats)
    games   = _last5(matches)
    players = _top_players(players_df, matches, args.team_name)

    if not s:
        sys.exit("Sem partidas concluídas nos dados. Verifique o sync-opponent.")

    print(f"Gerando 6 cards em {OUT_DIR}/")
    card_cover(cfg, s)
    card_campanha(cfg, s)
    card_mandante_vis(cfg, s)
    card_ultimos5(cfg, games)
    card_xg(cfg, s)
    card_jogadores(cfg, players)

    print(f"\nPronto. 6 cards gerados em: {OUT_DIR}/")
    print(f"  Campanha: {s['wins']}V {s['draws']}E {s['losses']}D | {s['gf']}:{s['ga']} gols")
    print(f"  xG médio: {s['xg_avg']:.2f} | Posse: {s['poss_avg']:.0f}%")
    print(f"  Jogadores detectados: {len(players)}")


if __name__ == "__main__":
    main()
