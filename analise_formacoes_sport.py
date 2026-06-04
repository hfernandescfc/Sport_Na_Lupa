"""
Análise de Lineups — Sport Recife, Série B 2026

Identifica o "Melhor" e o "Pior" Sport da temporada cruzando as métricas
(xG, xGA, posse) com os jogadores que estavam em campo em cada fase de jogo.

Substituições dividem cada partida em fases; os stats de partida são
distribuídos proporcionalmente ao tempo de cada fase.

Uso:
    python -X utf8 analise_formacoes_sport.py
    python -X utf8 analise_formacoes_sport.py --min-minutes 90
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

MATCHES_PATH   = BASE_DIR / "data/curated/sport_2026/matches.csv"
PLAYERS_PATH   = BASE_DIR / "data/curated/sport_2026/player_match_stats.csv"
INCIDENTS_PATH = BASE_DIR / "data/curated/sport_2026/match_incidents.csv"
STATS_SB_PATH  = BASE_DIR / "data/curated/serie_b_2026/team_match_stats.csv"

COMPETITION_FILTER = "Brasileirão Série B"
MATCH_DURATION     = 90  # minutos base para normalização
WEIGHTS = {"xg": 0.40, "xga": 0.40, "poss": 0.20}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(series: pd.Series) -> pd.Series:
    """Min-max normalização. Retorna 0.5 uniforme se todos valores iguais."""
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - lo) / (hi - lo)


def _fmt_lineup(player_ids: frozenset, id_to_name: dict) -> str:
    names = sorted(id_to_name.get(pid, f"#{pid}") for pid in player_ids)
    return ", ".join(names)


def _short_lineup(player_ids: frozenset, base_ids: frozenset, id_to_name: dict) -> str:
    """Descreve o lineup como diferenças em relação ao XI titular base."""
    if player_ids == base_ids:
        return "XI Inicial (sem subs)"
    entrou  = player_ids - base_ids
    saiu    = base_ids - player_ids
    entrou_names = sorted(id_to_name.get(p, f"#{p}") for p in entrou)
    saiu_names   = sorted(id_to_name.get(p, f"#{p}") for p in saiu)
    parts = []
    if saiu:
        parts.append("–" + ", ".join(saiu_names))
    if entrou:
        parts.append("+" + ", ".join(entrou_names))
    return "  ".join(parts) if parts else "XI Inicial"


# ── Fase de lineup de uma partida ─────────────────────────────────────────────

def build_lineup_phases(
    match_code: str,
    sport_is_home: bool,
    starters_df: pd.DataFrame,
    subs_df: pd.DataFrame,
) -> list[dict]:
    """
    Retorna lista de fases, cada uma com:
        lineup  frozenset[player_id]
        t_start int (minuto início)
        t_end   int (minuto fim)
    """
    # Lineup inicial
    starters = starters_df[
        (starters_df["match_code"] == match_code) &
        (starters_df["is_substitute"].astype(str).str.lower().isin(["false", "0"]))
    ]
    if starters.empty:
        return []

    current = set(starters["player_id"].dropna().astype(int).tolist())

    # Substituições do Sport nessa partida, ordenadas por minuto
    match_subs = subs_df[
        (subs_df["match_code"] == match_code) &
        (subs_df["incident_type"] == "substitution") &
        (subs_df["is_home"].astype(str).str.lower() == str(sport_is_home).lower())
    ].copy()
    match_subs["time"] = pd.to_numeric(match_subs["time"], errors="coerce").fillna(90)
    match_subs = match_subs.sort_values("time")

    phases = []
    t = 0
    for _, sub in match_subs.iterrows():
        t_sub = int(min(sub["time"], MATCH_DURATION))
        if t_sub > t:
            phases.append({"lineup": frozenset(current), "t_start": t, "t_end": t_sub})
        # Aplicar substituição
        out_id = sub["player_out_id"]
        in_id  = sub["player_in_id"]
        if pd.notna(out_id):
            current.discard(int(out_id))
        if pd.notna(in_id):
            current.add(int(in_id))
        t = t_sub

    # Fase final
    if t < MATCH_DURATION:
        phases.append({"lineup": frozenset(current), "t_start": t, "t_end": MATCH_DURATION})

    return phases


# ── Main ──────────────────────────────────────────────────────────────────────

def main(min_minutes: int = 45, player_name: str | None = None) -> None:
    # 1. Carregar dados
    matches   = pd.read_csv(MATCHES_PATH)
    players   = pd.read_csv(PLAYERS_PATH)
    incidents = pd.read_csv(INCIDENTS_PATH)
    stats_sb  = pd.read_csv(STATS_SB_PATH)

    # 2. Filtrar partidas da Série B do Sport (completas)
    sb_matches = matches[
        (matches["competition_name"] == COMPETITION_FILTER) &
        (matches["is_completed"].astype(str).str.lower().isin(["true", "1"]))
    ].drop_duplicates("match_code").copy()

    if sb_matches.empty:
        print("⚠  Nenhuma partida da Série B encontrada.")
        return

    # Avisar sobre partidas sem player stats
    all_sb = matches[matches["competition_name"] == COMPETITION_FILTER].drop_duplicates("match_code")
    sb_player_rows = players[players["match_code"].isin(sb_matches["match_code"])]
    missing = set(all_sb[all_sb["is_completed"].astype(str).str.lower().isin(["true","1"])]["match_code"]) - set(sb_player_rows["match_code"])

    n_total = len(all_sb[all_sb["is_completed"].astype(str).str.lower().isin(["true","1"])])
    print(f"Partidas da Série B analisadas: {len(sb_matches)} / {n_total} completas  (mínimo: {min_minutes} min)")
    if missing:
        miss_labels = all_sb[all_sb["match_code"].isin(missing)]["match_label"].tolist()
        print(f"⚠  Sem player stats: {', '.join(miss_labels)} — rode: python -m src.main sync-player-stats --season 2026")
    print()

    # 3. Obter xG do Sport e xGA (= xG do adversário) por partida
    sport_stats = stats_sb[stats_sb["team_key"] == "sport"][
        ["match_code", "expected_goals", "possession"]
    ].rename(columns={"expected_goals": "xg_sport", "possession": "poss_sport"})
    sport_stats["xg_sport"] = pd.to_numeric(sport_stats["xg_sport"], errors="coerce")
    sport_stats["poss_sport"] = pd.to_numeric(sport_stats["poss_sport"], errors="coerce")

    opp_stats = stats_sb[stats_sb["team_key"] != "sport"][
        ["match_code", "expected_goals"]
    ].rename(columns={"expected_goals": "xga_sport"})
    opp_stats["xga_sport"] = pd.to_numeric(opp_stats["xga_sport"], errors="coerce")

    match_metrics = sport_stats.merge(opp_stats, on="match_code", how="inner")

    # 4. Mapa player_id → nome (de todas as partidas Série B do Sport — já calculado acima)
    id_to_name: dict[int, str] = {}
    for _, row in sb_player_rows.iterrows():
        pid = row["player_id"]
        if pd.notna(pid):
            id_to_name[int(pid)] = row["player_name"]

    # 5. Construir fases de lineup e acumular stats
    lineup_accum: dict[frozenset, dict] = defaultdict(lambda: {
        "total_xg": 0.0, "total_xga": 0.0, "poss_wsum": 0.0, "total_mins": 0
    })

    # Determinar o XI base (mais frequente como starters)
    starter_counts: dict[int, int] = defaultdict(int)

    for _, match in sb_matches.iterrows():
        mc        = match["match_code"]
        is_home   = str(match.get("home_team_key", "")).lower() == "sport"

        row_m = match_metrics[match_metrics["match_code"] == mc]
        if row_m.empty:
            continue
        xg_total   = float(row_m["xg_sport"].iloc[0])
        xga_total  = float(row_m["xga_sport"].iloc[0])
        poss_total = float(row_m["poss_sport"].iloc[0])

        phases = build_lineup_phases(mc, is_home, sb_player_rows, incidents)
        if not phases:
            continue

        # Contar starters para determinar XI base
        first_lineup = phases[0]["lineup"] if phases else frozenset()
        for pid in first_lineup:
            starter_counts[pid] += 1

        total_phase_mins = sum(p["t_end"] - p["t_start"] for p in phases)
        if total_phase_mins == 0:
            continue

        for phase in phases:
            duration = phase["t_end"] - phase["t_start"]
            frac     = duration / total_phase_mins
            key      = phase["lineup"]

            lineup_accum[key]["total_xg"]   += xg_total  * frac
            lineup_accum[key]["total_xga"]  += xga_total * frac
            lineup_accum[key]["poss_wsum"]  += poss_total * duration
            lineup_accum[key]["total_mins"] += duration

    if not lineup_accum:
        print("⚠  Não foi possível construir fases de lineup.")
        return

    # XI base = jogadores que aparecem como starters em >= metade das partidas
    n_matches   = len(sb_matches)
    base_ids    = frozenset(
        pid for pid, cnt in starter_counts.items()
        if cnt >= max(1, n_matches // 2)
    )

    # 6. Montar tabela de resultados
    rows = []
    for lineup_key, acc in lineup_accum.items():
        mins = acc["total_mins"]
        if mins == 0:
            continue
        xg_per90  = acc["total_xg"]  / mins * MATCH_DURATION
        xga_per90 = acc["total_xga"] / mins * MATCH_DURATION
        poss_avg  = acc["poss_wsum"] / mins
        rows.append({
            "lineup_key":  lineup_key,
            "total_mins":  mins,
            "xg_per90":    round(xg_per90,  2),
            "xga_per90":   round(xga_per90, 2),
            "poss_avg":    round(poss_avg,  1),
            "valid":       mins >= min_minutes,
        })

    df = pd.DataFrame(rows)
    valid_df = df[df["valid"]].copy()

    if valid_df.empty:
        print(f"⚠  Nenhum lineup com >= {min_minutes} minutos. Ajuste --min-minutes.")
        return

    # 7. Score composto (normalização min-max, xGA invertido)
    valid_df["score"] = (
        WEIGHTS["xg"]   * _norm(valid_df["xg_per90"])
        + WEIGHTS["xga"] * (1 - _norm(valid_df["xga_per90"]))
        + WEIGHTS["poss"] * _norm(valid_df["poss_avg"])
    )
    valid_df = valid_df.sort_values("score", ascending=False).reset_index(drop=True)

    # 8. Exibir tabela
    sep = "─" * 82
    print("ANÁLISE DE LINEUPS — SPORT RECIFE  SÉRIE B 2026")
    print(sep)
    print(f"{'#':<3}  {'Lineup (diff. do XI inicial)':<34}  {'Mins':>4}  {'xG/90':>5}  {'xGA/90':>6}  {'Poss%':>5}  {'Score':>5}")
    print(sep)

    best_key = worst_key = None
    for i, row in valid_df.iterrows():
        rank       = i + 1
        label      = _short_lineup(row["lineup_key"], base_ids, id_to_name)
        mins_str   = f"{int(row['total_mins'])}"
        tag        = ""
        if rank == 1:
            tag = "  ✅ MELHOR"
            best_key = row["lineup_key"]
        elif rank == len(valid_df):
            tag = "  ❌ PIOR"
            worst_key = row["lineup_key"]
        print(
            f"{rank:<3}  {label:<34}  {mins_str:>4}  "
            f"{row['xg_per90']:>5.2f}  {row['xga_per90']:>6.2f}  "
            f"{row['poss_avg']:>4.1f}%  {row['score']:>5.2f}{tag}"
        )

    # Lineups inválidos
    invalid_df = df[~df["valid"]]
    if not invalid_df.empty:
        print()
        print(f"⚠  Abaixo do mínimo ({min_minutes} min) — excluídos do ranking:")
        for _, row in invalid_df.iterrows():
            label = _short_lineup(row["lineup_key"], base_ids, id_to_name)
            print(f"     {label}  [{int(row['total_mins'])} min]")

    print()
    print(sep)

    # 9. Detalhe do Melhor e Pior
    for titulo, key in [("MELHOR Sport", best_key), ("PIOR  Sport", worst_key)]:
        if key is None:
            continue
        acc  = lineup_accum[key]
        mins = acc["total_mins"]
        xg   = acc["total_xg"]  / mins * MATCH_DURATION
        xga  = acc["total_xga"] / mins * MATCH_DURATION
        poss = acc["poss_wsum"] / mins
        players_str = _fmt_lineup(key, id_to_name)
        print(f"\n{titulo}  ({mins} min)  xG/90: {xg:.2f}  xGA/90: {xga:.2f}  Posse: {poss:.1f}%")
        print(f"  Jogadores: {players_str}")

    # 10. Análise de impacto de jogador isolado (opcional)
    if player_name:
        player_split_analysis(lineup_accum, id_to_name, player_name)


def player_split_analysis(
    lineup_accum: dict,
    id_to_name: dict,
    player_name: str,
) -> None:
    """Compara métricas do Sport com e sem um jogador específico em campo."""
    # Resolver player_id pelo nome (busca parcial, case-insensitive)
    name_lower = player_name.lower()
    matches_pid = [
        pid for pid, nm in id_to_name.items()
        if name_lower in nm.lower()
    ]
    if not matches_pid:
        print(f"⚠  Jogador '{player_name}' não encontrado nos dados.")
        return
    if len(matches_pid) > 1:
        names = [id_to_name[p] for p in matches_pid]
        print(f"⚠  Mais de um jogador encontrado: {names}. Seja mais específico.")
        return

    pid = matches_pid[0]
    full_name = id_to_name[pid]

    # Agregar mins com vs sem o jogador
    groups: dict[str, dict] = {
        "com": {"total_xg": 0.0, "total_xga": 0.0, "poss_wsum": 0.0, "total_mins": 0},
        "sem": {"total_xg": 0.0, "total_xga": 0.0, "poss_wsum": 0.0, "total_mins": 0},
    }
    for lineup_key, acc in lineup_accum.items():
        grp = "com" if pid in lineup_key else "sem"
        groups[grp]["total_xg"]   += acc["total_xg"]
        groups[grp]["total_xga"]  += acc["total_xga"]
        groups[grp]["poss_wsum"]  += acc["poss_wsum"]
        groups[grp]["total_mins"] += acc["total_mins"]

    sep = "─" * 62
    print(f"\nANÁLISE DE IMPACTO — {full_name.upper()}")
    print(sep)
    print(f"{'Cenário':<12}  {'Mins':>4}  {'xG/90':>5}  {'xGA/90':>6}  {'Poss%':>5}  {'xG-xGA':>6}")
    print(sep)

    results = {}
    for label, grp in [("Com", "com"), ("Sem", "sem")]:
        acc  = groups[grp]
        mins = acc["total_mins"]
        if mins == 0:
            print(f"{label:<12}  {'—':>4}  {'—':>5}  {'—':>6}  {'—':>5}  {'—':>6}")
            continue
        xg   = acc["total_xg"]  / mins * MATCH_DURATION
        xga  = acc["total_xga"] / mins * MATCH_DURATION
        poss = acc["poss_wsum"] / mins
        diff = xg - xga
        results[grp] = {"xg": xg, "xga": xga, "poss": poss, "mins": mins}
        print(
            f"{label:<12}  {mins:>4}  {xg:>5.2f}  {xga:>6.2f}  {poss:>4.1f}%  {diff:>+6.2f}"
        )

    print(sep)

    # Delta entre cenários
    if "com" in results and "sem" in results:
        c, s = results["com"], results["sem"]
        dxg   = c["xg"]   - s["xg"]
        dxga  = c["xga"]  - s["xga"]
        dposs = c["poss"] - s["poss"]
        print(f"{'Δ (com−sem)':<12}  {'':>4}  {dxg:>+5.2f}  {dxga:>+6.2f}  {dposs:>+4.1f}%")
        print()
        # Interpretação
        verdict_parts = []
        if dxg > 0.15:
            verdict_parts.append(f"cria mais ({dxg:+.2f} xG/90)")
        elif dxg < -0.15:
            verdict_parts.append(f"cria menos ({dxg:+.2f} xG/90)")
        if dxga < -0.15:
            verdict_parts.append(f"sofre menos ({dxga:+.2f} xGA/90)")
        elif dxga > 0.15:
            verdict_parts.append(f"sofre mais ({dxga:+.2f} xGA/90)")
        if abs(dposs) >= 3:
            verdict_parts.append(f"posse {'maior' if dposs > 0 else 'menor'} ({dposs:+.1f}%)")
        if verdict_parts:
            print(f"  Com {full_name}: " + " · ".join(verdict_parts) + ".")
        else:
            print(f"  Impacto de {full_name} pouco expressivo nas métricas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Análise de lineups do Sport na Série B")
    parser.add_argument("--min-minutes", type=int, default=20,
                        help="Mínimo de minutos para um lineup ser considerado válido (default: 20)")
    parser.add_argument("--player", type=str, default=None,
                        help="Nome (parcial) do jogador para análise de impacto isolado")
    args = parser.parse_args()
    main(min_minutes=args.min_minutes, player_name=args.player)
