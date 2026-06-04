# -*- coding: utf-8 -*-
"""
Card: Contribuição dos jogadores do Sport em uma única partida
Filosofia visual "Thermal Glow" — adaptada de generate_player_contribution_card.py

Default: Sport 1x0 Grêmio Novorizontino — R6 Série B 2026 (event_id 15526043)
Saída: pending_posts/{data}_contribuicao-jogadores-{slug}/card.png
"""

import argparse
import re
import unicodedata
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image
from datetime import date, datetime

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).parent
DATA_FILE   = BASE_DIR / "data/curated/sport_2026/player_match_stats.csv"
MATCHES_FILE= BASE_DIR / "data/curated/sport_2026/matches.csv"
LOGOS_DIR   = BASE_DIR / "data/cache/logos"
SRL_LOGO    = BASE_DIR / "sportrecifelab_avatar.png"
SPORT_ID    = 1959

# ── Palette ───────────────────────────────────────────────────────────────────
BG        = "#0a0a0c"
ROW_ALT   = "#0e0e11"
GOLD      = "#F5C400"
GOLD_DEEP = "#7a5200"
WHITE     = "#FFFFFF"
LGRAY     = "#c0c0c0"
GRAY      = "#555555"
GLOW_PEAK = "#ffd54a"

# ── Métricas ──────────────────────────────────────────────────────────────────
METRICS = [
    ("accurate_opposition_half_passes",  "PASSES\nCAMPO ADV."),
    ("total_progression",                "PROGRESSÃO\nCOM A BOLA"),
    ("total_shots",                      "FINA-\nLIZAÇÕES"),
]

GK_IDS     = {871291, 1019685, 1020235}
S_MAX_SIZE = 2700
S_MIN_VAL  = 480
S_ZERO     = 200

DEFAULT_EVENT_ID = 15526043   # Sport 1x0 Grêmio Novorizontino — R6


# ── Utilidades ────────────────────────────────────────────────────────────────
def load_logo(path: Path, target: int = 60):
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
    f = float(np.clip(fraction, 0.0, 1.0))
    c_dim  = np.array([0x7a, 0x5a, 0x00], float) / 255
    c_full = np.array([0xF5, 0xC4, 0x00], float) / 255
    return tuple(c_dim + f * (c_full - c_dim))


def text_on_gold(fraction: float) -> str:
    return "#1a0d00" if fraction >= 0.72 else "#ffffff"


def slugify(text: str) -> str:
    txt = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    txt = re.sub(r"[^a-zA-Z0-9]+", "-", txt).strip("-").lower()
    return txt or "match"


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-id", type=int, default=DEFAULT_EVENT_ID)
    parser.add_argument("--exclude-metric", action="append", default=[])
    parser.add_argument("--output-name", default="card.png")
    parser.add_argument("--min-minutes", type=int, default=10,
                        help="Filtra jogadores com menos minutos que esse valor.")
    args = parser.parse_args()

    metrics = [(k, l) for k, l in METRICS if k not in set(args.exclude_metric)]
    if not metrics:
        raise ValueError("At least one metric must remain after exclusions.")

    # ── Dados da partida ─────────────────────────────────────────────────────
    df  = pd.read_csv(DATA_FILE, encoding="utf-8")
    mdf = pd.read_csv(MATCHES_FILE, encoding="utf-8")

    match_row = mdf[mdf["event_id"] == args.event_id]
    if match_row.empty:
        raise ValueError(f"event_id {args.event_id} não encontrado em matches.csv")
    m = match_row.iloc[0]

    sport_is_home = (m.get("home_team_key") == "sport")
    opp_name = m["away_team"] if sport_is_home else m["home_team"]
    home_score = m.get("home_score")
    away_score = m.get("away_score")
    if pd.notna(home_score) and pd.notna(away_score):
        sport_score = int(home_score) if sport_is_home else int(away_score)
        opp_score   = int(away_score) if sport_is_home else int(home_score)
        score_str = f"{sport_score}x{opp_score}"
    else:
        score_str = ""
    round_no  = int(m["competition_round"]) if pd.notna(m.get("competition_round")) else None
    match_dt  = m.get("match_date_utc") or ""
    try:
        match_label_dt = datetime.fromisoformat(str(match_dt).replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except Exception:
        match_label_dt = ""

    # ── Filtra players da partida ────────────────────────────────────────────
    sb = df[(df["event_id"] == args.event_id) & (df["team_key"] == "sport")].copy()
    sb = sb[~sb["player_id"].isin(GK_IDS)]
    sb["minutes_played"] = pd.to_numeric(sb["minutes_played"], errors="coerce").fillna(0)
    sb = sb[sb["minutes_played"] >= args.min_minutes]

    cols = [m for m, _ in metrics]
    for c in cols:
        sb[c] = pd.to_numeric(sb[c], errors="coerce").fillna(0).clip(lower=0)

    pool = sb[["player_id", "player_name", "minutes_played", *cols]].copy()

    # Top 10 por minutos
    top_mins_ids = set(pool.sort_values("minutes_played", ascending=False).head(10)["player_id"])

    # Top 3 de qualquer métrica (union)
    top_metric_ids: set = set()
    for c in cols:
        top_metric_ids.update(pool.nlargest(3, c)["player_id"].tolist())

    selected_ids = top_mins_ids | top_metric_ids
    agg = (
        pool[pool["player_id"].isin(selected_ids)]
          .sort_values("minutes_played", ascending=True)
          .reset_index(drop=True)
    )

    if agg.empty:
        raise ValueError("Sem jogadores acima do filtro de minutos para essa partida.")

    N = len(agg)
    M = len(metrics)

    # % de contribuição (por coluna)
    pct = pd.DataFrame(index=agg.index)
    for c in cols:
        total = agg[c].sum()
        pct[c] = (agg[c] / total * 100) if total > 0 else 0.0

    max_mins = float(agg["minutes_played"].max())

    top2_thresholds: dict[str, float] = {}
    for c in cols:
        sv = pct[c].sort_values(ascending=False).values
        top2_thresholds[c] = float(sv[1]) if len(sv) > 1 else float(sv[0])

    # ── Headline dinâmica ────────────────────────────────────────────────────
    _shot_col = "total_shots"
    _pass_col = "accurate_opposition_half_passes"
    if _shot_col in pct.columns and _pass_col in pct.columns and pct[_shot_col].sum() > 0:
        _top_shot_idx  = pct[_shot_col].idxmax()
        _top_pass_idx  = pct[_pass_col].idxmax()
        _top_shot_name = agg.loc[_top_shot_idx, "player_name"].split()[0]
        _top_pass_name = agg.loc[_top_pass_idx, "player_name"].split()[0]
        if _top_shot_name != _top_pass_name:
            headline = f"{_top_pass_name} constrói  ·  {_top_shot_name} decide"
        else:
            headline = f"{_top_shot_name} domina penetração e finalização"
    else:
        headline = f"Sport {score_str} {opp_name}".strip()

    subtitle_bits = []
    if round_no is not None:
        subtitle_bits.append(f"R{round_no} Série B")
    subtitle_bits.append(f"Sport {score_str} {opp_name}".strip())
    if match_label_dt:
        subtitle_bits.append(match_label_dt)
    subtitle_bits.append("% do total do time na partida")
    subtitle = "  ·  ".join(subtitle_bits)

    # ── Figura ────────────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(9.5, 12.0), facecolor=BG)

    # Header
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
    ax_h.text(0.086, 0.22, subtitle,
              transform=ax_h.transAxes,
              fontsize=8.5, color=GRAY, va="center", ha="left")

    srl_arr = load_logo(SRL_LOGO, 64)
    if srl_arr is not None:
        ax_h.imshow(srl_arr, extent=[0.927, 0.993, 0.06, 0.94],
                    aspect="auto", transform=ax_h.transAxes, zorder=5)

    sep = fig.add_axes([0.012, 0.9385, 0.976, 0.0018])
    sep.set_facecolor(GOLD)
    sep.axis("off")

    # Grid axes — Y_MAX dinâmico para acomodar N > 10
    X_MIN, X_MAX = -3.85, (M - 1) + 0.65
    Y_MAX = N - 1 + 1.20   # 1.2 unidades acima do último jogador (cabeçalhos)
    Y_MIN = -0.55

    ax = fig.add_axes([0.012, 0.022, 0.976, 0.912])
    ax.set_facecolor(BG)
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.axis("off")

    for i in range(N):
        color = ROW_ALT if i % 2 == 0 else BG
        ax.axhspan(i - 0.50, i + 0.50, xmin=0.0, xmax=1.0, color=color, zorder=0)

    # Cabeçalhos — posicionados acima do último jogador
    HDR_Y     = float(N - 1) + 0.52   # linha de acento
    HDR_TXT_Y = float(N - 1) + 0.60   # texto do cabeçalho

    for j, (_, title) in enumerate(metrics):
        x = float(j)
        ax.plot([x - 0.38, x + 0.38], [HDR_Y, HDR_Y],
                color=GOLD, linewidth=1.2, solid_capstyle="round", zorder=8)
        ax.text(x, HDR_TXT_Y, title,
                ha="center", va="bottom",
                color=GOLD, fontsize=7.6, fontweight="bold",
                multialignment="center", linespacing=1.25, zorder=9)

    ax.axvline(-0.55, ymin=0.015, ymax=0.91,
               color="#1a1a1e", linewidth=0.8, zorder=1)

    # Círculos
    for i in range(N):
        player  = agg.iloc[i]
        rank_no = N - i

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

            ax.scatter(x, y, s=S_MAX_SIZE, facecolors="none",
                       edgecolors="#252528", linewidths=0.7,
                       marker="o", zorder=2)

            if top1 and p > 0:
                ax.scatter(x, y, s=s_val * 1.55, color=GLOW_PEAK,
                           alpha=0.10, marker="o", linewidths=0, zorder=3)
            elif top2:
                ax.scatter(x, y, s=s_val * 1.40, color=GLOW_PEAK,
                           alpha=0.06, marker="o", linewidths=0, zorder=3)

            ax.scatter(x, y, s=s_val, color=fill_color,
                       marker="o", linewidths=0, zorder=4)

            if top1 and p > 0:
                ax.scatter(x, y, s=s_val, facecolors="none",
                           edgecolors=GOLD, linewidths=1.8,
                           marker="o", zorder=5)

            ax.text(x, y, txt,
                    ha="center", va="center",
                    color=txt_color, fontsize=7.3, fontweight=fw, zorder=6)

        # Coluna esquerda
        y     = float(i)
        mins  = int(player["minutes_played"])
        name  = shorten(player["player_name"])
        fmins = mins / max_mins if max_mins > 0 else 0.0

        ax.text(-3.65, y, f"{rank_no:02d}",
                ha="left", va="center",
                color="#6b5200", fontsize=15, fontweight="bold", zorder=7)

        ax.text(-3.10, y + 0.175, name,
                ha="left", va="center",
                color=LGRAY, fontsize=9.5, fontweight="bold", zorder=7)

        BAR_X0, BAR_X1 = -3.10, -0.70
        BAR_LEN = BAR_X1 - BAR_X0
        ax.barh(y - 0.17, BAR_LEN, height=0.085, left=BAR_X0,
                color="#1a1a1e", zorder=6)
        ax.barh(y - 0.17, BAR_LEN * fmins, height=0.085, left=BAR_X0,
                color=GOLD_DEEP, zorder=7)
        ax.text(BAR_X1 + 0.08, y - 0.17, f"{mins}'",
                ha="left", va="center",
                color=GRAY, fontsize=6.5, zorder=7)

    # Rodapé
    fig.text(0.14, 0.015, "menor contribuição",
             ha="left", va="bottom", color=GRAY, fontsize=6.0)
    fig.text(0.50, 0.015, "tamanho = % do time · por coluna",
             ha="center", va="bottom", color="#444444", fontsize=6.0)
    fig.text(0.86, 0.015, "maior contribuição",
             ha="right", va="bottom", color=GOLD, fontsize=6.0)
    fig.text(0.50, 0.006,
             "Valores negativos e nulos → zero  ·  Dados: SofaScore  ·  @SportRecifeLab",
             ha="center", va="bottom", color="#303030", fontsize=6.2)

    # Salvar
    today    = date.today().strftime("%Y-%m-%d")
    opp_slug = slugify(opp_name)
    out_dir  = BASE_DIR / "pending_posts" / f"{today}_contribuicao-jogadores-{opp_slug}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.output_name

    fig.savefig(out_path, dpi=120, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Salvo: {out_path}")


if __name__ == "__main__":
    main()
