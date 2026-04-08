from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    base_dir: Path
    log_level: str
    request_timeout: int
    user_agent: str

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def curated_dir(self) -> Path:
        return self.data_dir / "curated"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"


def get_settings() -> Settings:
    base_dir = Path(os.getenv("SPORTSOFA_BASE_DIR", ".")).resolve()
    return Settings(
        base_dir=base_dir,
        log_level=os.getenv("SPORTSOFA_LOG_LEVEL", "INFO"),
        request_timeout=int(os.getenv("SPORTSOFA_REQUEST_TIMEOUT", "30")),
        user_agent=os.getenv(
            "SPORTSOFA_USER_AGENT",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
        ),
    )

