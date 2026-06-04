"""Game-state-adjusted xG for Série B.

Motivação
---------
O xPts atual (standings.py) usa o xG total da partida como λ de um Poisson, sem
saber **quando** cada finalização aconteceu nem **qual era o placar** naquele
instante. Isso infla o xG de "lixo de fim de jogo": um time perdendo de 2 gols
acumula chances enquanto o adversário recua, e o modelo credita um xPts alto que
não reflete o contexto real do jogo (efeito *game state* / *garbage-time xG*).

Solução
-------
Para cada finalização, reconstruímos o saldo de gols do time que finaliza no
minuto do chute (cruzando o shotmap com os minutos de gol dos incidents) e
aplicamos um peso graduado:

    |saldo| <= 1  (jogo equilibrado, dentro de 1 gol) → peso 1,00
    |saldo| == 2                                       → peso 0,50
    |saldo| >= 3                                       → peso 0,25

O xG ponderado da partida é Σ(peso × xg_chute). Ele alimenta o mesmo Poisson do
standings.py, gerando um xPts ajustado por contexto.

Entradas
--------
  data/processed/{season}/shotmaps/serie_b_shotmaps.json  (xg + minuto por chute)
  data/curated/serie_b_{season}/match_incidents.csv       (minutos de gol + placar)
  data/curated/serie_b_{season}/matches.csv               (event_id ↔ team_key)

Saída
-----
  data/curated/serie_b_{season}/game_state_xg.csv
    uma linha por (event_id, team_key): xg_raw, xg_weighted + breakdown por estado
"""
from __future__ import annotations

import datetime
import json

import pandas as pd

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


# Pesos por |saldo de gols| no momento do chute
def _state_weight(diff: int) -> float:
    a = abs(diff)
    if a <= 1:
        return 1.0
    if a == 2:
        return 0.5
    return 0.25


def _to_int(v) -> int:
    """Converte minuto/acréscimo (pode vir como '4.0', 4, None) para int."""
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return 0
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return 0
    return int(float(s))


def _shot_key(minute, added_time) -> int:
    """Ordem total de eventos: minuto-base × 100 + acréscimos."""
    return _to_int(minute) * 100 + _to_int(added_time)


def _build_goal_timeline(incidents: pd.DataFrame) -> dict[str, list[tuple[int, int, int]]]:
    """Para cada event_id, lista ordenada de (chave_tempo, home_score, away_score)
    APÓS cada gol. O placar vem direto do incident (já cumulativo)."""
    goals = incidents[incidents["incident_type"] == "goal"].copy()
    goals["home_score"] = pd.to_numeric(goals["home_score"], errors="coerce")
    goals["away_score"] = pd.to_numeric(goals["away_score"], errors="coerce")
    goals = goals.dropna(subset=["home_score", "away_score"])

    timeline: dict[str, list[tuple[int, int, int]]] = {}
    for event_id, grp in goals.groupby("event_id"):
        events = [
            (_shot_key(r["time"], r.get("added_time")), int(r["home_score"]), int(r["away_score"]))
            for _, r in grp.iterrows()
        ]
        events.sort(key=lambda t: t[0])
        timeline[str(event_id)] = events
    return timeline


def _score_before(timeline_events: list[tuple[int, int, int]], shot_key: int) -> tuple[int, int]:
    """Placar (home, away) imediatamente ANTES do chute — último gol com chave < shot_key."""
    home, away = 0, 0
    for key, h, a in timeline_events:
        if key < shot_key:
            home, away = h, a
        else:
            break
    return home, away


def transform_game_state_xg(settings: Settings, season: int) -> None:
    curated = settings.curated_dir / f"serie_b_{season}"
    shotmap_path = settings.processed_dir / str(season) / "shotmaps" / "serie_b_shotmaps.json"
    incidents_path = curated / "match_incidents.csv"
    matches_path = curated / "matches.csv"

    for p in (shotmap_path, incidents_path, matches_path):
        if not p.exists():
            logger.warning("Required file missing: %s — run sync-shotmap + transform-incidents first", p)
            return

    shot_data = json.loads(shotmap_path.read_text(encoding="utf-8"))
    incidents = pd.read_csv(incidents_path, dtype=str)
    matches = pd.read_csv(matches_path, dtype=str)

    # event_id → (home_team_key, away_team_key)
    keymap = {
        str(r["event_id"]): (r["home_team_key"], r["away_team_key"])
        for _, r in matches.iterrows()
        if pd.notna(r.get("event_id"))
    }
    # event_id → match_code, round
    meta = {
        str(r["event_id"]): (r.get("match_code", ""), r.get("round", ""))
        for _, r in matches.iterrows()
        if pd.notna(r.get("event_id"))
    }

    timeline = _build_goal_timeline(incidents)

    # Acumuladores por (event_id, is_home)
    agg: dict[tuple[str, bool], dict] = {}

    n_shots_total = 0
    n_no_timeline = 0
    for match in shot_data.get("matches", []):
        event_id = str(match.get("event_id"))
        events = timeline.get(event_id, [])
        if event_id not in keymap:
            continue
        home_key, away_key = keymap[event_id]

        for shot in match.get("shots", []):
            xg = shot.get("xg")
            if xg is None:
                continue
            xg = float(xg)
            is_home = bool(shot.get("is_home"))
            n_shots_total += 1

            shot_key = _shot_key(shot.get("minute"), shot.get("added_time"))
            home_b, away_b = _score_before(events, shot_key)
            diff = (home_b - away_b) if is_home else (away_b - home_b)
            if not events:
                n_no_timeline += 1  # sem gols no jogo → estado 0-0 (diff=0), peso 1.0
            w = _state_weight(diff)

            key = (event_id, is_home)
            rec = agg.setdefault(key, {
                "event_id": event_id,
                "is_home": is_home,
                "team_key": home_key if is_home else away_key,
                "xg_raw": 0.0, "xg_weighted": 0.0,
                "n_shots": 0, "n_decided": 0,
                "xg_level": 0.0, "xg_d2": 0.0, "xg_d3plus": 0.0,
            })
            rec["xg_raw"] += xg
            rec["xg_weighted"] += w * xg
            rec["n_shots"] += 1
            a = abs(diff)
            if a <= 1:
                rec["xg_level"] += xg
            elif a == 2:
                rec["xg_d2"] += xg
                rec["n_decided"] += 1
            else:
                rec["xg_d3plus"] += xg
                rec["n_decided"] += 1

    if not agg:
        logger.warning("No shots aggregated — game_state_xg not generated")
        return

    rows = []
    for rec in agg.values():
        match_code, rnd = meta.get(rec["event_id"], ("", ""))
        reduction = (
            (rec["xg_raw"] - rec["xg_weighted"]) / rec["xg_raw"]
            if rec["xg_raw"] > 0 else 0.0
        )
        rows.append({
            "event_id": rec["event_id"],
            "match_code": match_code,
            "round": rnd,
            "team_key": rec["team_key"],
            "is_home": rec["is_home"],
            "xg_raw": round(rec["xg_raw"], 4),
            "xg_weighted": round(rec["xg_weighted"], 4),
            "xg_reduction_pct": round(reduction * 100, 1),
            "n_shots": rec["n_shots"],
            "n_decided": rec["n_decided"],
            "xg_level": round(rec["xg_level"], 4),
            "xg_d2": round(rec["xg_d2"], 4),
            "xg_d3plus": round(rec["xg_d3plus"], 4),
        })

    rows.sort(key=lambda r: (str(r["round"]).zfill(3), r["event_id"], not r["is_home"]))
    out_path = curated / "game_state_xg.csv"
    write_csv(out_path, rows)
    logger.info(
        "Game-state xG: %d team-match rows from %d shots (%d matches, %d shots w/o goal timeline) → %s",
        len(rows), n_shots_total, len(shot_data.get("matches", [])), n_no_timeline, out_path,
    )
