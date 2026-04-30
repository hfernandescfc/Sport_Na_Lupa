"""
Análise ofensiva da Série B 2026
=================================
Compara o xG produzido por cada clube contra o xG médio que o adversário
concedia até aquele momento na competição (força defensiva contextualizada).

Métricas por clube:
  xG_total   — soma do xG produzido em todas as partidas
  xG_ctx     — soma do xG esperado dado o contexto defensivo do adversário
  delta      — xG_total - xG_ctx  (>0 = superou o contexto, <0 = abaixo)
  delta_pct  — delta relativo ao contexto (%)
"""

import pandas as pd
import numpy as np
from pathlib import Path

BASE_DIR   = Path(__file__).parent
MATCHES    = BASE_DIR / "data/curated/serie_b_2026/matches.csv"
STATS      = BASE_DIR / "data/curated/serie_b_2026/team_match_stats.csv"

# ── Carrega dados ──────────────────────────────────────────────────────────────
matches = pd.read_csv(MATCHES)
stats   = pd.read_csv(STATS)

# Só partidas completas
matches = matches[matches["status"] == "completed"].copy()
stats   = stats[stats["match_code"].isin(matches["match_code"])].copy()

# Adiciona rodada ao stats
round_map = matches.set_index("match_code")["round"].to_dict()
stats["round"] = stats["match_code"].map(round_map)

# ── Para cada partida: identifica quem concedeu xG a quem ─────────────────────
# Monta par (atacante, defensor) por partida
rows = []
for match_code, grp in stats.groupby("match_code"):
    if len(grp) != 2:
        continue
    teams = grp[["team_key", "team_name", "expected_goals", "round"]].to_dict("records")
    t0, t1 = teams[0], teams[1]
    # t0 ataca t1, t1 ataca t0
    rows.append({
        "round":          t0["round"],
        "match_code":     match_code,
        "attacker_key":   t0["team_key"],
        "attacker_name":  t0["team_name"],
        "defender_key":   t1["team_key"],
        "xg_produced":    t0["expected_goals"],
    })
    rows.append({
        "round":          t1["round"],
        "match_code":     match_code,
        "attacker_key":   t1["team_key"],
        "attacker_name":  t1["team_name"],
        "defender_key":   t0["team_key"],
        "xg_produced":    t1["expected_goals"],
    })

duels = pd.DataFrame(rows).sort_values(["round", "match_code"]).reset_index(drop=True)

# ── Calcula xG médio concedido por cada time ATÉ aquela rodada (exclusive) ────
def avg_xg_conceded_before(defender_key: str, before_round: int, duels_df: pd.DataFrame) -> float:
    """Média de xG concedido pelo defensor em rodadas anteriores à `before_round`."""
    prior = duels_df[
        (duels_df["defender_key"] == defender_key) &
        (duels_df["round"] < before_round)
    ]
    if prior.empty:
        return np.nan
    return prior["xg_produced"].mean()

duels["xg_ctx"] = duels.apply(
    lambda r: avg_xg_conceded_before(r["defender_key"], r["round"], duels),
    axis=1,
)

# ── Agrega por clube ───────────────────────────────────────────────────────────
# Para o agregado, rodadas sem contexto (R1) usam a média geral da competição
# como proxy — marcamos separado para transparência
league_avg_xg_conceded = duels["xg_produced"].mean()  # proxy para R1

duels["xg_ctx_filled"] = duels["xg_ctx"].fillna(league_avg_xg_conceded)
duels["ctx_is_estimated"] = duels["xg_ctx"].isna()

agg = (
    duels.groupby(["attacker_key", "attacker_name"])
    .agg(
        MP          = ("round", "count"),
        xG_total    = ("xg_produced",    "sum"),
        xG_ctx      = ("xg_ctx_filled",  "sum"),
        R1_estimated= ("ctx_is_estimated","sum"),
    )
    .reset_index()
    .rename(columns={"attacker_name": "team"})
)

agg["delta"]     = agg["xG_total"] - agg["xG_ctx"]
agg["delta_pct"] = (agg["delta"] / agg["xG_ctx"] * 100).round(1)
agg["xG_total"]  = agg["xG_total"].round(2)
agg["xG_ctx"]    = agg["xG_ctx"].round(2)
agg["delta"]     = agg["delta"].round(2)

agg = agg.sort_values("delta", ascending=False).reset_index(drop=True)
agg.index += 1

# ── Exibe resultados ───────────────────────────────────────────────────────────
RODADAS = sorted(duels["round"].unique())
print(f"\n{'='*72}")
print(f"  SÉRIE B 2026 — Produção ofensiva vs contexto defensivo")
print(f"  Rodadas analisadas: {RODADAS}  |  Proxy R1 = média da liga ({league_avg_xg_conceded:.2f} xG)")
print(f"{'='*72}")
print(f"{'#':>2}  {'Time':<22} {'MP':>3} {'xG prod':>8} {'xG ctx':>8} {'Delta':>7} {'Delta%':>8}")
print(f"{'-'*72}")

for i, row in agg.iterrows():
    flag = "*" if row["R1_estimated"] > 0 else " "
    delta_str = f"{row['delta']:+.2f}"
    print(
        f"{i:>2}  {row['team']:<22} {row['MP']:>3} "
        f"{row['xG_total']:>8.2f} {row['xG_ctx']:>8.2f} "
        f"{delta_str:>7} {row['delta_pct']:>6.1f}%{flag}"
    )

print(f"{'-'*72}")
print("  * R1 sem historico do adversario - usa media da liga como proxy\n")

# ── Por rodada: detalhe partida a partida ─────────────────────────────────────
duels["delta"] = duels["xg_produced"] - duels["xg_ctx_filled"]

print(f"\n{'='*72}")
print(f"  DETALHE POR PARTIDA")
print(f"{'='*72}")

for rnd in RODADAS:
    print(f"\n  Rodada {rnd}")
    print(f"  {'Time':<22} {'xG prod':>8} {'xG ctx adv':>11} {'Delta':>7}")
    print(f"  {'-'*54}")
    rnd_df = duels[duels["round"] == rnd].sort_values("delta", ascending=False)
    for _, r in rnd_df.iterrows():
        ctx_str   = f"{r['xg_ctx']:.2f}" if not np.isnan(r["xg_ctx"]) else "  n/a"
        delta_str = f"{r['delta']:+.2f}"  if not np.isnan(r["xg_ctx"]) else "  n/a"
        print(f"  {r['attacker_name']:<22} {r['xg_produced']:>8.2f} {ctx_str:>11} {delta_str:>7}")
