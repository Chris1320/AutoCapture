from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import cast

from ..config import CameraMode


class CameraError(RuntimeError):
    """Raised when the camera workflow cannot complete."""


class CameraUnavailableError(CameraError):
    """Raised when the expected capture device cannot be reached."""


class CaptureFailedError(CameraError):
    """Raised when image acquisition or saving fails."""


@dataclass(slots=True, frozen=True)
class CaptureResult:
    image_path: Path
    camera_mode: CameraMode
    captured_at: datetime
    metadata: dict[str, str] = field(default_factory=lambda: cast(dict[str, str], {}))
