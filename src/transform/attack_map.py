"""Aggregate extended stats + shotmap for an opponent and detect play patterns.

Input:
  data/processed/{season}/opponents/{team_key}/
    extended_stats.csv
    shotmap.json

Output:
  data/curated/opponents_{season}/{team_key}/
    attack_profile.json

The attack profile contains:
  - averages:       per-match averages for each extended stat
  - attack_zones:   left/center/right shot percentages from shotmap
  - patterns:       list of detected play style bullets (PT-BR)
  - shots:          raw shot list (for card visualization)

Usage:
    python -m src.main transform-attack-map --team-key avai --season 2026
"""
from __future__ import annotations

import csv
import datetime
import json
import statistics
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Numeric fields to average across matches (all from extended_stats.csv)
NUMERIC_FIELDS = [
    "possession",
    "expected_goals",
    "big_chances_created",
    "shots_total",
    "shots_on_target",
    "shots_inside_box",
    "shots_outside_box",
    "final_third_entries",
    "final_third_phases",
    "long_balls_accurate",
    "crosses_accurate",
    "touches_opp_box",
    "passes_total",
    "passes_accurate",
    "corners",
    "fouls",
    "interceptions",
    "clearances",
]

# Lateral zone boundaries (player_y on 0-100 scale)
ZONE_LEFT_MAX   = 33.0
ZONE_RIGHT_MIN  = 67.0


def transform_attack_map(settings: Settings, team_key: str, season: int) -> None:
    """Aggregate attack map data and detect play patterns."""
    in_dir  = settings.processed_dir / str(season) / "opponents" / team_key
    out_dir = settings.curated_dir / f"opponents_{season}" / team_key

    extended_path = in_dir / "extended_stats.csv"
    shotmap_path  = in_dir / "shotmap.json"

    if not extended_path.exists():
        logger.error(
            "extended_stats.csv not found at %s — run sync-attack-map first.", extended_path
        )
        return

    rows = _read_csv(extended_path)
    if not rows:
        logger.error("[%s] extended_stats.csv is empty.", team_key)
        return

    shots: list[dict[str, Any]] = []
    if shotmap_path.exists():
        try:
            with open(shotmap_path, encoding="utf-8") as f:
                sm = json.load(f)
            shots = sm.get("shots", [])
        except Exception as exc:
            logger.warning("Could not read shotmap.json: %s", exc)

    averages   = _compute_averages(rows)
    atk_zones  = _compute_attack_zones(shots)
    patterns   = _detect_patterns(averages, atk_zones)

    profile: dict[str, Any] = {
        "team_key":         team_key,
        "season":           season,
        "matches_analyzed": len(rows),
        "fetched_at":       datetime.datetime.utcnow().isoformat() + "Z",
        "averages":         averages,
        "attack_zones":     atk_zones,
        "patterns":         patterns,
        "shots":            shots,
    }

    write_json(out_dir / "attack_profile.json", profile)
    logger.info(
        "[%s] Attack profile saved — %d matches, %d shots, %d patterns",
        team_key, len(rows), len(shots), len(patterns),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_averages(rows: list[dict[str, Any]]) -> dict[str, float]:
    """Return per-match averages for all numeric fields."""
    n = len(rows)
    result: dict[str, float] = {}

    for field in NUMERIC_FIELDS:
        vals: list[float] = []
        for r in rows:
            v = r.get(field)
            if v is not None and v != "":
                try:
                    vals.append(float(v))
                except (ValueError, TypeError):
                    pass
        if vals:
            result[field] = round(sum(vals) / n, 2)

    # Derived metrics
    passes_total  = result.get("passes_total",  0)
    long_balls    = result.get("long_balls_accurate", 0)
    shots_total   = result.get("shots_total",   0)
    shots_in_box  = result.get("shots_inside_box", 0)

    result["long_balls_pct"] = round(
        long_balls / passes_total * 100, 1
    ) if passes_total else 0.0

    result["shots_inside_box_pct"] = round(
        shots_in_box / shots_total * 100, 1
    ) if shots_total else 0.0

    return result


def _compute_attack_zones(shots: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify shots into left / center / right zones from player_y coordinate."""
    valid_shots = [
        s for s in shots
        if s.get("player_y") is not None and s.get("player_x") is not None
    ]
    total = len(valid_shots)

    if not total:
        return {
            "total_shots": 0,
            "left_shots": 0, "center_shots": 0, "right_shots": 0,
            "left_pct":   0.0, "center_pct":   0.0, "right_pct":   0.0,
        }

    left   = sum(1 for s in valid_shots if float(s["player_y"]) < ZONE_LEFT_MAX)
    right  = sum(1 for s in valid_shots if float(s["player_y"]) > ZONE_RIGHT_MIN)
    center = total - left - right

    return {
        "total_shots":  total,
        "left_shots":   left,
        "center_shots": center,
        "right_shots":  right,
        "left_pct":     round(left   / total * 100, 1),
        "center_pct":   round(center / total * 100, 1),
        "right_pct":    round(right  / total * 100, 1),
    }


def _detect_patterns(
    avg: dict[str, float],
    zones: dict[str, Any],
) -> list[str]:
    """Return 2–4 detected play style bullets in PT-BR."""
    bullets: list[str] = []

    # 1. Attack zone dominance
    left_pct   = zones.get("left_pct",   0)
    center_pct = zones.get("center_pct", 0)
    right_pct  = zones.get("right_pct",  0)
    total_shots = zones.get("total_shots", 0)

    if total_shots >= 3:
        dominant_zone = max(
            [("esquerdo", left_pct), ("centro", center_pct), ("direito", right_pct)],
            key=lambda t: t[1],
        )
        zone_name, zone_pct = dominant_zone

        if zone_pct >= 45:
            bullets.append(
                f"Ataque fortemente concentrado pelo {zone_name} ({zone_pct:.0f}% dos chutes)"
            )
        elif zone_pct >= 38:
            bullets.append(
                f"Preferência ofensiva pelo corredor {zone_name} ({zone_pct:.0f}% dos chutes)"
            )
        else:
            bullets.append(
                f"Ataque equilibrado pelas faixas — leve tendência pelo {zone_name} ({zone_pct:.0f}%)"
            )

    # 2. Possession style
    possession = avg.get("possession", 50)
    if possession >= 57:
        bullets.append(
            f"Jogo com posse dominante — controla {possession:.0f}% em média"
        )
    elif possession <= 43:
        bullets.append(
            f"Estilo reativo — cede posse ({possession:.0f}%) e explora contra-ataques"
        )

    # 3. Final third pressure
    fte = avg.get("final_third_entries", 0)
    if fte >= 35:
        bullets.append(
            f"Alta pressão no último terço — {fte:.0f} entradas por partida"
        )
    elif fte <= 20:
        bullets.append(
            f"Pouca penetração no último terço — {fte:.0f} entradas por partida"
        )

    # 4. Long ball vs short game
    lb_pct = avg.get("long_balls_pct", 0)
    if lb_pct >= 8:
        bullets.append(
            f"Jogo direto com bolas longas — {lb_pct:.1f}% dos passes são lançamentos"
        )
    elif lb_pct <= 3 and avg.get("passes_total", 0) >= 350:
        bullets.append(
            f"Construção pela base — passes curtos e encadeados ({lb_pct:.1f}% de bolas longas)"
        )

    # 5. Crossing game
    crosses = avg.get("crosses_accurate", 0)
    if crosses >= 5:
        bullets.append(
            f"Ameaça pelos flancos — {crosses:.1f} cruzamentos certeiros por partida"
        )

    # 6. Box presence
    touches_box = avg.get("touches_opp_box", 0)
    if touches_box >= 25:
        bullets.append(
            f"Boa penetração na área adversária — {touches_box:.0f} toques por partida"
        )

    # 7. Shot quality
    inside_pct = avg.get("shots_inside_box_pct", 0)
    if inside_pct >= 75:
        bullets.append(
            f"Chutes quase exclusivamente dentro da área ({inside_pct:.0f}%)"
        )
    elif inside_pct <= 50:
        bullets.append(
            f"Tenta bastante de fora da área ({100-inside_pct:.0f}% dos chutes)"
        )

    # Limit to 4 most relevant bullets
    return bullets[:4]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        logger.error("Could not read %s: %s", path, exc)
        return []
