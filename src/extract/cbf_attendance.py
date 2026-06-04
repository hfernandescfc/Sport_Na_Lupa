"""Extract stadium attendance from CBF website — Série B 2026.

Flow per round:
  1. GET https://www.cbf.com.br/api/cbf/jogos/campeonato/1260612/rodada/{N}/fase
     → returns 10 games with metadata + documentos[] URLs
  2. For each game: download Boletim Financeiro PDF and parse:
     - publico_pagante (total vendidos)
     - renda_bruta (total arrecadado)

Output:
  data/processed/{season}/attendance/serie_b_{season}_attendance.json
"""
from __future__ import annotations

import datetime
import io
import json
import re
import ssl
import time
import urllib.request
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)

# CBF internal IDs for Série B 2026 (discovered via RSC payload reverse-engineering)
_CBF_COMPETITION_ID = "1260612"
_CBF_JOGOS_URL = (
    "https://www.cbf.com.br/api/cbf/jogos/campeonato/{competition_id}/rodada/{round}/fase"
)
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://www.cbf.com.br",
    "Referer": "https://www.cbf.com.br/futebol-brasileiro/tabelas/campeonato-brasileiro/serie-b/",
}


def sync_attendance(settings: Settings, season: int, from_round: int = 1, to_round: int = 38) -> None:
    """Fetch CBF attendance data for Série B rounds from_round..to_round."""
    try:
        import pdfplumber  # noqa: F401
    except ImportError:
        logger.error("pdfplumber not installed — run: pip install pdfplumber")
        return

    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_ctx))

    all_records: list[dict[str, Any]] = []

    for round_num in range(from_round, to_round + 1):
        logger.info("Fetching CBF attendance for round %d", round_num)
        try:
            records = _fetch_round(opener, round_num, season)
            all_records.extend(records)
            logger.info("Round %d: %d/%d jogos com boletim", round_num,
                        sum(1 for r in records if r["publico_pagante"] is not None), len(records))
        except Exception as exc:
            logger.warning("Failed to fetch round %d: %s", round_num, exc)
        time.sleep(0.5)

    out_path = (
        settings.processed_dir / str(season) / "attendance"
        / f"serie_b_{season}_attendance.json"
    )
    write_json(out_path, {
        "season": season,
        "competition_id": _CBF_COMPETITION_ID,
        "from_round": from_round,
        "to_round": to_round,
        "record_count": len(all_records),
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
        "records": all_records,
    })
    logger.info("Attendance saved: %d records → %s", len(all_records), out_path)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_round(opener: urllib.request.OpenerDirector, round_num: int, season: int) -> list[dict[str, Any]]:
    url = _CBF_JOGOS_URL.format(competition_id=_CBF_COMPETITION_ID, round=round_num)
    req = urllib.request.Request(url, headers=_HEADERS)
    with opener.open(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))

    jogos = [j for grupo in data.get("jogos", []) for j in grupo.get("jogo", [])]
    records: list[dict[str, Any]] = []

    for jogo in jogos:
        record = _build_record(opener, jogo, round_num, season)
        records.append(record)
        time.sleep(0.3)

    return records


def _build_record(
    opener: urllib.request.OpenerDirector,
    jogo: dict[str, Any],
    round_num: int,
    season: int,
) -> dict[str, Any]:
    id_jogo = jogo.get("id_jogo")
    mandante = jogo.get("mandante", {})
    visitante = jogo.get("visitante", {})
    docs = {d["title"]: d["url"] for d in jogo.get("documentos", [])}

    record: dict[str, Any] = {
        "season": season,
        "round": round_num,
        "id_jogo": id_jogo,
        "num_jogo": jogo.get("num_jogo"),
        "data": jogo.get("data", "").strip(),
        "hora": jogo.get("hora", "").strip(),
        "local": jogo.get("local", "").strip(),
        "mandante_id": mandante.get("id"),
        "mandante_nome": mandante.get("nome"),
        "visitante_id": visitante.get("id"),
        "visitante_nome": visitante.get("nome"),
        "gols_mandante": _int_or_none(mandante.get("gols")),
        "gols_visitante": _int_or_none(visitante.get("gols")),
        "boletim_url": docs.get("Boletim Financeiro"),
        "sumula_url": docs.get("Súmula") or docs.get("S\u00famula"),
        "publico_pagante": None,
        "renda_bruta": None,
        "boletim_status": "sem_boletim",
        "fetched_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

    bf_url = record["boletim_url"]
    if bf_url:
        try:
            pagante, renda = _parse_boletim(opener, bf_url)
            record["publico_pagante"] = pagante
            record["renda_bruta"] = renda
            record["boletim_status"] = "ok" if pagante is not None else "parse_failed"
        except Exception as exc:
            logger.warning("Boletim parse failed id_jogo=%s: %s", id_jogo, exc)
            record["boletim_status"] = "download_failed"

    return record


def _parse_boletim(opener: urllib.request.OpenerDirector, url: str) -> tuple[int | None, float | None]:
    """Download PDF and extract total paid attendance + gross revenue."""
    import pdfplumber

    req = urllib.request.Request(url, headers={"User-Agent": _HEADERS["User-Agent"]})
    with opener.open(req, timeout=15) as r:
        pdf_bytes = r.read()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # Two PDF formats observed:
    # CBF-system:  "TOTAL  2.485  0  2.485  36.140,00"
    # FPF/state:   "TOTAIS  2754  0  2754  R$ 73.615,00"
    # Pattern: TOTAL(IS?) <disponivel> <devolvidos> <vendidos> (R$)? <arrecadacao>
    # "TOTAL" (CBF system) or "TOTAIS" (FPF/state federation system — plural)
    pat = r"TOTA(?:L|IS)\s+([\d.,]+)\s+([\d.,]+)\s+([\d.,]+)\s+(?:R\$\s*)?([\d.,]+)"
    m = re.search(pat, text, re.MULTILINE)
    if m:
        vendidos_str = m.group(3).replace(".", "").replace(",", "")
        renda_str = m.group(4).replace(".", "").replace(",", ".")
        try:
            vendidos = int(vendidos_str)
            renda = float(renda_str)
            return vendidos, renda
        except ValueError:
            pass

    logger.debug("Could not parse attendance from PDF: %s", url)
    return None, None


def _int_or_none(val: Any) -> int | None:
    try:
        return int(val)
    except (TypeError, ValueError):
        return None
