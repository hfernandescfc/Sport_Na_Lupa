from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(log_level: str, logs_dir: Path) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "sportsofa.log"
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

