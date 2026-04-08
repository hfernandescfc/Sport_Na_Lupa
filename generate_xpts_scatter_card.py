"""
Gera Card 02 — Scatter xPts vs Força dos Adversários  Série B 2026
  02_xpts_scatter.png

Saída: pending_posts/{date}_xpts-serie-b/

Requer:
  data/curated/serie_b_2026/expected_points_table.csv   (com colunas sos e sos_rank)

Se a coluna `sos` estiver ausente, o script encerra com instrução de como obtê-la.
"""

import datetime
import sys
from collections import deque
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Caminhos ─────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
TABLE_PATH  = BASE_DIR / "data/curated/serie_b_2026/expected_points_table.csv"
LOGO_CACHE  = BASE_DIR / "data/cache/logos"
AVATAR_PATH = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR   = datetime.date.today().strftime("%Y-%m-%d")
OUT_DIR     = BASE_DIR / f"pending_posts/{TODAY_STR}_xpts-serie-b"

TEAM_IDS = {
    "america-mineiro": 1973,
    "athletic-club":   342775,
    "atletico-go":     7314,
    "avai":            7315,
    "botafogo-sp":     1979,
    "ceara":           2001,
    "crb":             22032,
    "criciuma":        1984,
    "cuiaba":          49202,
    "fortaleza":       2020,
    "goias":           1960,
    "novorizontino":   135514,
    "juventude":       1980,
    "londrina":        2022,
    "nautico":         2011,
    "operario-pr":     39634,
    "ponte-preta":     1969,
    "sao-bernardo":    47504,
    "sport":           1959,
    "vila-nova-fc":    2021,
}

SPORT_KEY = "sport"

# ── Paleta ────────────────────────────────────────────────────────────────────
BG      = "#0d0d0d"
CARD    = "#161616"
YELLOW  = "#F5C400"
WHITE   = "#FFFFFF"
LGRAY   = "#CCCCCC"
GRAY    = "#888888"
DGRAY   = "#333333"
RED     = "#EF4444"
GREEN   = "#22C55E"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

FIG_W, FIG_H = 11.0, 7.5
DPI = 120   # → 1320×900 px

LOGO_SIZE_SPORT  = 44
LOGO_ZOOM_SPORT  = 1.0

# Colormap pts_diff: vermelho (underperforming) → cinza → verde (overperforming)
_CMAP = mcolors.LinearSegmentedColormap.from_list(
    "rg", [(0.0, "#EF4444"), (0.5, "#555555"), (1.0, "#22C55E")]
)
_NORM = mcolors.TwoSlopeNorm(vmin=-3.0, vcenter=0.0, vmax=3.0)


# ── Helpers de imagem ─────────────────────────────────────────────────────────

def _remove_bg(img: "Image.Image", thresh: int = 25) -> "Image.Image":
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    is_white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)
    visited = np.zeros((h, w), dtype=bool)
    from collections import deque
    queue: deque = deque()
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


def _get_logo(team_key: str, size: int) -> np.ndarray | None:
    """Le logo do cache local. Requer sync-logos previamente executado."""
    if not HAS_PIL:
        return None
    team_id = TEAM_IDS.get(team_key)
    if not team_id:
        return None
    cache_path = LOGO_CACHE / f"{team_id}.png"
    if not cache_path.exists():
        return None
    try:
        img = Image.open(cache_path).convert("RGBA")
        img = _remove_bg(img)
        img = img.resize((size, size), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None


# ── Rótulos com offsets manuais para evitar sobreposição ─────────────────────
# Ajuste (dx, dy) em pontos de offset para cada time
LABEL_OFFSETS: dict[str, tuple[float, float]] = {
    "sport":           (0, 12),
    "fortaleza":       (0, -12),
    "ceara":           (8, 6),
    "nautico":         (-8, -12),
    "criciuma":        (0, 10),
    "crb":             (-10, 8),
    "goias":           (8, -12),
    "avai":            (0, 10),
    "cuiaba":          (8, 6),
    "atletico-go":     (-10, -12),
    "juventude":       (8, 6),
    "america-mineiro": (-10, 8),
    "botafogo-sp":     (8, -12),
    "novorizontino":   (0, 10),
    "sao-bernardo":    (-10, 8),
    "londrina":        (8, -12),
    "operario-pr":     (0, 10),
    "athletic-club":   (-8, 8),
    "ponte-preta":     (8, -10),
    "vila-nova-fc":    (0, 10),
}


# ── Card ──────────────────────────────────────────────────────────────────────

def generate_scatter_card(df: pd.DataFrame) -> None:
    if "sos" not in df.columns:
        print(
            "\n⚠  Card 02 requer a coluna 'sos' — rode primeiro:\n"
            "   python -m src.main sync-serie-b-strength --season 2026\n"
            "   python -m src.main transform-standings --season 2026\n"
        )
        return

    fig = plt.figure(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)

    ax = fig.add_axes([0.09, 0.13, 0.82, 0.70])
    ax.set_facecolor(CARD)

    x_vals = df["sos"].values.astype(float)
    y_vals = df["xPts"].values.astype(float)
    deltas = df["pts_diff"].values.astype(float)

    x_med = np.median(x_vals)
    y_med = np.median(y_vals)

    x_min, x_max = x_vals.min() - 0.06, x_vals.max() + 0.06
    y_min, y_max = y_vals.min() - 0.35, y_vals.max() + 0.55

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    # ── Quadrantes ────────────────────────────────────────────────────────────
    ax.axvline(x_med, color=GRAY, linewidth=0.8, linestyle="--", alpha=0.35, zorder=2)
    ax.axhline(y_med, color=GRAY, linewidth=0.8, linestyle="--", alpha=0.35, zorder=2)

    ax.fill_betweenx([y_med, y_max], x_min, x_med, color=GRAY,  alpha=0.06,  zorder=1)  # fácil, alto
    ax.fill_betweenx([y_med, y_max], x_med, x_max, color=GREEN, alpha=0.10,  zorder=1)  # difícil, alto  ← destaque positivo
    ax.fill_betweenx([y_min, y_med], x_min, x_med, color=RED,   alpha=0.12,  zorder=1)  # fácil, baixo  ← zona crítica
    ax.fill_betweenx([y_min, y_med], x_med, x_max, color=GRAY,  alpha=0.06,  zorder=1)  # difícil, baixo

    # Rótulos de quadrante
    q_kw = dict(fontsize=7, fontfamily=FONT_BODY, style="italic", alpha=0.55, zorder=3)
    ax.text(x_min + 0.01, y_max - 0.05, "xPts alto · calendário fácil",
            color=GRAY, ha="left", va="top", **q_kw)
    ax.text(x_max - 0.01, y_max - 0.05, "xPts alto · calendário difícil",
            color=GREEN, ha="right", va="top", **q_kw)
    ax.text(x_min + 0.01, y_min + 0.05, "xPts baixo · calendário fácil",
            color=RED, ha="left", va="bottom", **q_kw)
    ax.text(x_max - 0.01, y_min + 0.05, "xPts baixo · calendário difícil",
            color=GRAY, ha="right", va="bottom", **q_kw)

    # ── Scatter — todos os times (exceto Sport) ───────────────────────────────
    sport_row = df[df["team_key"] == SPORT_KEY].iloc[0]
    others    = df[df["team_key"] != SPORT_KEY]

    for _, row in others.iterrows():
        c = _CMAP(_NORM(float(row["pts_diff"])))
        ax.scatter(row["sos"], row["xPts"], color=c, s=90, zorder=5,
                   edgecolors="#0d0d0d", linewidths=0.7)
        dx, dy = LABEL_OFFSETS.get(row["team_key"], (5, 5))
        ax.annotate(
            row["team_name"].split()[0],  # primeiro token do nome
            xy=(row["sos"], row["xPts"]),
            xytext=(dx, dy), textcoords="offset points",
            fontsize=6.8, color=LGRAY, fontfamily=FONT_BODY,
            ha="center", zorder=6,
        )

    # ── Sport — escudo como marcador ──────────────────────────────────────────
    sport_logo = _get_logo(SPORT_KEY, LOGO_SIZE_SPORT)
    if sport_logo is not None:
        # Anel amarelo atrás do escudo
        ax.scatter(sport_row["sos"], sport_row["xPts"],
                   s=560, color=YELLOW, zorder=7, linewidths=0)
        ab = AnnotationBbox(
            OffsetImage(sport_logo, zoom=LOGO_ZOOM_SPORT),
            (sport_row["sos"], sport_row["xPts"]),
            xycoords="data", frameon=False, zorder=8,
            box_alignment=(0.5, 0.5),
        )
        ax.add_artist(ab)
        # Anotação com xPts e pts_diff
        dx, dy = LABEL_OFFSETS.get(SPORT_KEY, (0, 14))
        delta = float(sport_row["pts_diff"])
        delta_str = f"+{delta:.1f}" if delta >= 0 else f"{delta:.1f}"
        ax.annotate(
            f"Sport\n{sport_row['xPts']:.2f} xPts  ({delta_str})",
            xy=(sport_row["sos"], sport_row["xPts"]),
            xytext=(dx, dy + 4), textcoords="offset points",
            fontsize=8, color=YELLOW, fontfamily=FONT_TITLE,
            fontweight="bold", ha="center", zorder=9,
        )
    else:
        c = _CMAP(_NORM(float(sport_row["pts_diff"])))
        ax.scatter(sport_row["sos"], sport_row["xPts"],
                   color=YELLOW, s=200, zorder=7,
                   edgecolors=WHITE, linewidths=1.5)

    # ── Eixos ─────────────────────────────────────────────────────────────────
    ax.set_xlabel(
        "Força dos adversários (SOS)  —  0 = mais fácil  ·  1 = mais difícil",
        color=LGRAY, fontsize=9, fontfamily=FONT_BODY, labelpad=8,
    )
    ax.set_ylabel(
        "xPts acumulados",
        color=LGRAY, fontsize=9, fontfamily=FONT_BODY, labelpad=8,
    )
    ax.tick_params(colors=LGRAY, labelsize=7.5)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(DGRAY)

    # ── Legenda de cor (pts_diff) ─────────────────────────────────────────────
    from matplotlib.lines import Line2D
    legend_elems = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GREEN,
               markersize=8, label="Pontuando acima do esperado (▲ PTS)"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#555555",
               markersize=8, label="Pontuando conforme esperado"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=RED,
               markersize=8, label="Pontuando abaixo do esperado (▼ PTS)"),
    ]
    ax.legend(handles=legend_elems, fontsize=7.5, loc="lower right",
              frameon=True, facecolor="#1a1a1a", edgecolor=DGRAY,
              labelcolor=LGRAY)

    # ── Título ────────────────────────────────────────────────────────────────
    fig.text(0.50, 0.965, "SÉRIE B 2026 — xPts vs FORÇA DOS ADVERSÁRIOS",
             ha="center", va="top", color=YELLOW,
             fontsize=14, fontfamily=FONT_TITLE, fontweight="bold")
    fig.text(0.50, 0.927,
             "Cor do ponto = performance real vs esperada  ·  Quadrante superior direito = desempenho mais consistente",
             ha="center", va="top", color=GRAY, fontsize=8, fontfamily=FONT_BODY)

    # ── Footer ────────────────────────────────────────────────────────────────
    if HAS_PIL and AVATAR_PATH.exists():
        try:
            avatar = Image.open(AVATAR_PATH).convert("RGBA").resize((40, 40), Image.LANCZOS)
            ab = AnnotationBbox(
                OffsetImage(np.array(avatar), zoom=1.0),
                (0.055, 0.028), xycoords="figure fraction",
                frameon=False, zorder=10, box_alignment=(0.5, 0.5),
            )
            fig.add_artist(ab)
        except Exception:
            pass

    fig.text(0.095, 0.028, "@SportRecifeLab",
             color=YELLOW, fontsize=9, fontfamily=FONT_TITLE,
             ha="left", va="center")
    fig.text(0.97, 0.028, "Dados: SofaScore",
             color=DGRAY, fontsize=7.5, fontfamily=FONT_BODY,
             ha="right", va="center")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "02_xpts_scatter.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  OK  {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Carregando dados...")
    df = pd.read_csv(TABLE_PATH)
    has_sos = "sos" in df.columns
    print(f"  {len(df)} times  ·  SOS: {'sim' if has_sos else 'não (rode sync-serie-b-strength primeiro)'}")

    print("\nGerando Card 02 — Scatter xPts vs SOS...")
    generate_scatter_card(df)
    print(f"\nCard salvo em: {OUT_DIR}")
