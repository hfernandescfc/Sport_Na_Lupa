"""Transform raw incidents JSON into two curated tables.

Reads:
  data/processed/{season}/incidents/sport_incidents.json
  data/processed/{season}/incidents/serie_b_incidents.json

Produces:
  data/curated/sport_2026/match_incidents.csv     — one row per incident (goal/card/sub)
  data/curated/sport_2026/goal_sequences.csv      — one row per action in a goal's passing chain
  data/curated/serie_b_2026/match_incidents.csv
  data/curated/serie_b_2026/goal_sequences.csv
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

# Columns for match_incidents.csv
INCIDENT_COLS = [
    "season", "competition", "round", "event_id", "match_code", "match_label",
    "home_team", "away_team",
    "incident_id", "incident_type", "incident_class",
    "time", "added_time",
    "is_home",
    "home_score", "away_score",
    # Goal
    "scorer_name", "scorer_id", "assist_name", "assist_id",
    # Card
    "carded_player_name", "carded_player_id", "card_reason",
    # Substitution
    "player_in_name", "player_in_id",
    "player_out_name", "player_out_id",
    "transformed_at",
]

# Columns for goal_sequences.csv
SEQUENCE_COLS = [
    "season", "competition", "round", "event_id", "match_code", "match_label",
    "home_team", "away_team",
    "goal_incident_id", "scorer_name", "goal_minute", "goal_added_time",
    "home_score_after", "away_score_after",
    "sequence_order",
    "player_name", "player_id", "player_position",
    "action_type", "is_assist",
    "from_x", "from_y",
    "to_x", "to_y",
    "is_home",
    "transformed_at",
]


def transform_incidents(settings: Settings, season: int) -> None:
    inc_dir = settings.processed_dir / str(season) / "incidents"

    for scope, filename, curated_subdir in [
        ("sport_all",  "sport_incidents.json",   f"sport_{season}"),
        ("serie_b",    "serie_b_incidents.json",  f"serie_b_{season}"),
    ]:
        src_path = inc_dir / filename
        if not src_path.exists():
            logger.warning("[%s] Incidents file not found: %s", scope, src_path)
            continue

        data = json.loads(src_path.read_text(encoding="utf-8"))
        matches = data.get("matches", [])

        incident_rows: list[dict[str, Any]] = []
        sequence_rows: list[dict[str, Any]] = []
        now = datetime.datetime.utcnow().isoformat() + "Z"

        for match in matches:
            meta = {
                "season": season,
                "competition": match.get("competition"),
                "round": match.get("round"),
                "event_id": match.get("event_id"),
                "match_code": match.get("match_code"),
                "match_label": f"{match.get('home_team')} x {match.get('away_team')}",
                "home_team": match.get("home_team"),
                "away_team": match.get("away_team"),
                "transformed_at": now,
            }

            for incident in match.get("incidents", []):
                itype = incident.get("incidentType")

                row = {**meta}
                row["incident_id"] = incident.get("id")
                row["incident_type"] = itype
                row["incident_class"] = incident.get("incidentClass")
                row["time"] = incident.get("time")
                row["added_time"] = incident.get("addedTime")
                row["is_home"] = incident.get("isHome")

                if itype == "goal":
                    row["home_score"] = incident.get("homeScore")
                    row["away_score"] = incident.get("awayScore")
                    player = incident.get("player") or {}
                    row["scorer_name"] = player.get("name")
                    row["scorer_id"] = player.get("id")
                    assist = incident.get("assist1") or {}
                    row["assist_name"] = assist.get("name")
                    row["assist_id"] = assist.get("id")

                    # Goal passing sequence
                    for order, action in enumerate(
                        incident.get("footballPassingNetworkAction", []), start=1
                    ):
                        ap = action.get("player") or {}
                        orig = action.get("playerCoordinates") or {}
                        dest = action.get("passEndCoordinates") or {}
                        seq_row = {
                            **meta,
                            "goal_incident_id": incident.get("id"),
                            "scorer_name": player.get("name"),
                            "goal_minute": incident.get("time"),
                            "goal_added_time": incident.get("addedTime"),
                            "home_score_after": incident.get("homeScore"),
                            "away_score_after": incident.get("awayScore"),
                            "sequence_order": order,
                            "player_name": ap.get("name"),
                            "player_id": ap.get("id"),
                            "player_position": ap.get("position"),
                            "action_type": action.get("eventType"),
                            "is_assist": action.get("isAssist", False),
                            "from_x": orig.get("x"),
                            "from_y": orig.get("y"),
                            "to_x": dest.get("x"),
                            "to_y": dest.get("y"),
                            "is_home": action.get("isHome"),
                        }
                        sequence_rows.append(seq_row)

                elif itype == "card":
                    player = incident.get("player") or {}
                    row["carded_player_name"] = player.get("name") or incident.get("playerName")
                    row["carded_player_id"] = player.get("id")
                    row["card_reason"] = incident.get("reason")

                elif itype == "substitution":
                    pin = incident.get("playerIn") or {}
                    pout = incident.get("playerOut") or {}
                    row["player_in_name"] = pin.get("name")
                    row["player_in_id"] = pin.get("id")
                    row["player_out_name"] = pout.get("name")
                    row["player_out_id"] = pout.get("id")

                # period and injuryTime have no player fields — row keeps only meta + timing
                incident_rows.append(row)

        curated_dir = settings.curated_dir / curated_subdir
        _write(curated_dir / "match_incidents.csv", incident_rows, INCIDENT_COLS)
        _write(curated_dir / "goal_sequences.csv", sequence_rows, SEQUENCE_COLS)

        n_goals = sum(1 for r in incident_rows if r.get("incident_type") == "goal")
        logger.info(
            "[%s] match_incidents: %d rows (%d goals) | goal_sequences: %d action rows",
            scope, len(incident_rows), n_goals, len(sequence_rows),
        )


def _write(path: Path, rows: list[dict[str, Any]], cols: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = [{c: r.get(c) for c in cols} for r in rows]
    write_csv(path, ordered)
