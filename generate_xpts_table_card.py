"""
Gera Card 01 — Tabela xPts Série B 2026
  01_xpts_table.png   — tabela dos 20 times rankeados por xPts

Saída: pending_posts/{date}_xpts-serie-b/

Requer:
  data/curated/serie_b_2026/expected_points_table.csv
  data/curated/serie_b_2026/matches.csv          (para número da rodada)
"""

import datetime
import math
import sys
import urllib.request
from collections import deque
from pathlib import Path

# Garante saída UTF-8 no Windows (evita UnicodeEncodeError no terminal)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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
MATCHES_PATH= BASE_DIR / "data/curated/serie_b_2026/matches.csv"
LOGO_CACHE  = BASE_DIR / "data/cache/logos"
AVATAR_PATH = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR   = datetime.date.today().strftime("%Y-%m-%d")
OUT_DIR     = BASE_DIR / f"pending_posts/{TODAY_STR}_xpts-serie-b"

# ── IDs SofaScore por team_key (chave = valor em team_match_stats.csv) ───────
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
CARD2   = "#1e1e1e"
YELLOW  = "#F5C400"
WHITE   = "#FFFFFF"
LGRAY   = "#CCCCCC"
GRAY    = "#888888"
DGRAY   = "#333333"
RED     = "#EF4444"
GREEN   = "#22C55E"
BLUE    = "#60A5FA"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

FIG_W, FIG_H = 10.0, 9.5
DPI = 120   # → 1200×1140 px

# ── Dimensões da tabela (em fração dos eixos) ─────────────────────────────────
Y_TITLE      = 0.968
Y_SUBTITLE   = 0.940
Y_DIV_TOP    = 0.922
Y_HEADER     = 0.906
Y_FIRST_ROW  = 0.872
ROW_H        = 0.037   # 20 linhas → última em y=0.872−19×0.037=0.169
Y_DIV_BOT    = 0.065
Y_FOOTER     = 0.040

X_RANK  = 0.038
X_LOGO  = 0.078
X_NAME  = 0.118   # alinhamento esquerdo
X_BAR0  = 0.372   # início da barra de xPts
BAR_MAX = 0.145   # largura máxima da barra
X_XPTS  = 0.552   # centro do valor xPts (logo após a barra)
X_PTS   = 0.640   # centro do valor Pts reais
X_DELTA = 0.733   # centro do Δ
X_SOS   = 0.865   # centro dos dots de dificuldade
X_RIGHT = 0.960   # margem direita

# Nível de dificuldade SOS (1=fácil, 5=difícil) e cores
SOS_COLORS = {1: "#22C55E", 2: "#86EFAC", 3: "#F5C400", 4: "#F97316", 5: "#EF4444"}
SOS_FILLED = "●"
SOS_EMPTY  = "○"

LOGO_SIZE   = 24   # pixels após resize — reduzido para não sobrepor linhas adjacentes
LOGO_ZOOM   = 0.70


# ── Helpers de imagem ─────────────────────────────────────────────────────────

def _remove_bg(img: "Image.Image", thresh: int = 25) -> "Image.Image":
    """Remove fundo branco de bordas via BFS."""
    data = np.array(img.convert("RGBA"), dtype=np.uint8)
    h, w = data.shape[:2]
    r, g, b = data[..., 0], data[..., 1], data[..., 2]
    is_white = (r >= 255 - thresh) & (g >= 255 - thresh) & (b >= 255 - thresh)
    visited = np.zeros((h, w), dtype=bool)
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


def _get_logo(team_key: str, size: int = LOGO_SIZE) -> np.ndarray | None:
    """Retorna logo como array RGBA (size×size) do cache local.

    Requer que os logos tenham sido baixados previamente com:
        python -m src.main sync-logos --season 2026
    """
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


# ── Helpers de desenho ────────────────────────────────────────────────────────

def _hline(ax, y, x0=0.02, x1=0.98, color=YELLOW, lw=0.6, alpha=0.30):
    ax.plot([x0, x1], [y, y], color=color, lw=lw, alpha=alpha,
            transform=ax.transAxes, zorder=3)


def _draw_sos(ax, x_center: float, y: float, level: int | None):
    """Desenha 5 círculos representando a dificuldade do adversário."""
    if level is None:
        ax.text(x_center, y, "–", color=GRAY, fontsize=8,
                fontfamily=FONT_BODY, ha="center", va="center",
                transform=ax.transAxes, zorder=5)
        return
    color = SOS_COLORS.get(level, GRAY)
    dots = SOS_FILLED * level + SOS_EMPTY * (5 - level)
    ax.text(x_center, y, dots, color=color, fontsize=7.5,
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)


def _draw_delta(ax, x: float, y: float, delta: float):
    if delta > 0.3:
        txt, color = f"▲ +{delta:.1f}", GREEN
    elif delta < -0.3:
        txt, color = f"▼ {delta:.1f}", RED
    else:
        txt, color = f"≈ {delta:+.1f}", GRAY
    ax.text(x, y, txt, color=color, fontsize=7.8,
            fontfamily=FONT_BODY, ha="center", va="center",
            transform=ax.transAxes, zorder=5)


def _place_logo(ax, arr: np.ndarray, x: float, y: float, zoom: float = LOGO_ZOOM):
    ab = AnnotationBbox(
        OffsetImage(arr, zoom=zoom),
        (x, y), xycoords="axes fraction",
        frameon=False, zorder=6, box_alignment=(0.5, 0.5),
    )
    ax.add_artist(ab)


# ── Leitura dos dados ─────────────────────────────────────────────────────────

def _load_data() -> tuple[pd.DataFrame, int]:
    df = pd.read_csv(TABLE_PATH)
    # Número da última rodada completada
    try:
        mdf = pd.read_csv(MATCHES_PATH, dtype=str)
        max_round = int(mdf.loc[mdf["status"] == "completed", "round"].astype(int).max())
    except Exception:
        max_round = int(df["MP"].max()) if "MP" in df.columns else 0
    return df, max_round


def _sos_level(sos_rank: float | None, n: int = 20) -> int | None:
    if sos_rank is None or (isinstance(sos_rank, float) and math.isnan(sos_rank)):
        return None
    r = int(sos_rank)
    # rank 1=mais difícil → level 5; rank 20=mais fácil → level 1
    return max(1, min(5, 6 - math.ceil(r / (n / 5))))


# ── Card ──────────────────────────────────────────────────────────────────────

def generate_table_card(df: pd.DataFrame, max_round: int) -> None:
    has_sos = "sos_rank" in df.columns

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ── Título ────────────────────────────────────────────────────────────────
    ax.text(0.50, Y_TITLE, "SÉRIE B 2026 — TABELA ESPERADA",
            color=YELLOW, fontsize=17, fontfamily=FONT_TITLE, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    subtitle = f"xPts via xG (Poisson)  ·  Rodada {max_round}"
    if has_sos:
        subtitle += "  ·  Dificuldade de calendário incluída"
    ax.text(0.50, Y_SUBTITLE, subtitle,
            color=GRAY, fontsize=8.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)

    _hline(ax, Y_DIV_TOP)

    # ── Cabeçalho das colunas ─────────────────────────────────────────────────
    headers = [
        (X_RANK,  "#",      "center"),
        (X_NAME,  "TIME",   "left"),
        (X_XPTS,  "xPts",   "center"),
        (X_PTS,   "PTS",    "center"),
        (X_DELTA, "±PTS",   "center"),
    ]
    if has_sos:
        headers.append((X_SOS, "DIFIC.", "center"))

    for x, label, ha in headers:
        ax.text(x, Y_HEADER, label, color=LGRAY, fontsize=7.5,
                fontfamily=FONT_TITLE, ha=ha, va="center",
                transform=ax.transAxes, zorder=5)

    xpts_max = df["xPts"].max()

    # ── Linhas da tabela ──────────────────────────────────────────────────────
    for i, row in df.iterrows():
        y = Y_FIRST_ROW - i * ROW_H
        is_sport = row["team_key"] == SPORT_KEY

        # Fundo alternado
        row_bg = CARD if i % 2 == 0 else BG
        bg_rect = patches.Rectangle(
            (0.02, y - ROW_H * 0.47), X_RIGHT - 0.02, ROW_H * 0.94,
            facecolor=row_bg, edgecolor="none",
            transform=ax.transAxes, zorder=1,
        )
        ax.add_patch(bg_rect)

        # Destaque Sport: borda amarela + fundo levemente amarelado
        if is_sport:
            highlight = patches.FancyBboxPatch(
                (0.015, y - ROW_H * 0.47), X_RIGHT - 0.015, ROW_H * 0.94,
                boxstyle="round,pad=0.003",
                facecolor=YELLOW, alpha=0.07,
                edgecolor=YELLOW, linewidth=0.9,
                transform=ax.transAxes, zorder=2,
            )
            ax.add_patch(highlight)

        rank_color = YELLOW if is_sport else LGRAY
        name_color = YELLOW if is_sport else WHITE

        # Rank
        ax.text(X_RANK, y, str(row["rank_xpts"]), color=rank_color,
                fontsize=8.5, fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=5)

        # Escudo
        logo = _get_logo(row["team_key"])
        if logo is not None:
            _place_logo(ax, logo, X_LOGO, y)
        else:
            # Fallback: círculo com iniciais do time
            circle = patches.Circle(
                (X_LOGO, y), radius=ROW_H * 0.38,
                facecolor=DGRAY, edgecolor="none",
                transform=ax.transAxes, zorder=4,
            )
            ax.add_patch(circle)
            initials = "".join(w[0] for w in row["team_name"].split()[:2]).upper()
            ax.text(X_LOGO, y, initials, color=LGRAY, fontsize=5.5,
                    fontfamily=FONT_BODY, ha="center", va="center",
                    transform=ax.transAxes, zorder=5)

        # Nome do time
        name = row["team_name"]
        ax.text(X_NAME, y, name, color=name_color, fontsize=8.5,
                fontfamily=FONT_BODY, ha="left", va="center",
                transform=ax.transAxes, zorder=5)

        # Barra de xPts
        bar_fill = (row["xPts"] / xpts_max) * BAR_MAX
        bar_color = YELLOW if is_sport else BLUE
        # trilho (fundo escuro)
        ax.add_patch(patches.Rectangle(
            (X_BAR0, y - ROW_H * 0.25), BAR_MAX, ROW_H * 0.50,
            facecolor="#252525", edgecolor="none",
            transform=ax.transAxes, zorder=3,
        ))
        # preenchimento proporcional
        ax.add_patch(patches.Rectangle(
            (X_BAR0, y - ROW_H * 0.25), bar_fill, ROW_H * 0.50,
            facecolor=bar_color, alpha=0.75, edgecolor="none",
            transform=ax.transAxes, zorder=4,
        ))
        # valor xPts
        ax.text(X_XPTS, y, f"{row['xPts']:.2f}", color=name_color,
                fontsize=8.5, fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=5)

        # Pts reais
        ax.text(X_PTS, y, str(int(row["Pts"])), color=LGRAY,
                fontsize=8.5, fontfamily=FONT_TITLE, ha="center", va="center",
                transform=ax.transAxes, zorder=5)

        # Δ pts_diff
        _draw_delta(ax, X_DELTA, y, float(row["pts_diff"]))

        # SOS dots
        if has_sos:
            level = _sos_level(row.get("sos_rank"))
            _draw_sos(ax, X_SOS, y, level)

    # ── Footer ────────────────────────────────────────────────────────────────
    _hline(ax, Y_DIV_BOT)

    if HAS_PIL and AVATAR_PATH.exists():
        try:
            avatar = Image.open(AVATAR_PATH).convert("RGBA").resize((44, 44), Image.LANCZOS)
            ab = AnnotationBbox(
                OffsetImage(np.array(avatar), zoom=1.0),
                (0.055, Y_FOOTER), xycoords="axes fraction",
                frameon=False, zorder=6, box_alignment=(0.5, 0.5),
            )
            ax.add_artist(ab)
        except Exception:
            pass

    ax.text(0.105, Y_FOOTER, "@SportRecifeLab",
            color=YELLOW, fontsize=9, fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=5)

    ax.text(X_RIGHT, Y_FOOTER, "Dados: SofaScore",
            color=DGRAY, fontsize=7.5, fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes, zorder=5)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "01_xpts_table.png"
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", facecolor=BG)
    plt.close(fig)
    print(f"  OK  {out_path}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Carregando dados...")
    df, max_round = _load_data()
    has_sos = "sos_rank" in df.columns
    print(f"  {len(df)} times  ·  rodada {max_round}  ·  SOS: {'sim' if has_sos else 'não'}")

    print("\nGerando Card 01 — Tabela xPts...")
    generate_table_card(df, max_round)
    print(f"\nCard salvo em: {OUT_DIR}")
