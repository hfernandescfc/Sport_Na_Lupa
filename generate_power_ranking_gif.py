"""
Power Ranking Série B — Evolução de posições rodada a rodada.
Formato bump chart: posições 1-20 no eixo Y, rodadas no eixo X,
linhas conectando a classificação de cada time.

Uso:
  python generate_power_ranking_gif.py
  python generate_power_ranking_gif.py --duration 1400
"""

import argparse
import datetime
import io
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
    print("PIL não encontrado. pip install Pillow"); sys.exit(1)

# ── Caminhos ──────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
MATCHES_PATH = BASE_DIR / "data/curated/serie_b_2026/matches.csv"
STATS_PATH   = BASE_DIR / "data/curated/serie_b_2026/team_match_stats.csv"
LOGO_CACHE   = BASE_DIR / "data/cache/logos"
AVATAR_PATH  = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR    = datetime.date.today().strftime("%Y-%m-%d")

# ── IDs SofaScore ─────────────────────────────────────────────────────────────
TEAM_IDS = {
    "america-mg":    1973,   "athletic-club": 342775, "atletico-go":   7314,
    "avai":          7315,   "botafogo-sp":   1979,   "ceara":         2001,
    "crb":           22032,  "criciuma":      1984,   "cuiaba":        49202,
    "fortaleza":     2020,   "goias":         1960,   "novorizontino": 135514,
    "juventude":     1980,   "londrina":      2022,   "nautico":       2011,
    "operario-pr":   39634,  "ponte-preta":   1969,   "sao-bernardo":  47504,
    "sport":         1959,   "vila-nova":     2021,
}
SPORT_KEY = "sport"

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
LGRAY  = "#CCCCCC"
GRAY   = "#555555"
DGRAY  = "#2a2a2a"
WHITE  = "#FFFFFF"
GREEN  = "#22C55E"
RED    = "#EF4444"

FONT_TITLE = "Franklin Gothic Heavy"
FONT_BODY  = "Arial"

# Cor de linha por time (Sport sempre amarelo)
TEAM_LINE_COLORS: dict[str, str] = {
    "america-mg":    "#A78BFA",  "athletic-club": "#60A5FA",
    "atletico-go":   "#F87171",  "avai":          "#34D399",
    "botafogo-sp":   "#FBBF24",  "ceara":         "#2DD4BF",
    "crb":           "#FB923C",  "criciuma":      "#818CF8",
    "cuiaba":        "#4ADE80",  "fortaleza":     "#F472B6",
    "goias":         "#38BDF8",  "novorizontino": "#A3E635",
    "juventude":     "#FB7185",  "londrina":      "#C084FC",
    "nautico":       "#67E8F9",  "operario-pr":   "#FDE68A",
    "ponte-preta":   "#6EE7B7",  "sao-bernardo":  "#FDA4AF",
    "sport":         YELLOW,     "vila-nova":     "#93C5FD",
}

# ── Layout bump chart ─────────────────────────────────────────────────────────
FIG_W = 13.0
FIG_H =  9.0
DPI   = 110          # → 1430 × 990 px

LOGO_SZ      = 32    # px dos logos laterais
LOGO_ZOOM    = 0.78
LOGO_SZ_DOT  = 20    # px dos logos nos pontos de rodada
LOGO_ZOOM_DOT = 0.58

# Coordenadas em axes fraction
X_LNUM  = 0.020      # números de posição (esquerda)
X_LLOGO = 0.065      # logos R1 (esquerda)
X_COL0  = 0.120      # coluna R1 (dot)
X_COL1  = 0.875      # coluna última rodada (dot)
X_RLOGO = 0.930      # logos rodada atual (direita)
X_RNUM  = 0.978      # números de posição (direita)

Y_TOP   = 0.862      # eixo Y: posição 1
Y_BOT   = 0.068      # eixo Y: posição 20

Y_TITLE    = 0.966
Y_SUBTITLE = 0.948
Y_DIV_TOP  = 0.932
Y_DIV_BOT  = 0.048
Y_FOOTER   = 0.028


def _y(pos: float) -> float:
    """Rank position (1-20) → axes-fraction Y."""
    return Y_TOP - (pos - 1) / 19.0 * (Y_TOP - Y_BOT)


def _x(round_n: int, all_rounds: list[int]) -> float:
    """Round number → axes-fraction X."""
    n = len(all_rounds)
    if n <= 1:
        return (X_COL0 + X_COL1) / 2
    idx = all_rounds.index(round_n)
    return X_COL0 + idx / (n - 1) * (X_COL1 - X_COL0)


# ── Imagem helpers ────────────────────────────────────────────────────────────

def _remove_bg(img: Image.Image, thresh: int = 25) -> Image.Image:
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
        y, x = q.popleft(); data[y, x, 3] = 0
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True; q.append((ny, nx))
    return Image.fromarray(data, "RGBA")


_logo_cache:     dict[str, "np.ndarray | None"] = {}
_logo_cache_dot: dict[str, "np.ndarray | None"] = {}

def _get_logo(team_key: str) -> "np.ndarray | None":
    if team_key in _logo_cache:
        return _logo_cache[team_key]
    tid = TEAM_IDS.get(team_key)
    result = None
    if tid:
        p = LOGO_CACHE / f"{tid}.png"
        if p.exists():
            try:
                img = Image.open(p).convert("RGBA")
                img = _remove_bg(img)
                img = img.resize((LOGO_SZ, LOGO_SZ), Image.LANCZOS)
                result = np.array(img)
            except Exception:
                pass
    _logo_cache[team_key] = result
    return result


def _get_logo_dot(team_key: str) -> "np.ndarray | None":
    if team_key in _logo_cache_dot:
        return _logo_cache_dot[team_key]
    tid = TEAM_IDS.get(team_key)
    result = None
    if tid:
        p = LOGO_CACHE / f"{tid}.png"
        if p.exists():
            try:
                img = Image.open(p).convert("RGBA")
                img = _remove_bg(img)
                img = img.resize((LOGO_SZ_DOT, LOGO_SZ_DOT), Image.LANCZOS)
                result = np.array(img)
            except Exception:
                pass
    _logo_cache_dot[team_key] = result
    return result


def _place_logo(ax, team_key: str, x: float, y: float, zoom: float = LOGO_ZOOM):
    logo = _get_logo(team_key)
    if logo is None:
        return
    ab = AnnotationBbox(
        OffsetImage(logo, zoom=zoom),
        (x, y), xycoords="axes fraction",
        frameon=False, zorder=8, box_alignment=(0.5, 0.5),
    )
    ax.add_artist(ab)


def _fig_to_pil(fig: plt.Figure) -> Image.Image:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, facecolor=BG)
    buf.seek(0)
    img = Image.open(buf).copy().convert("RGB")
    plt.close(fig)
    return img


# ── Cálculo do ranking por rodada ─────────────────────────────────────────────

def _norm(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    if hi <= lo:
        return pd.Series(0.5, index=s.index)
    return (s - lo) / (hi - lo)


def _compute_standings_for_round(
    all_matches: pd.DataFrame,
    all_team_names: dict[str, str],
    max_round: int,
) -> pd.DataFrame:
    """Tabela real: ordena por Pts (desc) e saldo de gols (desc) como desempate."""
    m = all_matches.copy()
    m["round_int"] = pd.to_numeric(m["round"], errors="coerce")
    completed = m[
        (m["status"] == "completed") & (m["round_int"] <= max_round)
    ].copy()
    completed["home_score"] = pd.to_numeric(completed["home_score"], errors="coerce")
    completed["away_score"] = pd.to_numeric(completed["away_score"], errors="coerce")
    completed = completed.dropna(subset=["home_score", "away_score"])

    # Base zerada com todos os 20 times
    base = {tk: {"team_key": tk, "team_name": tn, "pts": 0, "gf": 0, "ga": 0}
            for tk, tn in all_team_names.items()}

    for _, row in completed.iterrows():
        hs, as_ = int(row["home_score"]), int(row["away_score"])
        htk, atk = row["home_team_key"], row["away_team_key"]

        if htk not in base or atk not in base:
            continue

        # Gols
        base[htk]["gf"] += hs; base[htk]["ga"] += as_
        base[atk]["gf"] += as_; base[atk]["ga"] += hs

        # Pontos
        if hs > as_:
            base[htk]["pts"] += 3
        elif hs == as_:
            base[htk]["pts"] += 1; base[atk]["pts"] += 1
        else:
            base[atk]["pts"] += 3

    tbl = pd.DataFrame(base.values())
    tbl["gd"] = tbl["gf"] - tbl["ga"]

    tbl = tbl.sort_values(
        ["pts", "gd", "gf"],
        ascending=[False, False, False],
    ).reset_index(drop=True)
    tbl.insert(0, "rank_power", range(1, len(tbl) + 1))
    return tbl


# ── Frame do bump chart ───────────────────────────────────────────────────────

def generate_bump_frame(
    rankings: dict[int, pd.DataFrame],
    all_rounds: list[int],
    up_to_round: int,
    all_team_names: dict[str, str],
) -> Image.Image:

    visible = [r for r in all_rounds if r <= up_to_round]
    r_first = all_rounds[0]
    spacing = (Y_TOP - Y_BOT) / 19.0

    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

    # ── Título ────────────────────────────────────────────────────────────────
    ax.text(0.50, Y_TITLE, "EVOLUÇÃO DA CLASSIFICAÇÃO",
            color=YELLOW, fontsize=17, fontfamily=FONT_TITLE, fontweight="bold",
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.50, Y_SUBTITLE,
            f"Série B 2026  ·  R{r_first} → R{up_to_round}  ·  "
            "Pts  ›  Saldo de Gols  ›  Gols Marcados",
            color=GRAY, fontsize=7.5, fontfamily=FONT_BODY,
            ha="center", va="center", transform=ax.transAxes, zorder=5)
    ax.plot([0.018, 0.978], [Y_DIV_TOP]*2,
            color=YELLOW, lw=0.5, alpha=0.25, transform=ax.transAxes, zorder=3)

    # ── Bandas de zona ────────────────────────────────────────────────────────
    band_x0 = X_COL0 - 0.003
    band_w  = (X_COL1 - X_COL0) + 0.006
    lbl_x   = X_COL1 + 0.005

    # G6 — zona de acesso estendida (posições 1-6), fundo mais suave
    y_g6_top = Y_TOP + spacing * 0.55
    y_g6_bot = _y(6)  - spacing * 0.55
    ax.add_patch(patches.Rectangle(
        (band_x0, y_g6_bot), band_w, y_g6_top - y_g6_bot,
        facecolor=GREEN, alpha=0.06, edgecolor="none",
        transform=ax.transAxes, zorder=1,
    ))
    ax.text(lbl_x, (y_g6_top + _y(3)) / 2, "G6",
            color=GREEN, fontsize=6.5, fontfamily=FONT_TITLE, alpha=0.45,
            ha="left", va="center", transform=ax.transAxes, zorder=4)

    # G2 — top 2 (promoção direta / título), fundo mais intenso
    y_g2_top = Y_TOP + spacing * 0.55
    y_g2_bot = _y(2)  - spacing * 0.55
    ax.add_patch(patches.Rectangle(
        (band_x0, y_g2_bot), band_w, y_g2_top - y_g2_bot,
        facecolor=GREEN, alpha=0.13, edgecolor="none",
        transform=ax.transAxes, zorder=1,
    ))
    ax.text(lbl_x, (y_g2_top + y_g2_bot) / 2, "G2",
            color=GREEN, fontsize=6.5, fontfamily=FONT_TITLE, alpha=0.70,
            ha="left", va="center", transform=ax.transAxes, zorder=4)

    # Z4 — rebaixamento (posições 17-20)
    y_z4_top = _y(17) + spacing * 0.55
    y_z4_bot = Y_BOT  - spacing * 0.55
    ax.add_patch(patches.Rectangle(
        (band_x0, y_z4_bot), band_w, y_z4_top - y_z4_bot,
        facecolor=RED, alpha=0.09, edgecolor="none",
        transform=ax.transAxes, zorder=1,
    ))
    ax.text(lbl_x, (y_z4_top + y_z4_bot) / 2, "Z4",
            color=RED, fontsize=6.5, fontfamily=FONT_TITLE, alpha=0.60,
            ha="left", va="center", transform=ax.transAxes, zorder=4)

    # ── Grid ──────────────────────────────────────────────────────────────────
    for pos in range(1, 21):
        yp = _y(pos)
        ax.plot([X_COL0 - 0.003, X_COL1 + 0.003], [yp, yp],
                color=DGRAY, lw=0.4, alpha=0.6,
                transform=ax.transAxes, zorder=2)

    # ── Labels de rodada ──────────────────────────────────────────────────────
    for r in all_rounds:
        xr = _x(r, all_rounds)
        revealed = r <= up_to_round
        ax.text(xr, Y_DIV_TOP - 0.018, f"R{r}",
                color=YELLOW if revealed else GRAY,
                fontsize=8, fontfamily=FONT_TITLE,
                ha="center", va="bottom", transform=ax.transAxes, zorder=5,
                alpha=1.0 if revealed else 0.30)
        # Linha vertical
        ax.plot([xr, xr], [Y_BOT - spacing * 0.5, Y_TOP + spacing * 0.5],
                color=DGRAY, lw=0.5, alpha=0.50 if revealed else 0.15,
                transform=ax.transAxes, zorder=2)

    # ── Linhas por time ───────────────────────────────────────────────────────
    # Desenha todos os outros times antes do Sport
    for pass_sport in (False, True):
        for tk in all_team_names:
            is_sport = tk == SPORT_KEY
            if pass_sport != is_sport:
                continue

            color  = TEAM_LINE_COLORS.get(tk, LGRAY)
            lw     = 2.8 if is_sport else 1.0
            alpha  = 1.0 if is_sport else 0.55
            zorder = 12 if is_sport else 4

            pts_x, pts_y = [], []
            for r in visible:
                df = rankings[r]
                row = df[df["team_key"] == tk]
                if row.empty:
                    continue
                pos = int(row.iloc[0]["rank_power"])
                pts_x.append(_x(r, all_rounds))
                pts_y.append(_y(pos))

            if len(pts_x) < 1:
                continue

            # Linha
            if len(pts_x) >= 2:
                ax.plot(pts_x, pts_y,
                        color=color, lw=lw, alpha=alpha,
                        solid_capstyle="round", solid_joinstyle="round",
                        transform=ax.transAxes, zorder=zorder)

            # Logos nos pontos de cada rodada
            logo_dot = _get_logo_dot(tk)
            zoom_dot = LOGO_ZOOM_DOT * (1.20 if is_sport else 1.0)
            for xi, yi in zip(pts_x, pts_y):
                if logo_dot is not None:
                    ab = AnnotationBbox(
                        OffsetImage(logo_dot, zoom=zoom_dot, alpha=alpha),
                        (xi, yi), xycoords="axes fraction",
                        frameon=False, zorder=zorder + 1,
                        box_alignment=(0.5, 0.5),
                    )
                    ax.add_artist(ab)
                else:
                    dot_s = 55 if is_sport else 18
                    ax.scatter([xi], [yi], s=dot_s, color=color, alpha=alpha,
                               zorder=zorder + 1, transform=ax.transAxes,
                               linewidths=0)

    # ── Logos esquerda (sempre R1) ────────────────────────────────────────────
    df_r1 = rankings[r_first]
    for _, row in df_r1.iterrows():
        tk  = row["team_key"]
        pos = int(row["rank_power"])
        yp  = _y(pos)
        is_sport = tk == SPORT_KEY

        # Número de posição
        ax.text(X_LNUM, yp, str(pos),
                color=YELLOW if is_sport else GRAY,
                fontsize=6.0, fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=6)

        # Anel Sport
        if is_sport:
            hw = (LOGO_SZ * LOGO_ZOOM) / (FIG_W * DPI) * 1.22
            hh = (LOGO_SZ * LOGO_ZOOM) / (FIG_H * DPI) * 1.22
            ax.add_patch(patches.FancyBboxPatch(
                (X_LLOGO - hw, yp - hh), hw * 2, hh * 2,
                boxstyle="round,pad=0.004",
                facecolor="none", edgecolor=YELLOW, linewidth=1.8,
                transform=ax.transAxes, zorder=7,
            ))
        _place_logo(ax, tk, X_LLOGO, yp)

    # ── Logos direita (rodada atual) ──────────────────────────────────────────
    df_cur = rankings[up_to_round]
    for _, row in df_cur.iterrows():
        tk  = row["team_key"]
        pos = int(row["rank_power"])
        yp  = _y(pos)
        is_sport = tk == SPORT_KEY

        if is_sport:
            hw = (LOGO_SZ * LOGO_ZOOM) / (FIG_W * DPI) * 1.22
            hh = (LOGO_SZ * LOGO_ZOOM) / (FIG_H * DPI) * 1.22
            ax.add_patch(patches.FancyBboxPatch(
                (X_RLOGO - hw, yp - hh), hw * 2, hh * 2,
                boxstyle="round,pad=0.004",
                facecolor="none", edgecolor=YELLOW, linewidth=1.8,
                transform=ax.transAxes, zorder=7,
            ))
        _place_logo(ax, tk, X_RLOGO, yp)

        # Número de posição (direita)
        ax.text(X_RNUM, yp, str(pos),
                color=YELLOW if is_sport else GRAY,
                fontsize=6.0, fontfamily=FONT_TITLE,
                ha="center", va="center", transform=ax.transAxes, zorder=6)

    # ── Footer ────────────────────────────────────────────────────────────────
    ax.plot([0.018, 0.978], [Y_DIV_BOT]*2,
            color=YELLOW, lw=0.5, alpha=0.25, transform=ax.transAxes, zorder=3)

    if AVATAR_PATH.exists():
        try:
            av = Image.open(AVATAR_PATH).convert("RGBA").resize((16, 16), Image.LANCZOS)
            ab = AnnotationBbox(OffsetImage(np.array(av), zoom=1.0),
                                (0.025, Y_FOOTER), xycoords="axes fraction",
                                frameon=False, zorder=6, box_alignment=(0.5, 0.5))
            ax.add_artist(ab)
        except Exception:
            pass

    ax.text(0.090, Y_FOOTER, "@SportRecifeLab",
            color=YELLOW, fontsize=7.5, fontfamily=FONT_TITLE,
            ha="left", va="center", transform=ax.transAxes, zorder=5)
    ax.text(0.978, Y_FOOTER, "Dados: SofaScore",
            color="#444444", fontsize=6, fontfamily=FONT_BODY,
            ha="right", va="center", transform=ax.transAxes, zorder=5)

    return _fig_to_pil(fig)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration",      type=int, default=1400,
                        help="ms por frame (default: 1400)")
    parser.add_argument("--last-duration", type=int, default=4000,
                        help="ms no último frame (default: 4000)")
    args = parser.parse_args()

    print("Carregando dados...")
    all_matches = pd.read_csv(MATCHES_PATH, dtype=str)

    all_team_names: dict[str, str] = {}
    for _, row in all_matches.iterrows():
        all_team_names[row["home_team_key"]] = row["home_team"]
        all_team_names[row["away_team_key"]] = row["away_team"]

    all_matches["round_int"] = pd.to_numeric(all_matches["round"], errors="coerce")
    completed_rounds = sorted(
        all_matches.loc[all_matches["status"] == "completed", "round_int"]
        .dropna().unique().astype(int)
    )
    if not completed_rounds:
        print("Nenhuma rodada completa."); sys.exit(1)

    max_round = completed_rounds[-1]
    print(f"  {len(completed_rounds)} rodadas: R{completed_rounds[0]}–R{max_round}")

    print("\nCalculando classificações...")
    rankings: dict[int, pd.DataFrame] = {}
    for r in completed_rounds:
        print(f"  R{r}...", end="", flush=True)
        rankings[r] = _compute_standings_for_round(all_matches, all_team_names, r)
        sport_rank = int(
            rankings[r].loc[rankings[r]["team_key"] == SPORT_KEY, "rank_power"].iloc[0]
        ) if SPORT_KEY in rankings[r]["team_key"].values else "?"
        print(f" líder: {rankings[r].iloc[0]['team_name']} | Sport: #{sport_rank}")

    print("\nGerando frames...")
    pil_frames: list[Image.Image] = []
    durations:  list[int] = []

    for r in completed_rounds:
        print(f"  Frame R{r}...", end="", flush=True)
        img = generate_bump_frame(rankings, completed_rounds, r, all_team_names)
        pil_frames.append(img)
        durations.append(args.last_duration if r == max_round else args.duration)
        print(f" {img.size[0]}×{img.size[1]}px  OK")

    # Pausa extra no frame final
    pil_frames.append(pil_frames[-1].copy())
    durations.append(args.last_duration)

    out_dir = BASE_DIR / f"pending_posts/{TODAY_STR}_power-ranking-r{max_round}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Salvar GIF
    gif_path = out_dir / "power_ranking_evolution.gif"
    print(f"\nSalvando GIF ({len(pil_frames)} frames)...")
    quantized = [
        f.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                   dither=Image.Dither.FLOYDSTEINBERG)
        for f in pil_frames
    ]
    quantized[0].save(
        gif_path, format="GIF", save_all=True,
        append_images=quantized[1:], loop=0,
        duration=durations, optimize=False,
    )

    # Salvar frame final como PNG estático também
    png_path = out_dir / "power_ranking_evolution_final.png"
    pil_frames[-1].save(png_path)

    size_mb = gif_path.stat().st_size / (1024 * 1024)
    print(f"\n{'─'*55}")
    print(f"  GIF:       {gif_path}")
    print(f"  PNG final: {png_path}")
    print(f"  Tamanho:   {size_mb:.1f} MB  ({pil_frames[0].size[0]}×{pil_frames[0].size[1]}px)")
    print(f"  Frames:    {len(pil_frames) - 1} rodadas + pausa final")


if __name__ == "__main__":
    main()
