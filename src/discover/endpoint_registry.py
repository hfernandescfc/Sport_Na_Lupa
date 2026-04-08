from __future__ import annotations

from src.config import Settings
from src.discover.network_sniffer import sniff_sofascore_requests, write_discovery_notes
from src.utils.io import write_json
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def discover_endpoints(settings: Settings) -> None:
    registry_path = settings.raw_dir / "sofascore" / "endpoint_registry.json"
    target_url = "https://www.sofascore.com/pt/football/team/sport-recife/1959"
    result = sniff_sofascore_requests(settings, target_url=target_url)

    payload = {"generated_by": "discover-endpoints", "status": result.status, "endpoints": []}

    if result.endpoints:
        payload["endpoints"] = [
            {
                "name": _infer_endpoint_name(item["path"]),
                "url_pattern": item["path"],
                "entity_type": _infer_entity_type(item["path"]),
                "method": item["method"],
                "requires_browser": True,
                "notes": f"Captured from {target_url}",
            }
            for item in result.endpoints
        ]
    else:
        payload["endpoints"] = [
            {
                "name": "match_shotmap",
                "url_pattern": "/api/v1/event/{match_id}/shotmap",
                "entity_type": "match",
                "method": "GET",
                "requires_browser": True,
                "notes": "Fallback seed from the reference notebook tied to the video.",
            }
        ]
        if result.error:
            logger.warning("Endpoint discovery fallback used: %s", result.error)

    write_json(registry_path, payload)
    write_discovery_notes(settings, result=result)


def _infer_endpoint_name(path: str) -> str:
    normalized = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    return normalized.replace("-", "_")


def _infer_entity_type(path: str) -> str:
    if "/team/" in path:
        return "team"
    if "/event/" in path:
        return "match"
    if "/unique-tournament/" in path or "/tournament/" in path:
        return "competition"
    return "unknown"
