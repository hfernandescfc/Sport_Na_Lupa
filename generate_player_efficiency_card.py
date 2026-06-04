"""
Eficiência Ofensiva Individual — Série B 2026
=============================================
Scatter: Chutes/90 (volume) × Gols/90 (produção)
  - Tamanho da bolha: minutos jogados
  - Cor: taxa de conversão (gols/chutes)  RED→GRAY→GREEN
  - Anel dourado: jogadores do Sport Recife
  - Labels: top artilheiros por total de gols
  - Apenas jogadores com >= 1 gol

Fontes de dados:
  data/curated/serie_b_2026/player_match_stats.csv  (R1-R5; sem Sport R1-R4)
  data/curated/sport_2026/player_match_stats.csv    (Sport R1-R4 Série B)
  data/curated/serie_b_2026/match_incidents.csv     (gols R1-R4; sem partidas do Sport)
  data/curated/sport_2026/match_incidents.csv       (partidas do Sport, filtrado Serie B)

Saída:
  pending_posts/{hoje}_eficiencia-atacantes-serie-b/card.png
"""

import sys
import json
import datetime
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
SB_STATS_PATH   = BASE_DIR / "data/curated/serie_b_2026/player_match_stats.csv"
SP_STATS_PATH   = BASE_DIR / "data/curated/sport_2026/player_match_stats.csv"
SB_INC_PATH     = BASE_DIR / "data/curated/serie_b_2026/match_incidents.csv"
SP_INC_PATH     = BASE_DIR / "data/curated/sport_2026/match_incidents.csv"
SP_MATCHES_PATH = BASE_DIR / "data/curated/sport_2026/matches.csv"
LOGOS_DIR       = BASE_DIR / "data/cache/logos"
SRL_LOGO        = BASE_DIR / "sportrecifelab_avatar.png"
TODAY_STR       = datetime.date.today().isoformat()
OUT_DIR         = BASE_DIR / f"pending_posts/{TODAY_STR}_eficiencia-atacantes-serie-b"

def _sport_serie_b_codes() -> set:
    df = pd.read_csv(SP_MATCHES_PATH)
    mask = (
        df["competition_name"].str.contains("Série B|Serie B", case=False, na=False) &
        (df["status"] == "completed")
    )
    return set(df.loc[mask, "match_code"].tolist())

# ── Paleta ────────────────────────────────────────────────────────────────────
BG     = "#0d0d0d"
YELLOW = "#F5C400"
WHITE  = "#FFFFFF"
LGRAY  = "#CCCCCC"
GRAY   = "#555555"
DGRAY  = "#1e1e1e"
GREEN  = "#22C55E"
RED    = "#EF4444"

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

# ── CLI ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--min-minutes", type=int, default=90,
                    help="Minutos minimos para incluir jogador (padrao: 90)")
parser.add_argument("--min-shots", type=int, default=1,
                    help="Chutes minimos totais para incluir jogador (padrao: 1)")
parser.add_argument("--top-labels", type=int, default=12,
                    help="Numero de jogadores a rotular (top por gols, padrao: 12)")
args = parser.parse_args()

MIN_MINUTES = args.min_minutes
MIN_SHOTS   = args.min_shots
TOP_LABELS  = args.top_labels

# ── Carrega dados ─────────────────────────────────────────────────────────────
print("Carregando dados...")
sport_sb_codes = _sport_serie_b_codes()
print(f"  Sport Serie B match codes: {sorted(sport_sb_codes)}")

# Stats: serie_b (todos exceto Sport R1-R4) + sport R1-R4 (só Sport players)
sb_stats  = pd.read_csv(SB_STATS_PATH)
sp_stats  = pd.read_csv(SP_STATS_PATH)
sp_sb     = sp_stats[
    sp_stats["match_code"].isin(sport_sb_codes) &
    (sp_stats["team_key"] == "sport")
].copy()
# Garante mesmas colunas antes de concat
common_cols = [c for c in sb_stats.columns if c in sp_sb.columns]
stats_df = pd.concat([sb_stats[common_cols], sp_sb[common_cols]], ignore_index=True)
# Remove duplicatas por (player_id, match_code) — R5 aparece nas duas fontes
stats_df = stats_df.drop_duplicates(subset=["player_id", "match_code"])
print(f"  Stats: {len(sb_stats)} serie_b + {len(sp_sb)} sport R1-R4 = {len(stats_df)} (dedup)")

# Incidents: serie_b + sport (filtrado Serie B) — deduplica por incident_id
sb_inc = pd.read_csv(SB_INC_PATH)
sp_inc = pd.read_csv(SP_INC_PATH)
sp_inc_sb = sp_inc[sp_inc["match_code"].isin(sport_sb_codes)].copy()
inc_df = pd.concat([sb_inc, sp_inc_sb], ignore_index=True)
if "incident_id" in inc_df.columns:
    inc_df = inc_df.dropna(subset=["incident_id"]).drop_duplicates(subset=["incident_id"])
print(f"  Incidents: {len(sb_inc)} serie_b + {len(sp_inc_sb)} sport = {len(inc_df)} total")

# ── Gols por jogador (exclui gols contra) ────────────────────────────────────
goals_df = (
    inc_df[
        (inc_df["incident_type"] == "goal") &
        (inc_df["incident_class"].fillna("") != "ownGoal") &
        (inc_df["scorer_id"].notna())
    ]
    .groupby("scorer_id")
    .size()
    .reset_index(name="goals")
)
goals_df["scorer_id"] = goals_df["scorer_id"].astype(float)

# ── Agrega stats por jogador ──────────────────────────────────────────────────
agg = (
    stats_df.groupby("player_id")
    .agg(
        player_name=("player_name", "first"),
        team_key=("team_key", "first"),
        team_name=("team_name", "first"),
        position=("position", "first"),
        total_shots=("total_shots", "sum"),
        minutes_played=("minutes_played", "sum"),
        goal_assist=("goal_assist", "sum"),
    )
    .reset_index()
)

# ── Join com gols ─────────────────────────────────────────────────────────────
agg = agg.merge(goals_df, left_on="player_id", right_on="scorer_id", how="left")
agg["goals"] = agg["goals"].fillna(0).astype(int)

# ── Filtra: mín. minutos + pelo menos 1 gol ───────────────────────────────────
agg = agg[
    (agg["minutes_played"] >= MIN_MINUTES) &
    (agg["total_shots"] >= MIN_SHOTS) &
    (agg["goals"] >= 1)
].copy()

print(f"  {len(agg)} jogadores com >= 1 gol, >= {MIN_MINUTES} min, >= {MIN_SHOTS} chute")

# ── Métricas derivadas ────────────────────────────────────────────────────────
agg["shots_p90"]       = agg["total_shots"] / agg["minutes_played"] * 90
agg["goals_p90"]       = agg["goals"] / agg["minutes_played"] * 90
agg["conversion_rate"] = agg["goals"] / agg["total_shots"]

# ── Detecta rodada maxima ─────────────────────────────────────────────────────
max_round = int(stats_df["round"].max()) if "round" in stats_df.columns else "?"
round_label = f"R1-R{max_round}" if max_round != 1 else "R1"

# ── Output dir ────────────────────────────────────────────────────────────────
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Limites dos eixos ─────────────────────────────────────────────────────────
X_PAD = 0.25
Y_PAD = 0.04
X_MIN = max(0, agg["shots_p90"].min() - X_PAD)
X_MAX = agg["shots_p90"].max() + X_PAD * 2.5
Y_MIN = max(0, agg["goals_p90"].min() - Y_PAD)
Y_MAX = agg["goals_p90"].max() + Y_PAD * 4

X_MID = float(agg["shots_p90"].median())
Y_MID = float(agg["goals_p90"].median())

# ── Colormap: conversão RED→YELLOW→GREEN ─────────────────────────────────────
cmap  = plt.cm.RdYlGn
conv_lo  = 0.0
conv_mid = max(0.001, float(agg["conversion_rate"].median()))
conv_hi  = min(1.0, float(agg["conversion_rate"].quantile(0.95)) + 0.05)
norm  = mcolors.TwoSlopeNorm(vmin=conv_lo, vcenter=conv_mid, vmax=conv_hi)

BUBBLE_S = 85  # tamanho fixo — dimensão removida do encoding

# ── Top jogadores para labels ─────────────────────────────────────────────────
top_label_ids = set(agg.nlargest(TOP_LABELS, "goals")["player_id"].tolist())

# Outliers extremos: top 3 por goals_p90 (destacados extra)
outlier_ids = set(agg.nlargest(3, "goals_p90")["player_id"].tolist())

# ── Figura ────────────────────────────────────────────────────────────────────
FIG_W    = 10
FIG_H    = 10
HEADER_H = 0.14
FOOTER_H = 0.09
ANN_H    = 0.068   # faixa para anotação Sport abaixo do gráfico
CHART_L  = 0.09
CHART_W  = 0.81
CHART_B  = FOOTER_H + ANN_H + 0.01
CHART_H  = 1 - HEADER_H - CHART_B - 0.01

fig    = plt.figure(figsize=(FIG_W, FIG_H), facecolor=BG)
ax_hdr = fig.add_axes([0, 1 - HEADER_H, 1, HEADER_H],               facecolor=BG)
ax     = fig.add_axes([CHART_L, CHART_B, CHART_W, CHART_H],          facecolor=BG)
ax_ann = fig.add_axes([CHART_L, FOOTER_H + 0.005, CHART_W, ANN_H],   facecolor=BG)
ax_ftr = fig.add_axes([0, 0, 1, FOOTER_H],                           facecolor=BG)

for spine in ax.spines.values():
    spine.set_color("#333333")
    spine.set_linewidth(0.6)
ax.tick_params(colors="#888888", labelsize=8.5, length=3)

ax.set_xlim(X_MIN, X_MAX)
ax.set_ylim(Y_MIN, Y_MAX)

# ── Quadrantes ────────────────────────────────────────────────────────────────
ax.axvline(X_MID, color="#333333", lw=1.0, alpha=0.8, linestyle="--", zorder=1)
ax.axhline(Y_MID, color="#333333", lw=1.0, alpha=0.8, linestyle="--", zorder=1)

ax.fill_betweenx([Y_MID, Y_MAX], X_MID, X_MAX, color=GREEN, alpha=0.06, zorder=0)
ax.fill_betweenx([Y_MIN, Y_MID], X_MIN, X_MID, color=RED,   alpha=0.05, zorder=0)
ax.fill_betweenx([Y_MID, Y_MAX], X_MIN, X_MID, color=GRAY,  alpha=0.04, zorder=0)
ax.fill_betweenx([Y_MIN, Y_MID], X_MID, X_MAX, color=GRAY,  alpha=0.03, zorder=0)

ql_kw = dict(ha="center", va="top", fontsize=7.2, alpha=0.35,
             fontweight="bold", color=WHITE, style="italic",
             fontfamily="Arial")
ax.text((X_MID + X_MAX) / 2, Y_MAX - 0.006, "ELITE",       **ql_kw)
ax.text((X_MIN + X_MID) / 2, Y_MAX - 0.006, "OPORTUNISTAS", **ql_kw)
ax.text((X_MID + X_MAX) / 2, Y_MIN + 0.006, "DESPERDÍCIO",
        **{**ql_kw, "va": "bottom"})
ax.text((X_MIN + X_MID) / 2, Y_MIN + 0.006, "BAIXO VOLUME",
        **{**ql_kw, "va": "bottom"})

ax.grid(color="#2a2a2a", alpha=0.8, lw=0.4, linestyle=":")

# ── Bolhas — não-Sport ────────────────────────────────────────────────────────
is_sport_mask = agg["team_key"] == "sport"

for _, row in agg[~is_sport_mask].iterrows():
    c = cmap(norm(row["conversion_rate"]))
    is_out = row["player_id"] in outlier_ids
    ax.scatter(
        row["shots_p90"], row["goals_p90"],
        s=BUBBLE_S * (1.25 if is_out else 1.0),
        color=c, alpha=0.82, edgecolors="white" if is_out else "none",
        linewidths=0.7 if is_out else 0,
        zorder=4 if is_out else 3,
    )

# ── Bolhas — Sport (anel dourado + brilho) ────────────────────────────────────
for _, row in agg[is_sport_mask].iterrows():
    c = cmap(norm(row["conversion_rate"]))
    ax.scatter(row["shots_p90"], row["goals_p90"],
               s=BUBBLE_S * 2.6, color=YELLOW, alpha=0.09,
               edgecolors="none", zorder=5)
    ax.scatter(row["shots_p90"], row["goals_p90"],
               s=BUBBLE_S * 1.65, color="none", edgecolors=YELLOW,
               linewidths=1.6, alpha=1.0, zorder=6)
    ax.scatter(row["shots_p90"], row["goals_p90"],
               s=BUBBLE_S, color=c, alpha=0.95,
               edgecolors="none", zorder=7)

# ── Labels ────────────────────────────────────────────────────────────────────
label_rows = agg[agg["player_id"].isin(top_label_ids)].copy()

_texts = []
_pts_x = list(agg["shots_p90"])
_pts_y = list(agg["goals_p90"])

for _, row in label_rows.iterrows():
    name_parts = str(row["player_name"]).split()
    short_name = name_parts[-1] if len(name_parts) > 1 else name_parts[0]
    team_abbr  = str(row["team_key"]).split("-")[0].upper()[:3]
    is_sport   = row["team_key"] == "sport"
    is_outlier = row["player_id"] in outlier_ids
    label      = f"{short_name}  {team_abbr}"
    col        = YELLOW if is_sport else ("#FFFFFF" if is_outlier else LGRAY)
    fs         = 8.0 if is_sport else (7.6 if is_outlier else 7.2)
    fw         = "bold" if (is_sport or is_outlier) else "normal"

    # Offset inicial: afasta do centro do chart
    ox = 10 if row["shots_p90"] >= X_MID else -10
    oy =  8 if row["goals_p90"] >= Y_MID else  -8

    t = ax.text(
        row["shots_p90"] + ox * (X_MAX - X_MIN) / 800,
        row["goals_p90"] + oy * (Y_MAX - Y_MIN) / 800,
        label,
        fontsize=fs, color=col, fontweight=fw,
        fontfamily="Arial",
        ha="left" if ox > 0 else "right",
        va="bottom" if oy > 0 else "top",
        zorder=10,
    )
    _texts.append(t)

# Ajuste anti-sobreposição
try:
    from adjustText import adjust_text
    adjust_text(
        _texts,
        x=_pts_x, y=_pts_y,
        ax=ax,
        expand_points=(1.5, 1.8),
        expand_text=(1.2, 1.3),
        force_points=(0.25, 0.3),
        force_text=(0.12, 0.15),
        only_move={"text": "xy", "points": "xy"},
        arrowprops=dict(arrowstyle="-", color="#444444", lw=0.35, alpha=0.6),
        lim=500,
    )
except ImportError:
    pass

# ── Eixos ─────────────────────────────────────────────────────────────────────
ax.set_xlabel("Chutes por 90 min", color=LGRAY, fontsize=9, labelpad=7,
              fontfamily="Arial")
ax.set_ylabel("Gols por 90 min",   color=LGRAY, fontsize=9, labelpad=7,
              fontfamily="Arial")

# ── Anotação Sport — faixa inferior (fora do gráfico) ─────────────────────────
ax_ann.axis("off")
sport_rows = agg[is_sport_mask].sort_values("goals_p90", ascending=False)
if not sport_rows.empty:
    parts = []
    for _, r in sport_rows.iterrows():
        nm   = str(r["player_name"]).split()[-1]
        conv = r["conversion_rate"] * 100
        sp90 = r["shots_p90"]
        parts.append(f"{nm}: {r['goals']}G · {sp90:.1f} chutes/90 · conv. {conv:.0f}%")
    summary = "  ·  ".join(parts)
    ax_ann.text(
        0.0, 0.75,
        "▶  Sport Recife — alto volume de chutes, conversão abaixo da elite",
        ha="left", va="top", transform=ax_ann.transAxes,
        color=YELLOW, fontsize=7.8, fontweight="bold", fontfamily="Arial",
    )
    ax_ann.text(
        0.0, 0.28,
        summary,
        ha="left", va="top", transform=ax_ann.transAxes,
        color="#999999", fontsize=7.0, fontfamily="Arial",
    )
    ax_ann.axhline(1.0, color="#2a2a2a", lw=0.6, xmin=0, xmax=1)

# ── Colorbar personalizada: Baixa / Média / Alta ──────────────────────────────
cb_l = CHART_L + CHART_W + 0.025
cb_b = CHART_B + 0.08
cb_w = 0.018
cb_h = CHART_H - 0.12
cbar_ax = fig.add_axes([cb_l, cb_b, cb_w, cb_h])
gradient = np.linspace(1, 0, 256).reshape(256, 1)
cbar_ax.imshow(gradient, aspect="auto", cmap=cmap, extent=[0, 1, 0, 1])
cbar_ax.set_xlim(0, 1)
cbar_ax.set_ylim(0, 1)
cbar_ax.axis("off")
# Borda sutil
for sp in ["top", "bottom", "left", "right"]:
    cbar_ax.spines[sp].set_visible(False)

# Labels da colorbar
tx = cb_l + cb_w + 0.006
fig.text(tx, cb_b + cb_h, "Alta",  ha="left", va="top",
         color=GREEN, fontsize=7.5, fontweight="bold")
fig.text(tx, cb_b + cb_h * 0.5, "Média", ha="left", va="center",
         color="#E8D44D", fontsize=7.5)
fig.text(tx, cb_b, "Baixa", ha="left", va="bottom",
         color=RED, fontsize=7.5)
fig.text(cb_l + cb_w / 2, cb_b + cb_h + 0.012, "Conv.",
         ha="center", va="bottom", color="#666666", fontsize=6.5)

# ── Header ────────────────────────────────────────────────────────────────────
ax_hdr.axis("off")
ax_hdr.text(
    0.5, 0.92,
    "Quem realmente finaliza bem na Série B?",
    ha="center", va="top", transform=ax_hdr.transAxes,
    color=YELLOW, fontsize=14.5, fontweight="bold",
    fontfamily="Franklin Gothic Heavy",
)
ax_hdr.text(
    0.5, 0.54,
    "Chutes/90 x Gols/90  •  Cor: taxa de conversão",
    ha="center", va="top", transform=ax_hdr.transAxes,
    color=LGRAY, fontsize=8.2, fontfamily="Arial",
)
ax_hdr.text(
    0.5, 0.20,
    f"Brasileirão Série B 2026  ·  {round_label}  ·  apenas jogadores com ≥ 1 gol",
    ha="center", va="top", transform=ax_hdr.transAxes,
    color="#666666", fontsize=7.5, fontfamily="Arial",
)
ax_hdr.axhline(0.06, color=YELLOW, lw=1.2, xmin=0.04, xmax=0.96, alpha=0.7)

# ── Footer ────────────────────────────────────────────────────────────────────
ax_ftr.axis("off")
try:
    srl_arr  = np.array(Image.open(SRL_LOGO).convert("RGBA"))
    srl_size = 0.055
    ax_srl   = fig.add_axes([0.030, 0.015, srl_size, srl_size])
    ax_srl.imshow(srl_arr)
    ax_srl.axis("off")
except Exception:
    pass
fig.text(0.103, 0.047, "@SportRecifeLab",
         ha="left", va="center", color=LGRAY, fontsize=8.5,
         fontweight="bold", fontfamily="Arial")
fig.text(0.103, 0.026, "Dados: SofaScore",
         ha="left", va="center", color="#555555", fontsize=7.2,
         fontfamily="Arial")

# Legenda anel dourado
fig.text(0.97, 0.047, "○  Sport Recife",
         ha="right", va="center", color=YELLOW,
         fontsize=7.5, fontfamily="Arial")

# ── Salva ─────────────────────────────────────────────────────────────────────
card_path = OUT_DIR / "card.png"
fig.savefig(card_path, dpi=108, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"Card: {card_path}")

# ── Estatísticas de resumo ────────────────────────────────────────────────────
top_scorers = agg.nlargest(5, "goals")[["player_name", "team_name", "goals",
                                         "total_shots", "conversion_rate",
                                         "shots_p90", "goals_p90"]]
print("\nTop 5 artilheiros:")
print(top_scorers.to_string(index=False))

top_conv = (
    agg[agg["goals"] >= 2]
    .nlargest(5, "conversion_rate")[["player_name", "team_name", "goals",
                                      "total_shots", "conversion_rate"]]
)
print("\nTop 5 conversão (mín. 2 gols):")
print(top_conv.to_string(index=False))

sport_players = agg[agg["team_key"] == "sport"].sort_values("goals", ascending=False)
if not sport_players.empty:
    print("\nJogadores do Sport:")
    print(sport_players[["player_name", "goals", "total_shots",
                          "minutes_played", "conversion_rate",
                          "shots_p90", "goals_p90"]].to_string(index=False))

# ── Metadata ──────────────────────────────────────────────────────────────────
metadata = {
    "type": "eficiencia-ofensiva",
    "competition": "serie_b_2026",
    "round_label": round_label,
    "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
    "filters": {
        "min_minutes": MIN_MINUTES,
        "min_shots": MIN_SHOTS,
    },
    "players_plotted": len(agg),
    "top_scorer": (
        agg.nlargest(1, "goals")[["player_name", "team_name", "goals"]]
        .to_dict("records")[0]
        if len(agg) > 0 else {}
    ),
}
(OUT_DIR / "metadata.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(f"\nMetadata: {OUT_DIR / 'metadata.json'}")
print(f"\nSaída completa: {OUT_DIR}")
