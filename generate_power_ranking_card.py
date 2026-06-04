"""
Power Ranking Série B 2026 — card visual

Critérios (redesenho jun/2026 — sem contagem dupla de xG):
  Força (70%)   = fusão Desempenho (xPts/MP) + Domínio (Net xG/MP), r≈0,99,
                  já ajustada pelo Calendário (SOS aplicado uma vez)
  Momento (30%) = Pts/MP nas últimas K rodadas (único sinal ortogonal)

Gera:
  data/curated/serie_b_2026/power_ranking.csv
  pending_posts/{date}_power-ranking-rN/
    01_power_ranking.png
    tweet.txt
    metadata.json

Uso:
  python generate_power_ranking_card.py
  python generate_power_ranking_card.py --sos-window 6
"""

import argparse
import datetime
import json
import math
import sys
from collections import deque
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
XPTS_PATH     = BASE_DIR / "data/curated/serie_b_2026/expected_points_table.csv"
MATCHES_PATH  = BASE_DIR / "data/curated/serie_b_2026/matches.csv"
STATS_PATH    = BASE_DIR / "data/curated/serie_b_2026/team_match_stats.csv"
RANKING_PATH  = BASE_DIR / "data/curated/serie_b_2026/power_ranking.csv"
LOGO_CACHE    = BASE_DIR / "data/cache/logos"
AVATAR_PATH   = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR     = datetime.date.today().strftime("%Y-%m-%d")

# ── IDs SofaScore ─────────────────────────────────────────────────────────────
TEAM_IDS = {
    "america-mg":              1973,
    "athletic-club":           342775,
    "atletico-go":             7314,
    "avai":                    7315,
    "botafogo-sp":             1979,
    "ceara":                   2001,
    "crb":                     22032,
    "clube-de-regatas-brasil": 22032,
    "criciuma":                1984,
    "cuiaba":                  49202,
    "fortaleza":               2020,
    "goias":                   1960,
    "novorizontino":           135514,
    "juventude":               1980,
    "londrina":                2022,
    "nautico":                 2011,
    "operario-pr":             39634,
    "ponte-preta":             1969,
    "sao-bernardo":            47504,
    "sport":                   1959,
    "vila-nova":               2021,
}

TEAM_NAME_OVERRIDES = {
    "clube-de-regatas-brasil": "CRB",
}

SPORT_KEY = "sport"

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
CARD   = "#161616"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
LGRAY  = "#CCCCCC"
GRAY   = "#888888"
DGRAY  = "#333333"
BLUE   = "#60A5FA"
GREEN  = "#22C55E"
ORANGE = "#F97316"
RED    = "#EF4444"

# ── Tier List ─────────────────────────────────────────────────────────────────
TIER_DEFS = [
    {
        "label": "CANDIDATO\nAO G2",
        "ranks": list(range(1, 5)),
        "color": YELLOW,
    },
    {
        "label": "BRIGAM PELOS\nPLAYOFFS",
        "ranks": list(range(5, 11)),
        "color": BLUE,
    },
    {
        "label": "MAROLA",
        "ranks": list(range(11, 17)),
        "color": LGRAY,
    },
    {
        "label": "MANUTENÇÃO\nÉ LUCRO",
        "ranks": list(range(17, 21)),
        "color": RED,
    },
]

TL_LOGO_SIZE = 80
TL_LOGO_ZOOM = 0.80

TL_FIG_W = 12.0
TL_FIG_H = 9.0

TL_LABEL_X1  = 0.232   # right edge of label column
TL_LOGO_X0   = 0.255   # left edge of logo area
TL_LOGO_X1   = 0.972   # right edge of logo area

TL_Y_TITLE    = 0.962
TL_Y_SUBTITLE = 0.940
TL_Y_DIV_TOP  = 0.920
TL_Y_DIV_BOT  = 0.068
TL_Y_FOOTER   = 0.038

_TIER_TOP_Y = TL_Y_DIV_TOP
_TIER_BOT_Y = TL_Y_DIV_BOT + 0.012
_TIER_H     = (_TIER_TOP_Y - _TIER_BOT_Y) / 4   # ≈ 0.210

# Dois componentes PONDERADOS (barras) + Calendário como modificador (dots).
# Força funde Desempenho (xPts/MP) + Domínio (Net xG/MP) — eram r≈0,99, contagem
# dupla — e já vem ajustada pelo calendário (SOS aplicado uma vez).
COMP_COLORS  = [YELLOW, BLUE]
COMP_LABELS  = ["Força", "Momento"]
COMP_KEYS    = ["n_forca", "n_form"]
COMP_WEIGHTS = [0.70, 0.30]
COMP_DESC    = [
    "xPts/MP + Net xG/MP, ajustada p/ SOS",
    "Pts/MP nas últimas 4 rodadas",
]
SOS_LABEL = "Calendário"
SOS_COLOR = ORANGE
SOS_DESC  = "Força dos adversários recentes"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

# ── Dimensões ─────────────────────────────────────────────────────────────────
FIG_W, FIG_H = 10.0, 11.0
DPI = 120

Y_TITLE     = 0.972
Y_SUBTITLE  = 0.950
Y_DIV_TOP   = 0.932
Y_HEADER    = 0.915
Y_FIRST_ROW = 0.882
ROW_H       = 0.0405
Y_DIV_BOT   = 0.082
Y_LEGEND    = 0.058
Y_FOOTER    = 0.028

X_RANK  = 0.032
X_LOGO  = 0.075
X_NAME  = 0.115   # left-align, end ~0.335

# Duas mini-barras ponderadas (Força, Momento) lado a lado
MINI_BAR_W   = 0.085
MINI_BAR_GAP = 0.015
X_MINI_START = 0.345
X_MINI = [X_MINI_START + i * (MINI_BAR_W + MINI_BAR_GAP) for i in range(2)]

# Coluna de dots do Calendário (SOS) — modificador embutido na Força
SOS_DOTS_X0 = 0.548   # centro do 1º dot
SOS_DOTS_W  = 0.072   # extensão dos 5 dots
SOS_N_DOTS  = 5

X_BAR0   = 0.638   # início da barra de power score
BAR_MAX  = 0.217   # largura máxima → termina em 0.855
X_SCORE  = 0.920   # centro do valor numérico
X_RIGHT  = 0.970

LOGO_SIZE = 36
LOGO_ZOOM = 0.85


# ── Imagem helpers ────────────────────────────────────────────────────────────

def _remove_bg(img: "Image.Image", thresh: int = 25) -> "Image.Image":
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    is_white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)
    visited = np.zeros((h, w), dtype=bool)
    q: deque = deque()
    for y in range(h):
        for x in (0, w - 1):
            if is_white[y, x] and not visited[y, x]:
                visited[y, x] = True; q.append((y, x))
    for x in range(w):
        for y in (0, h - 1):
            if is_white[y, x] and not visited[y, x]:
                visited[y, x] = True; q.append((y, x))
    while q:
        y, x = q.popleft()
        data[y, x, 3] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True; q.append((ny, nx))
    return Image.fromarray(data, "RGBA")


def _get_logo(team_key: str) -> "np.ndarray | None":
    if not HAS_PIL:
        return None
    tid = TEAM_IDS.get(team_key)
    if not tid:
        return None
    p = LOGO_CACHE / f"{tid}.png"
    if not p.exists():
        return None
    try:
        img = Image.open(p).convert("RGBA")
        img = _remove_bg(img)
        img = img.resize((LOGO_SIZE, LOGO_SIZE), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None


# ── Helpers de desenho ────────────────────────────────────────────────────────

def _hline(ax, y, x0=0.020, x1=0.970, color=YELLOW, lw=0.5, alpha=0.25):
    ax.plot([x0, x1], [y, y], color=color, lw=lw, alpha=alpha,
            transform=ax.transAxes, zorder=3)


def _place_logo(ax, arr: "np.ndarray", x: float, y: float):
    ab = AnnotationBbox(
        OffsetImage(arr, zoom=LOGO_ZOOM),
        (x, y), xycoords="axes fraction",
        frameon=False, zorder=6, box_alignment=(0.5, 0.5),
    )
    ax.add_artist(ab)


def _mini_bar(ax, x0: float, y: float, value: float, color: str):
    """Barra horizontal de componente normalizado [0,1]. Fundo track + fill."""
    bar_h = ROW_H * 0.38
    # track
    ax.add_patch(patches.Rectangle(
        (x0, y - bar_h / 2), MINI_BAR_W, bar_h,
        facecolor="#222222", edgecolor="none",
        transform=ax.transAxes, zorder=3,
    ))
    # fill
    if value > 0:
        ax.add_patch(patches.Rectangle(
            (x0, y - bar_h / 2), MINI_BAR_W * value, bar_h,
            facecolor=color, alpha=0.80, edgecolor="none",
            transform=ax.transAxes, zorder=4,
        ))


def _sos_dots(ax, y: float, level: int):
    """5 dots horizontais — quanto mais preenchidos, mais difícil o calendário.

    `level` em 1..5. Dots cheios em SOS_COLOR; vazios em cinza apagado.
    """
    step = SOS_DOTS_W / (SOS_N_DOTS - 1)
    # raio em fração de eixo, corrigido pelo aspect da figura para virar círculo
    r = 0.0052
    for i in range(SOS_N_DOTS):
        cx = SOS_DOTS_X0 + i * step
        filled = i < level
        ax.add_patch(patches.Ellipse(
            (cx, y), width=r * 2, height=r * 2 * (FIG_W / FIG_H),
            facecolor=SOS_COLOR if filled else "#2a2a2a",
            edgecolor="none", alpha=0.90 if filled else 1.0,
            transform=ax.transAxes, zorder=4,
        ))


def _power_bar(ax, x0: float, y: float, value_norm: float, is_sport: bool):
    """Barra principal de power score com preenchimento gradiente via retângulos."""
    bar_h = ROW_H * 0.48
    fill_w = BAR_MAX * value_norm

    # track
    ax.add_patch(patches.Rectangle(
        (x0, y - bar_h / 2), BAR_MAX, bar_h,
        facecolor="#1a1a1a", edgecolor="none",
        transform=ax.transAxes, zorder=3,
    ))

    if fill_w <= 0:
        return

    # Gradiente simulado com N fatias de opacidade crescente
    N = max(1, int(fill_w * 800))
    step = fill_w / N
    base_color = YELLOW if is_sport else LGRAY
    r, g, b = matplotlib.colors.to_rgb(base_color)

    for i in range(N):
        alpha = 0.25 + 0.75 * (i / N)
        ax.add_patch(patches.Rectangle(
            (x0 + i * step, y - bar_h / 2), step + 0.001, bar_h,
            facecolor=(r, g, b, alpha), edgecolor="none",
            transform=ax.transAxes, zorder=4,
        ))


def _get_logo_tier(team_key: str) -> "np.ndarray | None":
    """Larger logo for tier list card."""
    if not HAS_PIL:
        return None
    tid = TEAM_IDS.get(team_key)
    if not tid:
        return None
    p = LOGO_CACHE / f"{tid}.png"
    if not p.exists():
        return None
    try:
        img = Image.open(p).convert("RGBA")
        img = _remove_bg(img)
        img = img.resize((TL_LOGO_SIZE, TL_LOGO_SIZE), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None


# ── Tier List Card ─────────────────────────────────────────────────────────────

def generate_tier_card(df: pd.DataFrame, max_round: int, out_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(TL_FIG_W, TL_FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Título ────────────────────────────────────────────────────────────────
    ax.text(0.50, TL_Y_TITLE, "TIER LIST — POWER RANKING",
            color=YELLOW, fontsize=18, fontfamily=FONT_TITLE, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.50, TL_Y_SUBTITLE,
            f"Série B 2026  ·  Rodada {max_round}  ·  Força (70%) · Momento (30%) · ajuste por Calendário",
            color=GRAY, fontsize=8.0, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    ax.plot([0.018, 0.978], [TL_Y_DIV_TOP, TL_Y_DIV_TOP],
            color=YELLOW, lw=0.5, alpha=0.30, transform=ax.transAxes, zorder=3)

    # ── Tiers ─────────────────────────────────────────────────────────────────
    for t_idx, tier in enumerate(TIER_DEFS):
        y_top = _TIER_TOP_Y - t_idx * _TIER_H
        y_bot = y_top - _TIER_H
        y_mid = (y_top + y_bot) / 2
        color = tier["color"]

        # Content area background
        ax.add_patch(patches.Rectangle(
            (0.012, y_bot + 0.003), 0.963, _TIER_H - 0.006,
            facecolor=color, alpha=0.05, edgecolor="none",
            transform=ax.transAxes, zorder=1,
        ))

        # Label panel (stronger background)
        ax.add_patch(patches.Rectangle(
            (0.012, y_bot + 0.003), TL_LABEL_X1 - 0.012, _TIER_H - 0.006,
            facecolor=color, alpha=0.22, edgecolor="none",
            transform=ax.transAxes, zorder=2,
        ))

        # Vertical separator
        ax.plot([TL_LABEL_X1, TL_LABEL_X1], [y_bot + 0.004, y_top - 0.004],
                color=color, lw=1.5, alpha=0.55,
                transform=ax.transAxes, zorder=4)

        # Horizontal separator between tiers
        if t_idx < 3:
            ax.plot([0.012, 0.975], [y_bot, y_bot],
                    color=DGRAY, lw=0.7, alpha=0.80,
                    transform=ax.transAxes, zorder=3)

        # Label text
        label_x = TL_LABEL_X1 / 2
        ax.text(label_x, y_mid, tier["label"],
                color=color, fontsize=9.5, fontfamily=FONT_TITLE,
                fontweight="bold", ha="center", va="center",
                multialignment="center",
                transform=ax.transAxes, zorder=6)

        # ── Logos ─────────────────────────────────────────────────────────────
        tier_teams = df[df["rank_power"].isin(tier["ranks"])].sort_values("rank_power")
        n = len(tier_teams)
        if n == 0:
            continue

        logo_col_w = TL_LOGO_X1 - TL_LOGO_X0
        spacing = logo_col_w / n
        x_start = TL_LOGO_X0 + spacing / 2

        for li, (_, row) in enumerate(tier_teams.iterrows()):
            lx = x_start + li * spacing
            is_sport = row["team_key"] == SPORT_KEY

            logo = _get_logo_tier(row["team_key"])
            if logo is not None:
                if is_sport:
                    # Yellow border ring — FancyBboxPatch only, no duplicate logo
                    hw = (TL_LOGO_SIZE * TL_LOGO_ZOOM) / (TL_FIG_W * DPI) * 1.20
                    hh = (TL_LOGO_SIZE * TL_LOGO_ZOOM) / (TL_FIG_H * DPI) * 1.20
                    ax.add_patch(patches.FancyBboxPatch(
                        (lx - hw, y_mid - hh), hw * 2, hh * 2,
                        boxstyle="round,pad=0.004",
                        facecolor="none",
                        edgecolor=YELLOW, linewidth=2.2,
                        transform=ax.transAxes, zorder=5,
                    ))

                ab = AnnotationBbox(
                    OffsetImage(logo, zoom=TL_LOGO_ZOOM),
                    (lx, y_mid), xycoords="axes fraction",
                    frameon=False, zorder=6,
                    box_alignment=(0.5, 0.5),
                )
                ax.add_artist(ab)
            else:
                r = _TIER_H * 0.28
                ax.add_patch(patches.Circle(
                    (lx, y_mid), radius=r,
                    facecolor=DGRAY, edgecolor=color, linewidth=1.0,
                    transform=ax.transAxes, zorder=5,
                ))
                initials = "".join(w[0] for w in row["team_name"].split()[:2]).upper()
                ax.text(lx, y_mid, initials, color=LGRAY, fontsize=7,
                        fontfamily=FONT_BODY, ha="center", va="center",
                        transform=ax.transAxes, zorder=6)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.018, 0.978], [TL_Y_DIV_BOT, TL_Y_DIV_BOT],
            color=YELLOW, lw=0.5, alpha=0.30, transform=ax.transAxes, zorder=3)

    if HAS_PIL and AVATAR_PATH.exists():
        try:
            avatar = Image.open(AVATAR_PATH).convert("RGBA").resize((20, 20), Image.LANCZOS)
            ab = AnnotationBbox(
                OffsetImage(np.array(avatar), zoom=1.0),
                (0.025, TL_Y_FOOTER), xycoords="axes fraction",
                frameon=False, zorder=6, box_alignment=(0.5, 0.5),
            )
            ax.add_artist(ab)
        except Exception:
            pass

    ax.text(0.098, TL_Y_FOOTER, "@SportRecifeLab",
            color=YELLOW, fontsize=9, fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.976, TL_Y_FOOTER, "Dados: SofaScore",
            color=DGRAY, fontsize=7, fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes, zorder=5)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "02_tier_list.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Card salvo: {out_path}")
    return out_path


# ── Cálculo do ranking ────────────────────────────────────────────────────────

def _norm(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi <= lo:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def _load_weighted_xg_map(curated_dir) -> dict:
    """{(match_code, team_key): xg_weighted} de game_state_xg.csv. Vazio se ausente."""
    path = curated_dir / "game_state_xg.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    df["xg_weighted"] = pd.to_numeric(df["xg_weighted"], errors="coerce")
    return {
        (str(r["match_code"]), str(r["team_key"])): float(r["xg_weighted"])
        for _, r in df.iterrows()
        if pd.notna(r["xg_weighted"])
    }


def _compute_ranking(sos_window: int) -> tuple[pd.DataFrame, int]:
    xpts_df = pd.read_csv(XPTS_PATH)
    matches = pd.read_csv(MATCHES_PATH, dtype=str)
    stats   = pd.read_csv(STATS_PATH, dtype=str)

    # ── Número da rodada ──────────────────────────────────────────────────────
    try:
        max_round = int(
            matches.loc[matches["status"] == "completed", "round"].astype(int).max()
        )
    except Exception:
        max_round = int(xpts_df["MP"].max()) if "MP" in xpts_df.columns else 1

    # ── Build all_rows ────────────────────────────────────────────────────────
    completed = matches[matches["status"] == "completed"].copy()
    completed["round"] = completed["round"].astype(int)
    completed["home_score"] = pd.to_numeric(completed["home_score"], errors="coerce")
    completed["away_score"] = pd.to_numeric(completed["away_score"], errors="coerce")
    completed = completed.dropna(subset=["home_score", "away_score"])

    stats["expected_goals"] = pd.to_numeric(stats["expected_goals"], errors="coerce")
    stats["is_home"] = stats["is_home"].map(
        {"True": True, "False": False, True: True, False: False}
    )
    home_xg = stats[stats["is_home"] == True][["match_code", "expected_goals"]].rename(
        columns={"expected_goals": "xg_home"}
    )
    away_xg = stats[stats["is_home"] == False][["match_code", "expected_goals"]].rename(
        columns={"expected_goals": "xg_away"}
    )
    xg = home_xg.merge(away_xg, on="match_code", how="inner")
    merged = completed.merge(xg, on="match_code", how="inner").dropna(
        subset=["xg_home", "xg_away"]
    )

    def _outcome(gf, ga): return "W" if gf > ga else ("D" if gf == ga else "L")

    home_r = merged.assign(
        team_key=merged["home_team_key"], opp_key=merged["away_team_key"],
        xg_prod=merged["xg_home"], xg_conc=merged["xg_away"],
        outcome=merged.apply(lambda r: _outcome(r["home_score"], r["away_score"]), axis=1),
    )[["team_key", "opp_key", "match_code", "round", "xg_prod", "xg_conc", "outcome"]]

    away_r = merged.assign(
        team_key=merged["away_team_key"], opp_key=merged["home_team_key"],
        xg_prod=merged["xg_away"], xg_conc=merged["xg_home"],
        outcome=merged.apply(lambda r: _outcome(r["away_score"], r["home_score"]), axis=1),
    )[["team_key", "opp_key", "match_code", "round", "xg_prod", "xg_conc", "outcome"]]

    all_rows = pd.concat([home_r, away_r], ignore_index=True)
    all_rows["pts"] = all_rows["outcome"].map({"W": 3, "D": 1, "L": 0})

    # xG ponderado por game state (garbage-time discount) — fallback: xG cru
    _wmap = _load_weighted_xg_map(XPTS_PATH.parent)
    if _wmap:
        all_rows["xg_prod"] = all_rows.apply(
            lambda r: _wmap.get((str(r["match_code"]), str(r["team_key"])), r["xg_prod"]), axis=1
        )
        all_rows["xg_conc"] = all_rows.apply(
            lambda r: _wmap.get((str(r["match_code"]), str(r["opp_key"])), r["xg_conc"]), axis=1
        )

    # ── Força do adversário (live PPG) ────────────────────────────────────────
    xpts_df["MP"]   = pd.to_numeric(xpts_df["MP"], errors="coerce")
    xpts_df["Pts"]  = pd.to_numeric(xpts_df["Pts"], errors="coerce")
    ppg = (xpts_df["Pts"] / xpts_df["MP"]).where(xpts_df["MP"] > 0, 0.0)
    ppg_max = ppg.max()
    perf = dict(zip(xpts_df["team_key"], ppg / ppg_max if ppg_max > 0 else ppg))

    # ── Componentes ───────────────────────────────────────────────────────────
    # C1: xPts/MP (ajustado por game state quando disponível)
    _xpts_col = "xPts_adj" if "xPts_adj" in xpts_df.columns else "xPts"
    xpts_df[_xpts_col] = pd.to_numeric(xpts_df[_xpts_col], errors="coerce")
    c1 = dict(zip(xpts_df["team_key"], xpts_df[_xpts_col] / xpts_df["MP"]))

    # C2: Net xG/MP
    agg = (
        all_rows.groupby("team_key")
        .agg(xgp=("xg_prod", "sum"), xgc=("xg_conc", "sum"), mp=("pts", "count"))
        .assign(net=lambda d: (d["xgp"] - d["xgc"]) / d["mp"])
    )
    c2 = agg["net"].to_dict()

    # SOS-rolling (multiplicador único da Força, não componente somado)
    sos_roll: dict[str, float] = {}
    for tk, grp in all_rows.groupby("team_key"):
        recent_opps = grp.sort_values("round").tail(sos_window)["opp_key"]
        strengths = [perf.get(k, 0.0) for k in recent_opps]
        sos_roll[tk] = sum(strengths) / len(strengths) if strengths else 0.0

    # Forma recente
    recent_rounds = range(max(1, max_round - sos_window + 1), max_round + 1)
    recent = all_rows[all_rows["round"].isin(recent_rounds)]
    form_agg = recent.groupby("team_key").agg(
        pts_sum=("pts", "sum"), mp_r=("pts", "count")
    ).assign(ppg=lambda d: d["pts_sum"] / d["mp_r"])
    c4 = form_agg["ppg"].to_dict()

    # ── Montar tabela ─────────────────────────────────────────────────────────
    table = xpts_df[["team_key", "team_name", "MP", "xPts", "Pts", "pts_diff"]].copy()
    table["c_xpts_mp"]   = table["team_key"].map(c1).fillna(0.0)   # desempenho
    table["c_net_xg_mp"] = table["team_key"].map(c2).fillna(0.0)   # domínio
    table["c_form"]      = table["team_key"].map(c4).fillna(0.0)
    table["sos_rolling"] = table["team_key"].map(sos_roll).fillna(0.0).round(3)

    # Sub-sinais normalizados → fusão Desempenho+Domínio (eram r≈0,99: contagem dupla)
    table["n_desemp"] = _norm(table["c_xpts_mp"]).values
    table["n_dom"]    = _norm(table["c_net_xg_mp"]).values
    forca_raw = (table["n_desemp"] + table["n_dom"]) / 2.0

    # Força ajustada pelo calendário (SOS aplicado uma vez) → renormaliza
    table["n_forca"] = _norm(forca_raw * (1.0 + table["sos_rolling"])).values
    table["n_form"]  = _norm(table["c_form"]).values

    table["power_score"] = (
        0.70 * table["n_forca"]
        + 0.30 * table["n_form"]
    ) * 100

    table["power_score"] = table["power_score"].round(1)
    table = table.sort_values("power_score", ascending=False).reset_index(drop=True)
    table.insert(0, "rank_power", range(1, len(table) + 1))

    # Salvar CSV
    RANKING_PATH.parent.mkdir(parents=True, exist_ok=True)
    table["sos_window"] = sos_window
    table["generated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
    table.to_csv(RANKING_PATH, index=False)
    print(f"  CSV salvo: {RANKING_PATH}")

    return table, max_round


# ── Card ──────────────────────────────────────────────────────────────────────

def generate_card(df: pd.DataFrame, max_round: int, out_dir: Path) -> None:
    power_max = df["power_score"].max()

    # Nível de calendário (1..5) a partir do sos_rolling — mais dots = mais difícil
    sos_vals = df["sos_rolling"].astype(float)
    s_lo, s_hi = sos_vals.min(), sos_vals.max()

    def _sos_level(v: float) -> int:
        if s_hi <= s_lo:
            return 3
        frac = (float(v) - s_lo) / (s_hi - s_lo)
        return int(np.clip(round(frac * 4) + 1, 1, 5))

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Título ────────────────────────────────────────────────────────────────
    ax.text(0.50, Y_TITLE, "POWER RANKING",
            color=YELLOW, fontsize=24, fontfamily=FONT_TITLE, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    ax.text(0.50, Y_SUBTITLE,
            f"Série B 2026  ·  Rodada {max_round}  ·  Força (70%) · Momento (30%) · ajuste por Calendário",
            color=GRAY, fontsize=9.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _hline(ax, Y_DIV_TOP)

    # ── Cabeçalho ─────────────────────────────────────────────────────────────
    ax.text(X_RANK, Y_HEADER, "#", color=LGRAY, fontsize=8.5,
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=5)
    ax.text(X_NAME, Y_HEADER, "TIME", color=LGRAY, fontsize=8.5,
            fontfamily=FONT_TITLE, ha="left", va="center",
            transform=ax.transAxes, zorder=5)

    for i, (label, color) in enumerate(zip(COMP_LABELS, COMP_COLORS)):
        cx = X_MINI[i] + MINI_BAR_W / 2
        ax.text(cx, Y_HEADER, label, color=color, fontsize=7.5,
                fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=5)

    sos_cx = SOS_DOTS_X0 + SOS_DOTS_W / 2
    ax.text(sos_cx, Y_HEADER, SOS_LABEL, color=SOS_COLOR, fontsize=7.5,
            fontfamily=FONT_TITLE, ha="center", va="center",
            transform=ax.transAxes, zorder=5)

    ax.text(X_BAR0 + BAR_MAX / 2, Y_HEADER, "POWER SCORE",
            color=LGRAY, fontsize=8.5, fontfamily=FONT_TITLE,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    # ── Linhas ────────────────────────────────────────────────────────────────
    for idx, row in df.iterrows():
        y = Y_FIRST_ROW - idx * ROW_H
        is_sport = row["team_key"] == SPORT_KEY

        # Fundo alternado
        row_bg = CARD if idx % 2 == 0 else BG
        ax.add_patch(patches.Rectangle(
            (0.018, y - ROW_H * 0.47), X_RIGHT - 0.018, ROW_H * 0.94,
            facecolor=row_bg, edgecolor="none",
            transform=ax.transAxes, zorder=1,
        ))

        # Destaque Sport
        if is_sport:
            ax.add_patch(patches.FancyBboxPatch(
                (0.014, y - ROW_H * 0.47), X_RIGHT - 0.014, ROW_H * 0.94,
                boxstyle="round,pad=0.003",
                facecolor=YELLOW, alpha=0.06,
                edgecolor=YELLOW, linewidth=0.9,
                transform=ax.transAxes, zorder=2,
            ))

        rank_color = YELLOW if is_sport else LGRAY
        name_color = YELLOW if is_sport else WHITE

        # Rank
        ax.text(X_RANK, y, str(int(row["rank_power"])),
                color=rank_color, fontsize=12, fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=5)

        # Logo
        logo = _get_logo(row["team_key"])
        if logo is not None:
            _place_logo(ax, logo, X_LOGO, y)
        else:
            ax.add_patch(patches.Circle(
                (X_LOGO, y), radius=ROW_H * 0.36,
                facecolor=DGRAY, edgecolor="none",
                transform=ax.transAxes, zorder=4,
            ))
            initials = "".join(w[0] for w in row["team_name"].split()[:2]).upper()
            ax.text(X_LOGO, y, initials, color=LGRAY, fontsize=5,
                    fontfamily=FONT_BODY, ha="center", va="center",
                    transform=ax.transAxes, zorder=5)

        # Nome (com override opcional)
        display_name = TEAM_NAME_OVERRIDES.get(row["team_key"], row["team_name"])
        ax.text(X_NAME, y, display_name,
                color=name_color, fontsize=10.5, fontfamily=FONT_BODY,
                ha="left", va="center", transform=ax.transAxes, zorder=5)

        # Duas mini-barras ponderadas (Força, Momento)
        for ci, (comp_key, comp_color) in enumerate(zip(COMP_KEYS, COMP_COLORS)):
            val = float(row.get(comp_key, 0.0))
            _mini_bar(ax, X_MINI[ci], y, val, comp_color)

        # Calendário (SOS) como dots — modificador embutido na Força
        _sos_dots(ax, y, _sos_level(row.get("sos_rolling", 0.0)))

        # Barra de power score (gradiente)
        norm_score = float(row["power_score"]) / power_max
        _power_bar(ax, X_BAR0, y, norm_score, is_sport)

        # Valor numérico
        ax.text(X_SCORE, y, f"{row['power_score']:.1f}",
                color=name_color, fontsize=11, fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=5)

    # ── Legenda dos componentes ───────────────────────────────────────────────
    legend_y = Y_LEGEND
    weight_pct = ["70%", "30%"]
    lx = 0.025
    LEG_STEP = 0.320
    for i, (label, color, desc) in enumerate(zip(COMP_LABELS, COMP_COLORS, COMP_DESC)):
        ax.add_patch(patches.Rectangle(
            (lx, legend_y - 0.009), 0.012, 0.016,
            facecolor=color, alpha=0.80, edgecolor="none",
            transform=ax.transAxes, zorder=5,
        ))
        ax.text(lx + 0.017, legend_y + 0.008, f"{label}  ·  {weight_pct[i]}",
                color=color, fontsize=7.5, fontfamily=FONT_TITLE,
                ha="left", va="center", transform=ax.transAxes, zorder=5)
        ax.text(lx + 0.017, legend_y - 0.008, desc,
                color=GRAY, fontsize=7.0, fontfamily=FONT_BODY,
                ha="left", va="center", transform=ax.transAxes, zorder=5)
        lx += LEG_STEP

    # Calendário — marcador de 3 dots (modificador, não somado)
    for j in range(3):
        ax.add_patch(patches.Ellipse(
            (lx + 0.004 + j * 0.010, legend_y),
            width=0.0066, height=0.0066 * (FIG_W / FIG_H),
            facecolor=SOS_COLOR, edgecolor="none", alpha=0.90,
            transform=ax.transAxes, zorder=5,
        ))
    ax.text(lx + 0.040, legend_y + 0.008, f"{SOS_LABEL}  ·  ajuste",
            color=SOS_COLOR, fontsize=7.5, fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=5)
    ax.text(lx + 0.040, legend_y - 0.008, SOS_DESC,
            color=GRAY, fontsize=7.0, fontfamily=FONT_BODY,
            ha="left", va="center", transform=ax.transAxes, zorder=5)

    _hline(ax, Y_DIV_BOT)

    # ── Footer ────────────────────────────────────────────────────────────────
    if HAS_PIL and AVATAR_PATH.exists():
        try:
            avatar = Image.open(AVATAR_PATH).convert("RGBA").resize((24, 24), Image.LANCZOS)
            ab = AnnotationBbox(
                OffsetImage(np.array(avatar), zoom=1.0),
                (0.030, Y_FOOTER), xycoords="axes fraction",
                frameon=False, zorder=6, box_alignment=(0.5, 0.5),
            )
            ax.add_artist(ab)
        except Exception:
            pass

    ax.text(0.110, Y_FOOTER, "@SportRecifeLab",
            color=YELLOW, fontsize=11, fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=5)
    ax.text(X_RIGHT, Y_FOOTER, "Dados: SofaScore",
            color=DGRAY, fontsize=8.5, fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes, zorder=5)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "01_power_ranking.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  Card salvo: {out_path}")
    return out_path


# ── Tweet ─────────────────────────────────────────────────────────────────────

def generate_tweet(df: pd.DataFrame, max_round: int, out_dir: Path) -> None:
    TIER_EMOJIS = ["🥇", "🎯", "😴", "🆘"]
    tier_lines = []
    for tier, emoji in zip(TIER_DEFS, TIER_EMOJIS):
        teams = df[df["rank_power"].isin(tier["ranks"])].sort_values("rank_power")
        names = [r["team_name"].split()[0] for _, r in teams.iterrows()]
        label_short = tier["label"].replace("\n", " ")
        tier_lines.append(f"{emoji} {label_short}: {', '.join(names)}")

    sport = df[df["team_key"] == SPORT_KEY]
    sport_tier_label = "?"
    if not sport.empty:
        sr = int(sport.iloc[0]["rank_power"])
        for tier in TIER_DEFS:
            if sr in tier["ranks"]:
                sport_tier_label = tier["label"].replace("\n", " ")
                break

    tweet = (
        f"📊 TIER LIST Série B 2026 — Rodada {max_round}\n\n"
        + "\n".join(tier_lines) + "\n\n"
        f"Sport → {sport_tier_label}\n\n"
        "#SérieB #SportRecife #SportRecifeLab"
    )

    char_count = len(tweet)
    tweet_with_meta = f"[1/1 — card: 01_tier_list.png — {char_count} chars]\n\n{tweet}"

    out_file = out_dir / "tweet.txt"
    out_file.write_text(tweet_with_meta, encoding="utf-8")
    print(f"  Tweet salvo: {out_file}  ({char_count} chars)")


def generate_metadata(df: pd.DataFrame, max_round: int, sos_window: int, out_dir: Path) -> None:
    sport = df[df["team_key"] == SPORT_KEY]
    tiers_meta = {}
    for tier in TIER_DEFS:
        teams = df[df["rank_power"].isin(tier["ranks"])].sort_values("rank_power")
        tiers_meta[tier["label"].replace("\n", " ")] = [
            {"rank": int(r["rank_power"]), "team": r["team_name"], "score": float(r["power_score"])}
            for _, r in teams.iterrows()
        ]

    meta = {
        "post_type": "tier_list",
        "round": max_round,
        "sos_window": sos_window,
        "season": 2026,
        "competition": "serie_b",
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "cards": ["01_power_ranking.png", "02_tier_list.png"],
        "components": {
            "Força": "70% (xPts/MP + Net xG/MP, ajustada pelo SOS)",
            "Momento": "30% (Pts/MP últimas 4 rodadas)",
            "Calendário": "multiplicador da Força (não somado)",
        },
        "tiers": tiers_meta,
        "sport_rank": int(sport.iloc[0]["rank_power"]) if not sport.empty else None,
        "sport_score": float(sport.iloc[0]["power_score"]) if not sport.empty else None,
        "status": "pending_review",
    }
    out_file = out_dir / "metadata.json"
    out_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Metadata: {out_file}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Gera Power Ranking Série B 2026")
    parser.add_argument("--sos-window", type=int, default=4,
                        help="Janela rolling do SOS (default: 4 partidas)")
    args = parser.parse_args()

    print(f"Calculando Power Ranking (SOS window={args.sos_window})...")
    df, max_round = _compute_ranking(sos_window=args.sos_window)
    print(f"  {len(df)} times  ·  rodada {max_round}")

    out_dir = BASE_DIR / f"pending_posts/{TODAY_STR}_power-ranking-r{max_round}"
    print(f"\nGerando card de critérios (Força · Momento · Calendário)...")
    generate_card(df, max_round, out_dir)
    print(f"\nGerando card tier list...")
    generate_tier_card(df, max_round, out_dir)

    print(f"\nGerando tweet e metadata...")
    generate_tweet(df, max_round, out_dir)
    generate_metadata(df, max_round, args.sos_window, out_dir)

    sport = df[df["team_key"] == SPORT_KEY]
    sport_rank = int(sport.iloc[0]["rank_power"]) if not sport.empty else "?"
    top1 = df.iloc[0]

    print(f"\n{'─'*55}")
    print(f"  Líder: #{1} {top1['team_name']} ({top1['power_score']:.1f})")
    print(f"  Sport: #{sport_rank}  ({sport.iloc[0]['power_score']:.1f} pts)")
    print(f"  Saída: {out_dir}")


if __name__ == "__main__":
    main()
