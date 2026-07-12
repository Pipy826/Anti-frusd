from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any


LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


try:
    from loguru import logger as app_logger

    app_logger.remove()
    app_logger.add(sys.stderr, level="INFO", enqueue=True)
    app_logger.add(LOG_DIR / "app.log", level="INFO", rotation="10 MB", retention=10, encoding="utf-8", enqueue=True)
    app_logger.add(LOG_DIR / "error.log", level="ERROR", rotation="10 MB", retention=10, encoding="utf-8", enqueue=True)
except ImportError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        ],
    )
    app_logger = logging.getLogger("anti_fraud")


def log_event(event: str, **fields: Any) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    app_logger.info(f"{event} {payload}".strip())


def log_error(event: str, **fields: Any) -> None:
    payload = " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)
    app_logger.error(f"{event} {payload}".strip())

