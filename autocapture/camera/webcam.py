from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from .base import CaptureFailedError


class WebcamCaptureSource:
    def __init__(self, device_index: int) -> None:
        self._device_index = device_index

    def capture(self, destination: Path, latest_frame: object | None = None) -> Path:
        try:
            import cv2  # pylint: disable=import-outside-toplevel

        except ImportError as exc:  # pragma: no cover - runtime dependency guard
            raise CaptureFailedError(
                "OpenCV is not available for webcam capture"
            ) from exc

        destination.parent.mkdir(parents=True, exist_ok=True)
        frame: object | None = latest_frame

        if frame is None:
            backend: int = getattr(cv2, "CAP_DSHOW", 0)
            cv2_any: Any = cv2
            capture: Any = getattr(cv2_any, "VideoCapture")(self._device_index, backend)
            if not capture.isOpened():
                capture.release()
                raise CaptureFailedError(
                    f"Unable to open webcam device {self._device_index}"
                )

            try:
                for _ in range(3):
                    capture.read()

                success, frame = capture.read()
                if not success:
                    raise CaptureFailedError(
                        f"Unable to read frame from webcam device {self._device_index}"
                    )

            finally:
                capture.release()

        if frame is None:
            raise CaptureFailedError("No frame available for webcam capture")

        cv2_any: Any = cv2
        if not getattr(cv2_any, "imwrite")(str(destination), frame):
            raise CaptureFailedError(f"Unable to save webcam image to {destination}")

        logger.debug("Saved webcam capture to {}", destination)
        return destination
