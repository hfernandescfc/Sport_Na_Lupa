"""
Card: Producao ofensiva vs contexto defensivo - Serie B 2026
Dumbbell chart com escudos dos times, Sport Recife em destaque.

Saida: pending_posts/2026-04-16_ofensiva-serie-b/card.png
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
from PIL import Image

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
MATCHES   = BASE_DIR / "data/curated/serie_b_2026/matches.csv"
STATS     = BASE_DIR / "data/curated/serie_b_2026/team_match_stats.csv"
LOGOS_DIR = BASE_DIR / "data/cache/logos"
OUT_DIR   = BASE_DIR / "pending_posts/2026-04-16_ofensiva-serie-b"
OUT_DIR.mkdir(parents=True, exist_ok=True)

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

BG       = "#0d0d0d"
YELLOW   = "#F5C400"
WHITE    = "#FFFFFF"
LGRAY    = "#CCCCCC"
GRAY     = "#555555"
DGRAY    = "#2a2a2a"
GREEN    = "#22C55E"
RED      = "#EF4444"
SRL_LOGO = BASE_DIR / "sportrecifelab_avatar.png"

# ── Calcula dados ─────────────────────────────────────────────────────────────
matches = pd.read_csv(MATCHES)
stats   = pd.read_csv(STATS)
matches = matches[matches["status"] == "completed"].copy()
stats   = stats[stats["match_code"].isin(matches["match_code"])].copy()
round_map = matches.set_index("match_code")["round"].to_dict()
stats["round"] = stats["match_code"].map(round_map)

rows = []
for match_code, grp in stats.groupby("match_code"):
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

def avg_xg_conceded_before(defender_key, before_round, df):
    prior = df[(df["defender_key"] == defender_key) & (df["round"] < before_round)]
    return prior["xg_produced"].mean() if not prior.empty else np.nan

duels["xg_ctx"] = duels.apply(
    lambda r: avg_xg_conceded_before(r["defender_key"], r["round"], duels), axis=1
)
league_avg = duels["xg_produced"].mean()
duels["xg_ctx_filled"] = duels["xg_ctx"].fillna(league_avg)

agg = (
    duels.groupby(["attacker_key", "attacker_name"])
    .agg(xG_total=("xg_produced", "sum"), xG_ctx=("xg_ctx_filled", "sum"))
    .reset_index()
    .rename(columns={"attacker_name": "team"})
)
agg["delta"] = agg["xG_total"] - agg["xG_ctx"]
agg = agg.sort_values("delta").reset_index(drop=True)  # crescente = bottom→top

# ── Layout ────────────────────────────────────────────────────────────────────
N        = len(agg)
FIG_W    = 10
FIG_H    = 14
HEADER_H = 0.13   # fracao da figura
FOOTER_H = 0.10
CHART_H  = 1 - HEADER_H - FOOTER_H   # 0.77
CHART_L  = 0.26   # margem esquerda do eixo do grafico
CHART_W  = 0.70   # largura do eixo

fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor=BG)

ax_hdr = fig.add_axes([0, 1 - HEADER_H, 1, HEADER_H], facecolor=BG)
ax     = fig.add_axes([CHART_L, FOOTER_H, CHART_W, CHART_H], facecolor=BG)
ax_ftr = fig.add_axes([0, 0, 1, FOOTER_H], facecolor=BG)

for spine in ax.spines.values():
    spine.set_visible(False)
ax.tick_params(colors=LGRAY, labelsize=8.5)
ax.xaxis.set_tick_params(color=GRAY)
ax.yaxis.set_visible(False)

# ── Limites dos dados ─────────────────────────────────────────────────────────
Y_MIN  = -0.55
Y_MAX  = N - 0.45     # 19.55
X_MIN  = max(0, agg[["xG_total", "xG_ctx"]].min().min() - 0.8)
X_MAX  = agg[["xG_total", "xG_ctx"]].max().max() + 1.0

ax.set_xlim(X_MIN, X_MAX)
ax.set_ylim(Y_MIN, Y_MAX)

def data_y_to_fig(y_data):
    """Converte coordenada y de dados para fracao da figura."""
    t = (y_data - Y_MIN) / (Y_MAX - Y_MIN)
    return FOOTER_H + CHART_H * t

# ── Dumbbell ──────────────────────────────────────────────────────────────────
LOGO_SIZE_FIG = 0.040   # largura/altura do escudo em fracao da figura

for i, row in agg.iterrows():
    y        = float(i)
    xg_prod  = row["xG_total"]
    xg_ctx   = row["xG_ctx"]
    is_sport = row["attacker_key"] == "sport"
    over     = xg_prod >= xg_ctx

    line_col = GREEN if over else RED
    alpha    = 1.0 if is_sport else 0.75

    # faixa alternada
    if i % 2 == 0:
        ax.axhspan(y - 0.45, y + 0.45, color=DGRAY, alpha=0.22, zorder=0)

    # linha conectora
    ax.plot([xg_ctx, xg_prod], [y, y],
            color=line_col, lw=2.8 if is_sport else 1.8,
            alpha=alpha, zorder=2, solid_capstyle="round")

    # dot contexto (cinza)
    ax.scatter(xg_ctx, y, color="#888888", s=65, zorder=3, alpha=alpha)

    # dot producao
    dot_col = YELLOW if is_sport else (GREEN if over else RED)
    ax.scatter(xg_prod, y, color=dot_col, s=120 if is_sport else 80,
               zorder=4, alpha=alpha)

    # label delta
    dx        = xg_prod - xg_ctx
    label_x   = max(xg_prod, xg_ctx) + 0.10
    label_col = YELLOW if is_sport else (GREEN if over else RED)
    ax.text(label_x, y, f"{'+'if dx>=0 else ''}{dx:.1f}",
            va="center", ha="left",
            color=label_col, fontsize=8 if is_sport else 7.5,
            fontweight="bold" if is_sport else "normal",
            alpha=alpha)

    # ── Escudo (fig.add_axes) ──────────────────────────────────────────────────
    logo_id   = TEAM_LOGO_ID.get(row["attacker_key"])
    logo_path = LOGOS_DIR / f"{logo_id}.png" if logo_id else None
    y_fig_center = data_y_to_fig(y)
    logo_s = LOGO_SIZE_FIG * 1.25 if is_sport else LOGO_SIZE_FIG
    logo_ax_rect = [
        CHART_L - logo_s - 0.005,          # x: logo fica logo antes do eixo
        y_fig_center - logo_s / 2,
        logo_s,
        logo_s,
    ]
    if logo_path and logo_path.exists():
        try:
            img_arr = np.array(Image.open(logo_path).convert("RGBA"))
            ax_logo = fig.add_axes(logo_ax_rect, facecolor="none")
            ax_logo.imshow(img_arr)
            ax_logo.axis("off")
            ax_logo.set_zorder(10)
        except Exception as e:
            print(f"  logo erro {row['attacker_key']}: {e}")

    # ── Nome do time ───────────────────────────────────────────────────────────
    name_x   = CHART_L - logo_s - 0.012   # imediatamente a esq. do escudo
    name_col = YELLOW if is_sport else LGRAY
    name_fw  = "bold" if is_sport else "normal"
    fig.text(name_x, y_fig_center,
             row["team"], ha="right", va="center",
             color=name_col, fontsize=8.2 if is_sport else 7.8,
             fontweight=name_fw, figure=fig)

# ── Eixo X ────────────────────────────────────────────────────────────────────
ax.set_xticks(np.arange(int(X_MIN) + 1, int(X_MAX) + 1, 1))
ax.grid(axis="x", color=GRAY, alpha=0.2, lw=0.6, linestyle="--")
ax.set_xlabel("xG acumulado (Rodadas 1-4)", color=LGRAY, fontsize=8, labelpad=6)

# ── Legenda ───────────────────────────────────────────────────────────────────
# Linha 1: xG produzido
LEG_Y1 = FOOTER_H - 0.028   # logo abaixo do eixo X
LEG_Y2 = FOOTER_H - 0.050
fig.text(CHART_L + 0.018, LEG_Y1, "xG produzido",
         ha="left", va="center", color=LGRAY, fontsize=7.5, figure=fig)
fig.text(CHART_L, LEG_Y1, "●",
         ha="left", va="center", color=GREEN, fontsize=10, figure=fig)

# Linha 2: xG contexto
fig.text(CHART_L + 0.018, LEG_Y2,
         "xG esperado  (media de xG concedido pelo adversario ate aquela rodada)",
         ha="left", va="center", color=LGRAY, fontsize=7.5, figure=fig)
fig.text(CHART_L, LEG_Y2, "●",
         ha="left", va="center", color="#888888", fontsize=10, figure=fig)

# ── Header ────────────────────────────────────────────────────────────────────
ax_hdr.axis("off")
ax_hdr.text(0.5, 0.85,
            "PRODUCAO OFENSIVA vs CONTEXTO DEFENSIVO",
            ha="center", va="top", transform=ax_hdr.transAxes,
            color=WHITE, fontsize=13.5, fontweight="bold",
            fontfamily="Franklin Gothic Heavy")
ax_hdr.text(0.5, 0.50,
            "xG produzido  x  media de xG concedido pelo adversario ate aquela rodada",
            ha="center", va="top", transform=ax_hdr.transAxes,
            color=LGRAY, fontsize=8.5)
ax_hdr.text(0.5, 0.18,
            "Serie B 2026  -  Rodadas 1-4",
            ha="center", va="top", transform=ax_hdr.transAxes,
            color=GRAY, fontsize=8)
ax_hdr.axhline(0.08, color=YELLOW, lw=1.5, xmin=0.04, xmax=0.96)

# ── Footer ────────────────────────────────────────────────────────────────────
ax_ftr.axis("off")

# SRL avatar (bottom-left, padrao do projeto)
try:
    srl_arr = np.array(Image.open(SRL_LOGO).convert("RGBA"))
    srl_size = 0.058
    ax_srl = fig.add_axes([0.030, 0.014, srl_size, srl_size * FIG_W / FIG_H])
    ax_srl.imshow(srl_arr)
    ax_srl.axis("off")
except Exception:
    pass

# Texto de credito ao lado do logo
fig.text(0.105, 0.044, "@SportRecifeLab",
         ha="left", va="center", color=LGRAY, fontsize=8,
         fontweight="bold", figure=fig)
fig.text(0.105, 0.026, "Dados: SofaScore",
         ha="left", va="center", color=GRAY, fontsize=7, figure=fig)

# ── Salva ─────────────────────────────────────────────────────────────────────
out_path = OUT_DIR / "card.png"
fig.savefig(out_path, dpi=160, bbox_inches="tight", facecolor=BG)
plt.close(fig)
print(f"Salvo: {out_path}")
