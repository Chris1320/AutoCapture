from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from loguru import logger

from ..camera.base import CaptureFailedError


@dataclass(slots=True)
class CaptureStorage:
    root: Path

    @property
    def images_dir(self) -> Path:
        return self.root / "images"

    @property
    def logs_dir(self) -> Path:
        return self.root / "data" / "logs"

    @property
    def exports_dir(self) -> Path:
        return self.root / "exports"

    def ensure_layout(self) -> None:
        for directory in (self.root, self.images_dir, self.exports_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def build_image_path(self, *, extension: str = ".jpg") -> Path:
        stamp: str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        suffix: str = uuid4().hex[:8]
        return self.images_dir / f"capture_{stamp}_{suffix}{extension}"

    def write_frame(self, destination: Path, frame: object) -> Path:
        try:
            import cv2  # pylint: disable=import-outside-toplevel

        except ImportError as exc:  # pragma: no cover - runtime dependency guard
            raise CaptureFailedError(
                "OpenCV is not available for saving image files"
            ) from exc

        destination.parent.mkdir(parents=True, exist_ok=True)
        cv2_any: object = cv2
        if not getattr(cv2_any, "imwrite")(str(destination), frame):
            raise CaptureFailedError(f"Unable to write image file: {destination}")

        return destination

    def delete_file(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)

        except OSError as exc:
            logger.warning("Unable to delete file {}: {}", path, exc)
