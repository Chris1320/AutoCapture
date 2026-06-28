from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def configure_logging(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "autocapture.log"

    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        backtrace=False,
        diagnose=False,
        enqueue=True,
    )
    logger.add(
        log_path,
        level="DEBUG",
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        enqueue=True,
    )
    return log_path
