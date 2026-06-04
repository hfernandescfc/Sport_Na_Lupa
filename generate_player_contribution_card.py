# -*- coding: utf-8 -*-
"""
Card: Contribuição dos jogadores do Sport na Série B 2026
Filosofia visual "Thermal Glow" — grade de círculos, gradiente escuro→ouro

Saída: pending_posts/{data}_contribuicao-jogadores-r{N}/card.png
"""

import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image
from datetime import date

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
DATA_FILE = BASE_DIR / "data/curated/sport_2026/player_match_stats.csv"
LOGOS_DIR = BASE_DIR / "data/cache/logos"
SRL_LOGO  = BASE_DIR / "sportrecifelab_avatar.png"
SPORT_ID  = 1959

# ── Palette ───────────────────────────────────────────────────────────────────
BG        = "#0a0a0c"           # fundo quase-preto com toque azulado
ROW_ALT   = "#0e0e11"           # linha alternada (imperceptível à distância)
GOLD      = "#F5C400"
GOLD_DEEP = "#7a5200"
GOLD_MID  = "#c98800"
WHITE     = "#FFFFFF"
LGRAY     = "#c0c0c0"
GRAY      = "#555555"
RING_PEAK = "#F5C400"           # anel do maior contribuidor
GLOW_PEAK = "#ffd54a"           # glow sutil do maior contribuidor
RING_BASE = "#1e1e22"           # anel base de todos os círculos
CELL_ZERO = "#111116"           # círculo de valor zero / ausente

# ── Métricas ──────────────────────────────────────────────────────────────────
# 3 métricas que contam um arco narrativo: penetração → progressão → finalização
METRICS = [
    ("accurate_opposition_half_passes",  "PASSES\nCAMPO ADV."),
    ("total_progression",                "PROGRESSÃO\nCOM A BOLA"),
    ("total_shots",                      "FINA-\nLIZAÇÕES"),
]

GK_IDS     = {871291, 1019685, 1020235}
S_MAX_SIZE = 2700   # tamanho do maior círculo (líder da coluna)
S_MIN_VAL  = 480    # tamanho mínimo para valores não-zero (garante texto legível)
S_ZERO     = 200    # placeholder para valor zero


# ── Utilidades ────────────────────────────────────────────────────────────────
def load_logo(path: Path, target: int = 60) -> np.ndarray | None:
    try:
        img = Image.open(path).convert("RGBA")
        img.thumbnail((target, target), Image.LANCZOS)
        return np.array(img)
    except Exception:
        return None


def shorten(name: str, maxlen: int = 13) -> str:
    if len(name) <= maxlen:
        return name
    parts = name.split()
    return f"{parts[0][0]}. {parts[-1]}" if len(parts) > 1 else name[:maxlen]


def gold_shade(fraction: float) -> tuple:
    """Família ouro, variação sutil de brilho: âmbar escuro → ouro pleno."""
    f = float(np.clip(fraction, 0.0, 1.0))
    c_dim  = np.array([0x7a, 0x5a, 0x00], float) / 255   # âmbar escuro (0%)
    c_full = np.array([0xF5, 0xC4, 0x00], float) / 255   # ouro pleno (100%)
    return tuple(c_dim + f * (c_full - c_dim))


def text_on_gold(fraction: float) -> str:
    """Texto escuro sobre ouro brilhante, branco sobre âmbar escuro."""
    return "#1a0d00" if fraction >= 0.72 else "#ffffff"


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, default=None)
    parser.add_argument(
        "--exclude-metric",
        action="append",
        default=[],
        help="Metric key to exclude from the card (can be repeated).",
    )
    parser.add_argument(
        "--output-name",
        default="card.png",
        help="Output filename inside the pending_posts folder.",
    )
    parser.add_argument(
        "--normalize-per90",
        action="store_true",
        help="Normalize metric totals by minutes played and scale to per-90 values.",
    )
    args = parser.parse_args()
    metrics = [(key, label) for key, label in METRICS if key not in set(args.exclude_metric)]
    if not metrics:
        raise ValueError("At least one metric must remain after exclusions.")

    # ── Dados ─────────────────────────────────────────────────────────────────
    df   = pd.read_csv(DATA_FILE, encoding="utf-8")
    mask = df["competition"].str.contains(r"Brasileir|serie_b", case=False, na=False, regex=True)
    sb   = df[mask & (df["team_key"] == "sport")].copy()

    max_round = args.round if args.round else int(sb["round"].max())
    sb = sb[sb["round"] <= max_round]
    sb = sb[~sb["player_id"].isin(GK_IDS)]

    cols = [m for m, _ in metrics]
    agg  = (
        sb.groupby("player_id")
          .agg(player_name   = ("player_name",    "first"),
               minutes_played= ("minutes_played", "sum"),
               **{c: (c, lambda x, k=c: x.fillna(0).clip(lower=0).sum()) for c in cols})
          .reset_index()
          .sort_values("minutes_played", ascending=False)
          .head(10)
          .sort_values("minutes_played", ascending=True)   # y=0 base → y=9 topo
          .reset_index(drop=True)
    )

    if args.normalize_per90:
        valid_minutes = agg["minutes_played"].replace(0, np.nan)
        for c in cols:
            agg[c] = (agg[c] / valid_minutes) * 90.0
        agg[cols] = agg[cols].fillna(0.0)

    N = len(agg)
    M = len(metrics)

    # % de contribuição (por coluna)
    pct = pd.DataFrame(index=agg.index)
    for c in cols:
        total     = agg[c].sum()
        pct[c]    = (agg[c] / total * 100) if total > 0 else 0.0

    max_mins = float(agg["minutes_played"].max())

    # Top-2 por coluna para glow highlighting
    top2_thresholds: dict[str, float] = {}
    for c in cols:
        sv = pct[c].sort_values(ascending=False).values
        top2_thresholds[c] = float(sv[1]) if len(sv) > 1 else float(sv[0])

    # ── Headline dinâmica: arco construção → finalização ──────────────────────
    _shot_col = "total_shots"
    _pass_col = "accurate_opposition_half_passes"
    if _shot_col in pct.columns and _pass_col in pct.columns:
        _top_shot_idx  = pct[_shot_col].idxmax()
        _top_pass_idx  = pct[_pass_col].idxmax()
        _top_shot_name = agg.loc[_top_shot_idx, "player_name"].split()[0]
        _top_pass_name = agg.loc[_top_pass_idx, "player_name"].split()[0]
        if _top_shot_name != _top_pass_name:
            headline = f"{_top_pass_name} constrói  ·  {_top_shot_name} decide"
        else:
            headline = f"{_top_shot_name} domina penetração e finalização"
    else:
        headline = "Os jogadores mais influentes do Sport na Série B"

    # ── Figura ────────────────────────────────────────────────────────────────
    # 9.5 × 12" @ 120 DPI → 1140 × 1440 px  (ótimo para portrait X/Instagram)
    fig = plt.figure(figsize=(9.5, 12.0), facecolor=BG)

    # ── Header ────────────────────────────────────────────────────────────────
    ax_h = fig.add_axes([0.0, 0.942, 1.0, 0.058])
    ax_h.set_facecolor(BG)
    ax_h.axis("off")

    sport_arr = load_logo(LOGOS_DIR / f"{SPORT_ID}.png", 64)
    if sport_arr is not None:
        ax_h.imshow(sport_arr, extent=[0.009, 0.073, 0.06, 0.94],
                    aspect="auto", transform=ax_h.transAxes, zorder=5)

    ax_h.text(0.086, 0.72, headline,
              transform=ax_h.transAxes,
              fontsize=17, fontweight="bold", color=WHITE, va="center", ha="left")
    ax_h.text(0.086, 0.22,
              f"Top 10 jogadores de linha  ·  R1–R{max_round}  ·  % do total acumulado do time",
              transform=ax_h.transAxes,
              fontsize=8.5, color=GRAY, va="center", ha="left")

    srl_arr = load_logo(SRL_LOGO, 64)
    if srl_arr is not None:
        ax_h.imshow(srl_arr, extent=[0.927, 0.993, 0.06, 0.94],
                    aspect="auto", transform=ax_h.transAxes, zorder=5)

    # Linha separadora ouro
    sep = fig.add_axes([0.012, 0.9385, 0.976, 0.0018])
    sep.set_facecolor(GOLD)
    sep.axis("off")

    # ── Grid axes ─────────────────────────────────────────────────────────────
    # Colunas: x = 0..5  |  Linhas: y = 0 (base)..9 (topo)
    # Margem esq p/ rank + nome + barra de minutos: ~3.8 unidades
    # Margem dir: ~0.6 unidades
    # Margem sup (cabeçalhos): ~1.3 unidades
    X_MIN, X_MAX = -3.85, (M - 1) + 0.65
    Y_MIN, Y_MAX = -0.55, 10.20

    ax = fig.add_axes([0.012, 0.022, 0.976, 0.912])
    ax.set_facecolor(BG)
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.axis("off")

    # ── Listras de linha (alternadas, imperceptíveis à distância) ─────────────
    x_frac_start = (-0.55 - X_MIN) / (X_MAX - X_MIN)
    for i in range(N):
        color = ROW_ALT if i % 2 == 0 else BG
        ax.axhspan(i - 0.50, i + 0.50, xmin=0.0, xmax=1.0,
                   color=color, zorder=0)

    # ── Cabeçalhos das métricas ───────────────────────────────────────────────
    for j, (_, title) in enumerate(metrics):
        x = float(j)
        # Linha de acento acima do cabeçalho
        ax.plot([x - 0.38, x + 0.38], [9.52, 9.52],
                color=GOLD, linewidth=1.2, solid_capstyle="round", zorder=8)
        ax.text(x, 9.60, title,
                ha="center", va="bottom",
                color=GOLD, fontsize=7.6, fontweight="bold",
                multialignment="center", linespacing=1.25, zorder=9)

    # ── Divisória vertical (nomes ↔ grade) ────────────────────────────────────
    ax.axvline(-0.55, ymin=0.015, ymax=0.91,
               color="#1a1a1e", linewidth=0.8, zorder=1)

    # ── Círculos e valores ────────────────────────────────────────────────────
    for i in range(N):
        player  = agg.iloc[i]
        rank_no = N - i   # rank 1 = maior minutagem (topo visual)

        for j, (col, _) in enumerate(metrics):
            x    = float(j)
            y    = float(i)
            p    = float(pct.loc[i, col])
            mx   = float(pct[col].max())
            frac = p / mx if mx > 0 else 0.0
            top1 = mx > 0 and abs(p - mx) < 0.001
            top2 = (not top1) and p > 0 and abs(p - top2_thresholds[col]) < 0.001

            if p <= 0:
                s_val      = float(S_ZERO)
                fill_color = "#1c1600"
                txt        = "—"
                txt_color  = "#444444"
                fw         = "normal"
            else:
                s_val      = S_MIN_VAL + np.sqrt(frac) * (S_MAX_SIZE - S_MIN_VAL)
                fill_color = gold_shade(frac)
                txt        = f"{p:.1f}%"
                txt_color  = text_on_gold(frac)
                fw         = "bold" if top1 else "normal"

            # 1 — Anel fantasma: referência do máximo da coluna
            ax.scatter(x, y, s=S_MAX_SIZE, facecolors="none",
                       edgecolors="#252528", linewidths=0.7,
                       marker="o", zorder=2)

            # 2 — Glow suave: top-1 ou top-2 da coluna
            if top1 and p > 0:
                ax.scatter(x, y, s=s_val * 1.55, color=GLOW_PEAK,
                           alpha=0.10, marker="o", linewidths=0, zorder=3)
            elif top2:
                ax.scatter(x, y, s=s_val * 1.40, color=GLOW_PEAK,
                           alpha=0.06, marker="o", linewidths=0, zorder=3)

            # 3 — Círculo de valor, tamanho proporcional à % (escala sqrt)
            ax.scatter(x, y, s=s_val, color=fill_color,
                       marker="o", linewidths=0, zorder=4)

            # 4 — Anel ouro: apenas o líder da coluna
            if top1 and p > 0:
                ax.scatter(x, y, s=s_val, facecolors="none",
                           edgecolors=GOLD, linewidths=1.8,
                           marker="o", zorder=5)

            # 5 — Percentual centrado
            ax.text(x, y, txt,
                    ha="center", va="center",
                    color=txt_color, fontsize=7.3, fontweight=fw, zorder=6)

        # ── Coluna esquerda: rank + nome + barra de minutos ───────────────────
        y     = float(i)
        mins  = int(player["minutes_played"])
        name  = shorten(player["player_name"])
        fmins = mins / max_mins   # fração de minutos (0..1)

        # Número de rank (ouro escuro, grande, indexador lateral)
        ax.text(-3.65, y, f"{rank_no:02d}",
                ha="left", va="center",
                color="#6b5200", fontsize=15, fontweight="bold", zorder=7)

        # Nome do jogador
        ax.text(-3.10, y + 0.175, name,
                ha="left", va="center",
                color=LGRAY, fontsize=9.5, fontweight="bold", zorder=7)

        # Barra de minutagem
        BAR_X0, BAR_X1 = -3.10, -0.70
        BAR_LEN = BAR_X1 - BAR_X0
        # Trilho
        ax.barh(y - 0.17, BAR_LEN, height=0.085, left=BAR_X0,
                color="#1a1a1e", zorder=6)
        # Preenchimento
        ax.barh(y - 0.17, BAR_LEN * fmins, height=0.085, left=BAR_X0,
                color=GOLD_DEEP, zorder=7)
        # Minutos
        ax.text(BAR_X1 + 0.08, y - 0.17, f"{mins}'",
                ha="left", va="center",
                color=GRAY, fontsize=6.5, zorder=7)

    # ── Legenda de cor + rodapé (fig.text para não afetar bbox das axes) ────────
    fig.text(0.14, 0.015, "menor contribuição",
             ha="left", va="bottom", color=GRAY, fontsize=6.0)
    fig.text(0.50, 0.015, "tamanho = % do time · por coluna",
             ha="center", va="bottom", color="#444444", fontsize=6.0)
    fig.text(0.86, 0.015, "maior contribuição",
             ha="right", va="bottom", color=GOLD, fontsize=6.0)
    fig.text(0.50, 0.006,
             "Valores negativos e nulos → zero  ·  Dados: SofaScore  ·  @SportRecifeLab",
             ha="center", va="bottom", color="#303030", fontsize=6.2)

    # ── Salvar ────────────────────────────────────────────────────────────────
    if args.normalize_per90:
        fig.text(0.50, 0.013,
                 "Normalizacao por 90 min",
                 ha="center", va="bottom", color=GOLD_DEEP, fontsize=6.2)

    today   = date.today().strftime("%Y-%m-%d")
    out_dir = BASE_DIR / "pending_posts" / f"{today}_contribuicao-jogadores-r{max_round}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.output_name

    fig.savefig(out_path, dpi=120, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Salvo: {out_path}")


if __name__ == "__main__":
    main()
