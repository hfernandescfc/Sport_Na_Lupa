from __future__ import annotations

from typing import Any

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import Settings


@retry(wait=wait_exponential(min=1, max=8), stop=stop_after_attempt(3))
def get_json(settings: Settings, url: str, params: dict[str, Any] | None = None) -> Any:
    response = requests.get(
        url,
        params=params,
        timeout=settings.request_timeout,
        headers={"User-Agent": settings.user_agent},
    )
    response.raise_for_status()
    return response.json()

