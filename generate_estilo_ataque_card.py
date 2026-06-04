"""
Gera Card — Estilo de Ataque: Série B 2026 R1-R5
Scatter: X = % finalizações via Transição | Y = % via Bola Parada
Bubble size = xG total acumulado por time
Quadrantes definem o perfil ofensivo de cada time.

Saída: pending_posts/{hoje}_estilo-ataque-r5/card.png
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR     = Path(__file__).parent
SHOTMAP_PATH = BASE_DIR / "data/processed/2026/shotmaps/serie_b_shotmaps.json"
LOGOS_DIR    = BASE_DIR / "data/cache/logos"
AVATAR_PATH  = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR    = datetime.date.today().strftime("%Y-%m-%d")
OUT_DIR      = BASE_DIR / f"pending_posts/{TODAY_STR}_estilo-ataque-r5"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Paleta
# ---------------------------------------------------------------------------
BG          = "#0d0d0d"
GOLD        = "#F5C400"
WHITE       = "#FFFFFF"
GRAY_LIGHT  = "#aaaaaa"
GRAY_MID    = "#444444"
SPORT_KEY   = "sport"

# Cores de quadrante (fill + label)
Q_COLORS = {
    "jogo_aberto":  ("#1a7a3a", "#27ae60"),   # verde  — baixo trans, baixa BP
    "transicao":    ("#7a1a1a", "#e74c3c"),   # verm   — alto trans, baixa BP
    "bola_parada":  ("#1a3a7a", "#3498db"),   # azul   — baixo trans, alta BP
    "versatil":     ("#5a4a1a", "#d4ac0d"),   # ouro   — alto trans, alta BP
}

# ---------------------------------------------------------------------------
# Team → logo ID + short name
# ---------------------------------------------------------------------------
TEAM_META: dict[str, dict] = {
    "america-mg":    {"logo": 1973,   "short": "América"},
    "athletic-club": {"logo": 342775, "short": "Athletic"},
    "atletico-go":   {"logo": 7314,   "short": "Atlético-GO"},
    "avai":          {"logo": 7315,   "short": "Avaí"},
    "botafogo-sp":   {"logo": 1979,   "short": "Botafogo-SP"},
    "ceara":         {"logo": 2001,   "short": "Ceará"},
    "crb":           {"logo": 22032,  "short": "CRB"},
    "criciuma":      {"logo": 1984,   "short": "Criciúma"},
    "cuiaba":        {"logo": 49202,  "short": "Cuiabá"},
    "fortaleza":     {"logo": 2020,   "short": "Fortaleza"},
    "goias":         {"logo": 1960,   "short": "Goiás"},
    "novorizontino": {"logo": 135514, "short": "Novorizontino"},
    "juventude":     {"logo": 1980,   "short": "Juventude"},
    "londrina":      {"logo": 2022,   "short": "Londrina"},
    "nautico":       {"logo": 2011,   "short": "Náutico"},
    "operario-pr":   {"logo": 39634,  "short": "Operário"},
    "ponte-preta":   {"logo": 1969,   "short": "Ponte Preta"},
    "sao-bernardo":  {"logo": 47504,  "short": "São Bernardo"},
    "sport":         {"logo": 1959,   "short": "Sport"},
    "vila-nova":     {"logo": 2021,   "short": "Vila Nova"},
}

# Situations
OPEN  = {"assisted", "regular"}
TRANS = {"fast-break"}
BP    = {"corner", "set-piece", "free-kick", "throw-in-set-piece"}
PEN   = {"penalty"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _remove_bg_floodfill(img: Image.Image, thresh: int = 25) -> Image.Image:
    """BFS flood fill from image corners to remove exterior white background."""
    img = img.convert("RGBA")
    data = np.array(img, dtype=np.uint8)
    h, w = data.shape[:2]
    visited = np.zeros((h, w), dtype=bool)
    queue = []
    for y in range(h):
        for x in [0, w - 1]:
            if not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    for x in range(w):
        for y in [0, h - 1]:
            if not visited[y, x]:
                visited[y, x] = True
                queue.append((y, x))
    while queue:
        y, x = queue.pop()
        r, g, b, _ = data[y, x]
        if r >= 255 - thresh and g >= 255 - thresh and b >= 255 - thresh:
            data[y, x, 3] = 0
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx]:
                    visited[ny, nx] = True
                    queue.append((ny, nx))
    return Image.fromarray(data)


def _load_logo(team_key: str, zoom: float = 0.45) -> OffsetImage | None:
    meta = TEAM_META.get(team_key)
    if not meta:
        return None
    path = LOGOS_DIR / f"{meta['logo']}.png"
    if not path.exists():
        return None
    try:
        img = Image.open(path).convert("RGBA")
        img = _remove_bg_floodfill(img)
        return OffsetImage(np.array(img), zoom=zoom)
    except Exception:
        return None


def _normalize(name: str) -> str:
    """Minimal normalizer for team names from shotmap → team_key."""
    import unicodedata
    name = unicodedata.normalize("NFKD", name)
    name = "".join(c for c in name if not unicodedata.combining(c))
    name = name.lower().strip()
    ALIAS = {
        "america mineiro": "america-mg",
        "athletic club": "athletic-club",
        "atletico goianiense": "atletico-go",
        "avai": "avai",
        "botafogo-sp": "botafogo-sp",
        "ceara": "ceara",
        "crb": "crb",
        "criciuma": "criciuma",
        "cuiaba": "cuiaba",
        "fortaleza": "fortaleza",
        "goias": "goias",
        "gremio novorizontino": "novorizontino",
        "juventude": "juventude",
        "londrina": "londrina",
        "nautico": "nautico",
        "operario-pr": "operario-pr",
        "ponte preta": "ponte-preta",
        "sport recife": "sport",
        "sao bernardo": "sao-bernardo",
        "vila nova fc": "vila-nova",
    }
    return ALIAS.get(name, name.replace(" ", "-"))


# ---------------------------------------------------------------------------
# Build data
# ---------------------------------------------------------------------------
def build_df() -> pd.DataFrame:
    with open(SHOTMAP_PATH, encoding="utf-8") as f:
        d = json.load(f)

    shots = [s for m in d["matches"] for s in m["shots"]]
    df = pd.DataFrame(shots)
    df["xg"] = pd.to_numeric(df["xg"], errors="coerce").fillna(0)
    df["team_key"] = df["team_name"].apply(_normalize)

    rows = []
    for team_key, grp in df.groupby("team_key"):
        non_pen = grp[~grp["situation"].isin(PEN)]
        total_np = len(non_pen)
        if total_np == 0:
            continue
        pct_trans = non_pen["situation"].isin(TRANS).sum() / total_np * 100
        pct_bp    = non_pen["situation"].isin(BP).sum()    / total_np * 100
        pct_open  = non_pen["situation"].isin(OPEN).sum()  / total_np * 100
        total_xg  = grp["xg"].sum()
        rows.append({
            "team_key":   team_key,
            "short":      TEAM_META.get(team_key, {}).get("short", team_key),
            "pct_trans":  pct_trans,
            "pct_bp":     pct_bp,
            "pct_open":   pct_open,
            "total_xg":   total_xg,
            "total_shots": total_np,
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Plot
# ---------------------------------------------------------------------------
def draw(df: pd.DataFrame) -> None:
    med_x = df["pct_trans"].median()
    med_y = df["pct_bp"].median()

    fig, ax = plt.subplots(figsize=(12, 8.5), dpi=120)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

    xmin, xmax = 0, df["pct_trans"].max() * 1.15
    ymin, ymax = 14, df["pct_bp"].max() * 1.14

    # --- Quadrant fills ---
    fill_alpha = 0.10
    ax.fill_betweenx([med_y, ymax], xmin, med_x,  color=Q_COLORS["bola_parada"][0],  alpha=fill_alpha)
    ax.fill_betweenx([med_y, ymax], med_x, xmax,  color=Q_COLORS["versatil"][0],     alpha=fill_alpha)
    ax.fill_betweenx([ymin, med_y], xmin, med_x,  color=Q_COLORS["jogo_aberto"][0],  alpha=fill_alpha)
    ax.fill_betweenx([ymin, med_y], med_x, xmax,  color=Q_COLORS["transicao"][0],    alpha=fill_alpha)

    # --- Quadrant labels — corners inside each quadrant ---
    lbl_kw = dict(fontsize=9, fontweight="bold", alpha=0.60, va="top", ha="left")
    pad_x = (xmax - xmin) * 0.016
    pad_y = (ymax - ymin) * 0.025
    # top-left: BOLA PARADA
    ax.text(xmin + pad_x, ymax - pad_y, "BOLA PARADA",  color=Q_COLORS["bola_parada"][1],  **lbl_kw)
    # top-right: VERSÁTIL
    ax.text(med_x + pad_x, ymax - pad_y, "VERSÁTIL",    color=Q_COLORS["versatil"][1],     **lbl_kw)
    # bottom-left: pushed down to avoid logo cluster
    ax.text(xmin + pad_x, ymin + (med_y - ymin) * 0.18, "JOGO ABERTO",
            color=Q_COLORS["jogo_aberto"][1], fontsize=9, fontweight="bold", alpha=0.60,
            va="bottom", ha="left")
    # bottom-right: TRANSIÇÃO
    ax.text(med_x + pad_x, med_y - pad_y, "TRANSIÇÃO",  color=Q_COLORS["transicao"][1],    **lbl_kw)

    # --- Median lines ---
    ax.axvline(med_x, color=GRAY_MID, lw=0.8, ls="--", alpha=0.6)
    ax.axhline(med_y, color=GRAY_MID, lw=0.8, ls="--", alpha=0.6)

    # --- Collision avoidance: spread overlapping points in display space ---
    def _spread_positions(
        xs: list[float], ys: list[float],
        x_range: float, y_range: float,
        logo_w_pct: float = 0.055,
        logo_h_pct: float = 0.075,
        iterations: int = 60,
    ) -> list[tuple[float, float]]:
        """Push overlapping logos apart using a simple repulsion loop."""
        pos = [(float(x), float(y)) for x, y in zip(xs, ys)]
        lw = logo_w_pct * x_range
        lh = logo_h_pct * y_range
        for _ in range(iterations):
            for i in range(len(pos)):
                for j in range(i + 1, len(pos)):
                    dx = pos[j][0] - pos[i][0]
                    dy = pos[j][1] - pos[i][1]
                    overlap_x = lw - abs(dx)
                    overlap_y = lh - abs(dy)
                    if overlap_x > 0 and overlap_y > 0:
                        # Push along the axis with less overlap
                        if overlap_x < overlap_y:
                            shift = overlap_x / 2.0 + 0.05
                            sign = 1.0 if dx >= 0 else -1.0
                            pos[i] = (pos[i][0] - sign * shift, pos[i][1])
                            pos[j] = (pos[j][0] + sign * shift, pos[j][1])
                        else:
                            shift = overlap_y / 2.0 + 0.05
                            sign = 1.0 if dy >= 0 else -1.0
                            pos[i] = (pos[i][0], pos[i][1] - sign * shift)
                            pos[j] = (pos[j][0], pos[j][1] + sign * shift)
        return pos

    # Sort: Sport last so it renders on top
    df_sorted = pd.concat([df[df["team_key"] != SPORT_KEY], df[df["team_key"] == SPORT_KEY]])
    orig_x  = df_sorted["pct_trans"].tolist()
    orig_y  = df_sorted["pct_bp"].tolist()
    spread  = _spread_positions(orig_x, orig_y, xmax - xmin, ymax - ymin)

    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        ox, oy   = orig_x[idx], orig_y[idx]   # true data coords (for ring)
        sx, sy   = spread[idx]                  # spread coords (for logo placement)
        key      = row["team_key"]
        is_sport = (key == SPORT_KEY)

        # Sport: golden ring anchored at true position
        if is_sport:
            ax.scatter(ox, oy, s=1100, color="none", edgecolors=GOLD, linewidths=2.8, zorder=8)
            ax.scatter(ox, oy, s=700,  color=GOLD,   alpha=0.14,       zorder=7)

        # Logo at spread position
        zoom = 0.36 if is_sport else 0.30
        logo_img = _load_logo(key, zoom=zoom)
        if logo_img:
            ab = AnnotationBbox(logo_img, (sx, sy), frameon=False,
                                zorder=9 if is_sport else 6)
            ax.add_artist(ab)
        else:
            ax.scatter(sx, sy, s=100, color=GRAY_MID, zorder=6)
            ax.text(sx, sy, key[:2].upper(), color=WHITE, fontsize=6,
                    ha="center", va="center", zorder=7)

        # Connector line if logo moved from true position
        dist = ((sx - ox)**2 + (sy - oy)**2) ** 0.5
        if dist > 0.3 and not is_sport:
            ax.plot([ox, sx], [oy, sy], color=GRAY_MID, lw=0.5, alpha=0.35, zorder=4)

        # Label below logo
        label_color  = GOLD if is_sport else GRAY_LIGHT
        label_weight = "bold" if is_sport else "normal"
        label_size   = 9.0 if is_sport else 6.8
        ax.annotate(
            row["short"], xy=(sx, sy),
            xytext=(0, -20), textcoords="offset points",
            ha="center", va="top",
            color=label_color, fontsize=label_size,
            fontweight=label_weight, zorder=10,
        )

    xg_min, xg_max = df["total_xg"].min(), df["total_xg"].max()

    # --- Axes style ---
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("% FINALIZAÇÕES EM TRANSIÇÃO  (fast-break)",
                  color=GRAY_LIGHT, fontsize=9, labelpad=8)
    ax.set_ylabel("% FINALIZAÇÕES EM BOLA PARADA  (corner + escanteio + falta)",
                  color=GRAY_LIGHT, fontsize=9, labelpad=8)
    ax.tick_params(colors=GRAY_MID, labelsize=8)
    for spine in ax.spines.values():
        spine.set_edgecolor(GRAY_MID)
        spine.set_linewidth(0.5)
    ax.xaxis.label.set_color(GRAY_LIGHT)
    ax.yaxis.label.set_color(GRAY_LIGHT)
    for label in ax.get_xticklabels() + ax.get_yticklabels():
        label.set_color(GRAY_MID)

    # --- Grid ---
    ax.grid(color=GRAY_MID, alpha=0.15, lw=0.5)

    # --- Title block ---
    fig.text(0.13, 0.97, "ESTILO DE ATAQUE",
             color=GOLD, fontsize=18, fontweight="bold",
             va="top", ha="left", fontfamily="Franklin Gothic Medium")
    fig.text(0.13, 0.935, "Série B 2026  •  R1–R5  •  penaltis excluídos",
             color=GRAY_LIGHT, fontsize=9, va="top", ha="left")

    # --- Reading guide (top-right) ---
    guide_lines = [
        "Eixo X: % finalizações em transição",
        "Eixo Y: % finalizações em bola parada",
        "Mediana como divisor de quadrante",
    ]
    for i, line in enumerate(guide_lines):
        fig.text(0.985, 0.91 - i * 0.022, line,
                 color=GRAY_MID, fontsize=6.5, va="top", ha="right")

    # --- Footer ---
    footer_y = 0.012
    if AVATAR_PATH.exists():
        avatar = Image.open(AVATAR_PATH).convert("RGBA")
        avatar.thumbnail((52, 52), Image.LANCZOS)
        ax_h = fig.add_axes([0.068, footer_y - 0.005, 0.04, 0.055])
        ax_h.imshow(np.array(avatar))
        ax_h.axis("off")

    fig.text(0.115, footer_y + 0.022, "@SportRecifeLab",
             color=GRAY_LIGHT, fontsize=8, va="center", ha="left")
    fig.text(0.115, footer_y + 0.008, "Dados: SofaScore  •  Finalizações com situação classificada",
             color=GRAY_MID, fontsize=7, va="center", ha="left")

    fig.subplots_adjust(left=0.09, right=0.97, top=0.91, bottom=0.10)

    out_path = OUT_DIR / "card.png"
    fig.savefig(out_path, dpi=120, facecolor=BG, bbox_inches="tight")
    plt.close(fig)
    print(f"Card salvo: {out_path}")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    df = build_df()
    print(df[["team_key", "pct_trans", "pct_bp", "total_xg"]].sort_values("pct_trans", ascending=False).to_string(index=False))
    draw(df)
