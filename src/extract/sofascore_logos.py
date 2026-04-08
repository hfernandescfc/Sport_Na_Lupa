"""Download escudos dos 20 times da Série B via Selenium (Edge headless).

O SofaScore bloqueia requisições diretas ao CDN com 403; o Selenium contorna
isso porque o browser envia os cookies e headers corretos.

Output
------
  data/cache/logos/{team_id}.png   — um arquivo por time
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from src.config import Settings
from src.discover.team_mapper import MANUAL_TEAM_MAPPINGS
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def _make_options() -> Any:
    from selenium.webdriver.edge.options import Options
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    return opts


def _open_driver(options: Any) -> Any:
    from selenium import webdriver
    driver = webdriver.Edge(options=options)
    driver.set_page_load_timeout(30)
    driver.get("https://www.sofascore.com/pt/football")
    return driver


def _fetch_image_b64(driver: Any, team_id: int) -> bytes | None:
    """Busca imagem do escudo via XHR binário e retorna bytes PNG."""
    result = driver.execute_script(
        """
        var url = "/api/v1/team/" + arguments[0] + "/image";
        var xhr = new XMLHttpRequest();
        xhr.open("GET", url, false);
        xhr.overrideMimeType("text/plain; charset=x-user-defined");
        xhr.send();
        if (xhr.status !== 200) return null;
        var binary = xhr.responseText;
        var bytes = new Uint8Array(binary.length);
        for (var i = 0; i < binary.length; i++) {
            bytes[i] = binary.charCodeAt(i) & 0xff;
        }
        return btoa(String.fromCharCode.apply(null, bytes));
        """,
        team_id,
    )
    if not result:
        return None
    try:
        return base64.b64decode(result)
    except Exception:
        return None


def sync_logos(settings: Settings, season: int) -> None:
    cache_dir = settings.base_dir / "data" / "cache" / "logos"
    cache_dir.mkdir(parents=True, exist_ok=True)

    teams = {
        key: val["sofascore_team_id"]
        for key, val in MANUAL_TEAM_MAPPINGS.items()
        if val.get("mapping_status") == "confirmed"
    }
    logger.info("Downloading logos for %s teams -> %s", len(teams), cache_dir)

    try:
        from selenium import webdriver  # noqa: F401
    except ImportError as exc:
        logger.error("Selenium not available: %s", exc)
        return

    options = _make_options()
    driver = None
    ok = 0
    try:
        driver = _open_driver(options)
        for team_key, team_id in sorted(teams.items()):
            dest = cache_dir / f"{team_id}.png"
            if dest.exists():
                logger.info("  skip %s (cached)", team_key)
                ok += 1
                continue
            data = _fetch_image_b64(driver, team_id)
            if data:
                dest.write_bytes(data)
                ok += 1
                logger.info("  OK   %s (%s bytes)", team_key, len(data))
            else:
                logger.warning("  FAIL %s (team_id=%s)", team_key, team_id)
    finally:
        if driver:
            driver.quit()

    logger.info("Logo sync complete: %s/%s downloaded", ok, len(teams))
