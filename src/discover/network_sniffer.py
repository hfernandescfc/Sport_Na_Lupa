from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import Settings
from src.utils.io import write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class DiscoveryResult:
    status: str
    target_url: str
    endpoints: list[dict[str, Any]]
    error: str | None = None


def sniff_sofascore_requests(settings: Settings, target_url: str) -> DiscoveryResult:
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from webdriver_manager.chrome import ChromeDriverManager
    except Exception as exc:  # pragma: no cover
        return DiscoveryResult(
            status="error",
            target_url=target_url,
            endpoints=[],
            error=f"Missing Selenium dependencies: {exc}",
        )

    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.set_capability(
            "goog:loggingPrefs",
            {"performance": "ALL", "browser": "ALL"},
        )
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()),
            options=options,
        )
        driver.set_page_load_timeout(settings.request_timeout)

        try:
            driver.get(target_url)
        except Exception:
            logger.warning("Page load timeout for %s; collecting partial logs", target_url)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        logs_raw = driver.get_log("performance")
        endpoints = _extract_api_requests(logs_raw)
        return DiscoveryResult(
            status="ok",
            target_url=target_url,
            endpoints=endpoints,
        )
    except Exception as exc:  # pragma: no cover
        return DiscoveryResult(
            status="error",
            target_url=target_url,
            endpoints=[],
            error=str(exc),
        )
    finally:
        if driver is not None:
            driver.quit()


def write_discovery_notes(settings: Settings, result: DiscoveryResult) -> Path:
    output = settings.raw_dir / "sofascore" / "discovery_notes.json"
    payload = {
        "status": result.status,
        "target_url": result.target_url,
        "endpoint_count": len(result.endpoints),
        "error": result.error,
    }
    write_json(output, payload)
    return output


def _extract_api_requests(logs_raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    endpoints_by_path: dict[str, dict[str, Any]] = {}

    for entry in logs_raw:
        try:
            message = json.loads(entry["message"])["message"]
            params = message.get("params", {})
            request = params.get("request", {})
            url = request.get("url", "")
            method = request.get("method", "")
        except Exception:
            continue

        if "/api/v1/" not in url:
            continue

        path = url.split(".com", 1)[-1]
        if path not in endpoints_by_path:
            endpoints_by_path[path] = {
                "path": path,
                "url": url,
                "method": method or "GET",
                "resource_type": params.get("type", ""),
            }

    return sorted(endpoints_by_path.values(), key=lambda item: item["path"])
