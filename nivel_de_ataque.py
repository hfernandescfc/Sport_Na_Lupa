"""
Nivel de Ataque — Quadro semanal @SportRecifeLab
=================================================
Compara o xG produzido por cada clube contra o xG medio que o adversario
concedia ate aquele momento na Serie B.

USO:
    python nivel_de_ataque.py             # usa a ultima rodada completa
    python nivel_de_ataque.py --round 5   # forca rodada especifica

SAIDA (por execucao):
    pending_posts/{data}_nivel-de-ataque-r{N}/
        card.png
        tweet.txt
        metadata.json
"""

import sys
import json
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import date
from pathlib import Path
from PIL import Image

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
MATCHES   = BASE_DIR / "data/curated/serie_b_2026/matches.csv"
STATS     = BASE_DIR / "data/curated/serie_b_2026/team_match_stats.csv"
LOGOS_DIR = BASE_DIR / "data/cache/logos"
SRL_LOGO  = BASE_DIR / "sportrecifelab_avatar.png"

TEAM_LOGO_ID = {
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
    "juventude":       1980,
    "londrina":        2022,
    "nautico":         2011,
    "novorizontino":   135514,
    "operario-pr":     39634,
    "ponte-preta":     1969,
    "sao-bernardo":    47504,
    "sport":           1959,
    "vila-nova-fc":    2021,
}

BG     = "#0d0d0d"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
LGRAY  = "#CCCCCC"
GRAY   = "#555555"
DGRAY  = "#2a2a2a"
GREEN  = "#22C55E"
RED    = "#EF4444"

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--round", type=int, default=None,
                    help="Rodada a gerar (padrao: ultima completa)")
args = parser.parse_args()

# ── Carrega e filtra dados ────────────────────────────────────────────────────
# team_match_stats é fonte de verdade para rodadas — matches.csv pode estar incompleto
stats_df = pd.read_csv(STATS)

# Considera apenas partidas com stats completas (2 times por match_code)
valid_codes = stats_df.groupby("match_code").size()
valid_codes = valid_codes[valid_codes == 2].index
stats_df = stats_df[stats_df["match_code"].isin(valid_codes)].copy()

MAX_ROUND = args.round if args.round else int(stats_df["round"].max())

stats_df  = stats_df[stats_df["round"] <= MAX_ROUND].copy()

ROUNDS    = sorted(stats_df["round"].unique())
MIN_ROUND = int(ROUNDS[0])

print(f"Rodadas: {ROUNDS}  (gerando ate R{MAX_ROUND})")

# ── Monta duelos (atacante x defensor por partida) ────────────────────────────
rows = []
for match_code, grp in stats_df.groupby("match_code"):
    if len(grp) != 2:
        continue
    t = grp[["team_key", "team_name", "expected_goals", "round"]].to_dict("records")
    for i, j in [(0, 1), (1, 0)]:
        rows.append({
            "round":         t[i]["round"],
            "attacker_key":  t[i]["team_key"],
            "attacker_name": t[i]["team_name"],
            "defender_key":  t[j]["team_key"],
            "xg_produced":   t[i]["expected_goals"],
        })

duels = pd.DataFrame(rows).sort_values("round").reset_index(drop=True)

# ── xG medio concedido pelo adversario ate aquela rodada ─────────────────────
def avg_xg_conceded_before(defender_key, before_round, df):
    prior = df[(df["defender_key"] == defender_key) & (df["round"] < before_round)]
    return prior["xg_produced"].mean() if not prior.empty else np.nan

duels["xg_ctx"] = duels.apply(
    lambda r: avg_xg_conceded_before(r["defender_key"], r["round"], duels), axis=1
)
league_avg = duels["xg_produced"].mean()
duels["xg_ctx_filled"] = duels["xg_ctx"].fillna(league_avg)

# ── Agrega por time ───────────────────────────────────────────────────────────
agg = (
    duels.groupby(["attacker_key", "attacker_name"])
    .agg(xG_total=("xg_produced", "sum"), xG_ctx=("xg_ctx_filled", "sum"))
    .reset_index()
    .rename(columns={"attacker_name": "team"})
)
agg["delta"]     = agg["xG_total"] - agg["xG_ctx"]
agg["delta_pct"] = (agg["delta"] / agg["xG_ctx"] * 100).round(1)
agg = agg.sort_values("delta").reset_index(drop=True)  # bottom→top no grafico

# ── Ranking da rodada anterior (para badge de movimento) ─────────────────────
PREV_ROUND = MAX_ROUND - 1
rank_move = {}  # attacker_key → diff (positivo = subiu)
if PREV_ROUND >= MIN_ROUND:
    duels_prev = duels[duels["round"] <= PREV_ROUND].copy()
    league_avg_prev = duels_prev["xg_produced"].mean()
    duels_prev["xg_ctx"] = duels_prev.apply(
        lambda r: avg_xg_conceded_before(r["defender_key"], r["round"], duels_prev), axis=1
    )
    duels_prev["xg_ctx_filled"] = duels_prev["xg_ctx"].fillna(league_avg_prev)
    agg_prev = (
        duels_prev.groupby("attacker_key")
        .agg(xG_total=("xg_produced", "sum"), xG_ctx=("xg_ctx_filled", "sum"))
        .reset_index()
    )
    agg_prev["delta"] = agg_prev["xG_total"] - agg_prev["xG_ctx"]
    agg_prev = agg_prev.sort_values("xG_total").reset_index(drop=True)
    # rank 1 = melhor (maior delta) → posição no ranking de cima p/ baixo
    prev_rank = {row["attacker_key"]: (len(agg_prev) - i) for i, row in agg_prev.iterrows()}
    curr_rank = {row["attacker_key"]: (len(agg) - i) for i, row in agg.iterrows()}
    for key in curr_rank:
        if key in prev_rank:
            rank_move[key] = prev_rank[key] - curr_rank[key]  # positivo = subiu

# ── Output dir ────────────────────────────────────────────────────────────────
today   = date.today().isoformat()
OUT_DIR = BASE_DIR / f"pending_posts/{today}_nivel-de-ataque-r{MAX_ROUND}"
OUT_DIR.mkdir(parents=True, exist_ok=True)

round_label = f"R{MIN_ROUND}-R{MAX_ROUND}" if MIN_ROUND != MAX_ROUND else f"R{MAX_ROUND}"

# ── Figura ────────────────────────────────────────────────────────────────────
N        = len(agg)
FIG_W    = 10
FIG_H    = 14
HEADER_H = 0.13
FOOTER_H = 0.10
CHART_H  = 1 - HEADER_H - FOOTER_H
CHART_L  = 0.26
CHART_W  = 0.70

fig    = plt.figure(figsize=(FIG_W, FIG_H), facecolor=BG)
ax_hdr = fig.add_axes([0, 1 - HEADER_H, 1, HEADER_H], facecolor=BG)
ax     = fig.add_axes([CHART_L, FOOTER_H, CHART_W, CHART_H], facecolor=BG)
ax_ftr = fig.add_axes([0, 0, 1, FOOTER_H], facecolor=BG)

for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(colors=LGRAY, labelsize=8.5)
ax.xaxis.set_tick_params(color=GRAY)
ax.yaxis.set_visible(False)

Y_MIN = -0.55
Y_MAX = N - 0.45
X_MIN = max(0, agg[["xG_total", "xG_ctx"]].min().min() - 0.8)
X_MAX = agg[["xG_total", "xG_ctx"]].max().max() + 1.0
ax.set_xlim(X_MIN, X_MAX)
ax.set_ylim(Y_MIN, Y_MAX)

def data_y_to_fig(y_data):
    t = (y_data - Y_MIN) / (Y_MAX - Y_MIN)
    return FOOTER_H + CHART_H * t

# ── Dumbbell ──────────────────────────────────────────────────────────────────
LOGO_SIZE_FIG = 0.040

for i, row in agg.iterrows():
    y        = float(i)
    xg_prod  = row["xG_total"]
    xg_ctx   = row["xG_ctx"]
    is_sport = row["attacker_key"] == "sport"
    over     = xg_prod >= xg_ctx
    line_col = GREEN if over else RED
    alpha    = 1.0 if is_sport else 0.75

    if i % 2 == 0:
        ax.axhspan(y - 0.45, y + 0.45, color=DGRAY, alpha=0.22, zorder=0)

    ax.plot([xg_ctx, xg_prod], [y, y],
            color=line_col, lw=2.8 if is_sport else 1.8,
            alpha=alpha, zorder=2, solid_capstyle="round")

    ax.scatter(xg_ctx, y, color="#888888", s=65, zorder=3, alpha=alpha)

    dot_col = YELLOW if is_sport else (GREEN if over else RED)
    ax.scatter(xg_prod, y, color=dot_col, s=120 if is_sport else 80,
               zorder=4, alpha=alpha)

    dx        = xg_prod - xg_ctx
    label_x   = max(xg_prod, xg_ctx) + 0.10
    label_col = YELLOW if is_sport else (GREEN if over else RED)
    ax.text(label_x, y, f"{'+'if dx>=0 else ''}{dx:.1f}",
            va="center", ha="left",
            color=label_col, fontsize=8 if is_sport else 7.5,
            fontweight="bold" if is_sport else "normal",
            alpha=alpha)

    # Escudo
    logo_id   = TEAM_LOGO_ID.get(row["attacker_key"])
    logo_path = LOGOS_DIR / f"{logo_id}.png" if logo_id else None
    y_fig_c   = data_y_to_fig(y)
    logo_s    = LOGO_SIZE_FIG * 1.25 if is_sport else LOGO_SIZE_FIG
    if logo_path and logo_path.exists():
        try:
            img_arr = np.array(Image.open(logo_path).convert("RGBA"))
            ax_logo = fig.add_axes(
                [CHART_L - logo_s - 0.005, y_fig_c - logo_s / 2, logo_s, logo_s],
                facecolor="none"
            )
            ax_logo.imshow(img_arr)
            ax_logo.axis("off")
            ax_logo.set_zorder(10)
        except Exception as e:
            print(f"  logo erro {row['attacker_key']}: {e}")

    # Nome (recuado para abrir espaço ao badge)
    badge_x = CHART_L - logo_s - 0.010
    name_x  = CHART_L - logo_s - 0.055
    fig.text(name_x, y_fig_c, row["team"],
             ha="right", va="center",
             color=YELLOW if is_sport else LGRAY,
             fontsize=8.2 if is_sport else 7.8,
             fontweight="bold" if is_sport else "normal")

    # Badge de movimento (▲N / ▼N / —) na mesma linha, entre nome e logo
    move = rank_move.get(row["attacker_key"])
    if move is None:
        badge, badge_col = "—", GRAY
    elif move > 0:
        badge, badge_col = f"▲{move}", GREEN
    elif move < 0:
        badge, badge_col = f"▼{abs(move)}", RED
    else:
        badge, badge_col = "—", GRAY
    fig.text(badge_x, y_fig_c, badge,
             ha="right", va="center",
             color=badge_col, fontsize=6.5,
             fontweight="bold")

# ── Eixo X ────────────────────────────────────────────────────────────────────
ax.set_xticks(np.arange(int(X_MIN) + 1, int(X_MAX) + 1, 1))
ax.grid(axis="x", color=GRAY, alpha=0.2, lw=0.6, linestyle="--")
ax.set_xlabel(f"xG acumulado ({round_label})", color=LGRAY, fontsize=8, labelpad=6)

# ── Legenda ───────────────────────────────────────────────────────────────────
LEG_Y1 = FOOTER_H - 0.028
LEG_Y2 = FOOTER_H - 0.050
fig.text(CHART_L,        LEG_Y1, "●", ha="left", va="center", color=GREEN,     fontsize=10)
fig.text(CHART_L + 0.018, LEG_Y1, "xG produzido",
         ha="left", va="center", color=LGRAY, fontsize=7.5)
fig.text(CHART_L,        LEG_Y2, "●", ha="left", va="center", color="#888888", fontsize=10)
fig.text(CHART_L + 0.018, LEG_Y2,
         "xG esperado  (media de xG concedido pelo adversario ate aquela rodada)",
         ha="left", va="center", color=LGRAY, fontsize=7.5)

# ── Header ────────────────────────────────────────────────────────────────────
ax_hdr.axis("off")
ax_hdr.text(0.5, 0.88, "NIVEL DE ATAQUE",
            ha="center", va="top", transform=ax_hdr.transAxes,
            color=YELLOW, fontsize=15, fontweight="bold",
            fontfamily="Franklin Gothic Heavy")
ax_hdr.text(0.5, 0.54,
            "xG produzido  x  media de xG concedido pelo adversario ate aquela rodada",
            ha="center", va="top", transform=ax_hdr.transAxes,
            color=LGRAY, fontsize=8.2)
ax_hdr.text(0.5, 0.20,
            f"Serie B 2026  -  {round_label}",
            ha="center", va="top", transform=ax_hdr.transAxes,
            color=GRAY, fontsize=8)
ax_hdr.axhline(0.08, color=YELLOW, lw=1.5, xmin=0.04, xmax=0.96)

# ── Footer ────────────────────────────────────────────────────────────────────
ax_ftr.axis("off")
try:
    srl_arr  = np.array(Image.open(SRL_LOGO).convert("RGBA"))
    srl_size = 0.058
    ax_srl   = fig.add_axes([0.030, 0.014, srl_size, srl_size * FIG_W / FIG_H])
    ax_srl.imshow(srl_arr)
    ax_srl.axis("off")
except Exception:
    pass
fig.text(0.105, 0.044, "@SportRecifeLab",
         ha="left", va="center", color=LGRAY, fontsize=8, fontweight="bold")
fig.text(0.105, 0.026, "Dados: SofaScore",
         ha="left", va="center", color=GRAY, fontsize=7)

# ── Salva card ────────────────────────────────────────────────────────────────
card_path = OUT_DIR / "card.png"
fig.savefig(card_path, dpi=160, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"Card: {card_path}")

# ── Gera tweet.txt ────────────────────────────────────────────────────────────
top3  = agg.sort_values("delta", ascending=False).head(3)
bot3  = agg.sort_values("delta").head(3)

def fmt_badge(key):
    m = rank_move.get(key)
    if m is None or m == 0:
        return ""
    return f" ▲{m}" if m > 0 else f" ▼{abs(m)}"

def fmt_line(row, emoji):
    return f"{emoji} {row['team']}: {row['delta']:+.2f}{fmt_badge(row['attacker_key'])}"

top_lines = "\n".join(fmt_line(r, "✅") for _, r in top3.iterrows())
bot_lines = "\n".join(fmt_line(r, "❌") for _, r in bot3.iterrows())

# posicao do Sport no ranking
sport_rank = N - int(agg[agg["attacker_key"] == "sport"].index[0])
sport_row  = agg[agg["attacker_key"] == "sport"].iloc[0]
sport_move = rank_move.get("sport")
sport_prev = sport_rank + sport_move if sport_move is not None else None

# Narrativa do tweet 1: destaca maior subida/queda se houver rodada anterior
is_series = bool(rank_move) and PREV_ROUND >= MIN_ROUND
if is_series:
    biggest_up_key = max(rank_move, key=rank_move.get)
    biggest_dn_key = min(rank_move, key=rank_move.get)
    up_team = agg[agg["attacker_key"] == biggest_up_key].iloc[0]["team"]
    dn_team = agg[agg["attacker_key"] == biggest_dn_key].iloc[0]["team"]
    up_n    = rank_move[biggest_up_key]
    dn_n    = abs(rank_move[biggest_dn_key])
    tweet1  = (
        f"Nova edição do #NivelDeAtaque — xG produzido x contexto defensivo.\n\n"
        f"Após R{MAX_ROUND}, o ranking balançou:\n"
        f"▲ {up_team} subiu {up_n} posições.\n"
        f"▼ {dn_team} caiu {dn_n}.\n\n"
        f"O retrato da Série B segue mudando. 🧵"
    )
else:
    tweet1 = (
        "Criar xG é uma coisa.\n\n"
        "Criar xG além do que o adversário costuma conceder é outra.\n\n"
        "Cruzamos os dois — e o ranking muda bastante a narrativa da Série B. 🧵"
    )

# Linha do Sport com referência à rodada anterior (se houver)
if sport_move is not None and sport_move != 0:
    arrow = "▲" if sport_move > 0 else "▼"
    sport_ref = f"#{sport_rank} ({arrow}{abs(sport_move)})"
else:
    sport_ref = f"#{sport_rank}"

ctx_note = (
    f"xG × contexto defensivo · setas vs R{PREV_ROUND}"
    if is_series else "xG produzido × contexto defensivo"
)

tweet = f"""— THREAD —

[1/3 — sem imagem]

{tweet1}

---

[2/3 — card: card.png]

#NivelDeAtaque ({round_label})
{ctx_note}

{top_lines}

{bot_lines}

Sport: {sport_ref} · {sport_row['delta']:+.2f}

Qual time te surpreendeu mais? 👇

---

[3/3 — reply ao tweet 2]

Metodologia: para cada partida, calculamos a média de xG concedido pelo adversário nas rodadas anteriores. O delta = xG real produzido − esse contexto.

Dados: SofaScore · {round_label}

📊 @SportRecifeLab
#SerieB #SerieB2026 #SportRecife #NivelDeAtaque
"""

tweet_path = OUT_DIR / "tweet.txt"
tweet_path.write_text(tweet, encoding="utf-8")
print(f"Tweet: {tweet_path}")

# ── Gera metadata.json ────────────────────────────────────────────────────────
meta = {
    "quadro":          "Nivel de Ataque",
    "post_date":       today,
    "slug":            f"nivel-de-ataque-r{MAX_ROUND}",
    "topic":           "offensive_xg_vs_defensive_context",
    "season":          2026,
    "rounds_covered":  [int(r) for r in ROUNDS],
    "max_round":       int(MAX_ROUND),
    "cards":           {"card.png": "pronto"},
    "status":          "pronto para publicar",
}
meta_path = OUT_DIR / "metadata.json"
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Metadata: {meta_path}")
print(f"\nPronto. Pasta: {OUT_DIR}")
