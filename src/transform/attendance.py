"""Transform CBF attendance JSON into curated attendance.csv.

Reads:
  data/processed/{season}/attendance/serie_b_{season}_attendance.json

Produces:
  data/curated/serie_b_{season}/attendance.csv

One row per match, with:
  season, round, id_jogo, data, hora, estadio, cidade, uf,
  mandante, visitante, gols_mandante, gols_visitante,
  publico_pagante, renda_bruta, boletim_status
"""
from __future__ import annotations

import datetime
import json
import re
from pathlib import Path

from src.config import Settings
from src.utils.io import write_csv
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

ATTENDANCE_COLS = [
    "season", "round", "id_jogo", "num_jogo",
    "data", "hora",
    "estadio", "cidade", "uf",
    "mandante_id", "mandante_nome",
    "visitante_id", "visitante_nome",
    "gols_mandante", "gols_visitante",
    "publico_pagante", "renda_bruta",
    "boletim_status",
    "transformed_at",
]


def transform_attendance(settings: Settings, season: int) -> None:
    src = (
        settings.processed_dir / str(season) / "attendance"
        / f"serie_b_{season}_attendance.json"
    )
    if not src.exists():
        logger.warning("Attendance source not found: %s", src)
        return

    data = json.loads(src.read_text(encoding="utf-8"))
    records = data.get("records", [])
    if not records:
        logger.warning("No attendance records in %s", src)
        return

    now = datetime.datetime.utcnow().isoformat() + "Z"
    rows = []
    for r in records:
        estadio, cidade, uf = _parse_local(r.get("local", ""))
        rows.append({
            "season": r.get("season"),
            "round": r.get("round"),
            "id_jogo": r.get("id_jogo"),
            "num_jogo": r.get("num_jogo"),
            "data": r.get("data"),
            "hora": r.get("hora"),
            "estadio": estadio,
            "cidade": cidade,
            "uf": uf,
            "mandante_id": r.get("mandante_id"),
            "mandante_nome": r.get("mandante_nome"),
            "visitante_id": r.get("visitante_id"),
            "visitante_nome": r.get("visitante_nome"),
            "gols_mandante": r.get("gols_mandante"),
            "gols_visitante": r.get("gols_visitante"),
            "publico_pagante": r.get("publico_pagante"),
            "renda_bruta": r.get("renda_bruta"),
            "boletim_status": r.get("boletim_status"),
            "transformed_at": now,
        })

    out = settings.curated_dir / f"serie_b_{season}" / "attendance.csv"
    write_csv(out, rows)

    ok = sum(1 for r in rows if r["publico_pagante"] is not None)
    logger.info(
        "Attendance transform: %d rows (%d com público) → %s", len(rows), ok, out
    )


# ---------------------------------------------------------------------------

def _parse_local(local: str) -> tuple[str, str, str]:
    """Parse 'Estadio Nome - Cidade - UF' into (estadio, cidade, uf)."""
    parts = [p.strip() for p in local.split(" - ")]
    if len(parts) >= 3:
        return parts[0], parts[-2], parts[-1]
    if len(parts) == 2:
        return parts[0], parts[1], ""
    return local, "", ""
