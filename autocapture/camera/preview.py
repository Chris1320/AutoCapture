from __future__ import annotations

from threading import Event, Lock
import sys
from typing import Any

from loguru import logger
from PySide6.QtCore import QThread, Signal

from .base import CameraUnavailableError


class OpenCvPreviewThread(QThread):
    frame_received = Signal(object)
    status_changed = Signal(str)
    failed = Signal(str)

    def __init__(
        self, device_index: int, preview_fps: int = 30, parent: Any = None
    ) -> None:
        super().__init__(parent)
        self._device_index = device_index
        self._preview_fps = max(1, preview_fps)
        self._stop_event = Event()
        self._frame_lock = Lock()
        self._latest_frame: object | None = None

    def set_device_index(self, device_index: int) -> None:
        self._device_index = device_index

    def latest_frame(self) -> object | None:
        with self._frame_lock:
            return self._latest_frame

    def stop(self) -> None:
        self._stop_event.set()

    def _open_capture(self) -> Any:
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - runtime dependency guard
            raise CameraUnavailableError("OpenCV is not available") from exc

        backend = getattr(cv2, "CAP_DSHOW", 0) if sys.platform == "win32" else 0
        cv2_any: Any = cv2
        capture: Any = getattr(cv2_any, "VideoCapture")(self._device_index, backend)
        if not capture.isOpened():
            capture.release()
            raise CameraUnavailableError(
                f"Unable to open capture device {self._device_index}"
            )
        return capture

    def run(self) -> None:
        capture: Any = None
        try:
            capture = self._open_capture()
            self.status_changed.emit(f"Preview started on device {self._device_index}")
            frame_delay = max(1, int(1000 / self._preview_fps))

            while not self._stop_event.is_set():
                success, frame = capture.read()
                if success:
                    with self._frame_lock:
                        self._latest_frame = (
                            frame.copy() if hasattr(frame, "copy") else frame
                        )
                    self.frame_received.emit(frame)
                else:
                    logger.debug(
                        "Preview frame read failed for device {}", self._device_index
                    )
                self.msleep(frame_delay)
        except CameraUnavailableError as exc:
            logger.warning("Preview thread failed: {}", exc)
            self.failed.emit(str(exc))
        finally:
            if capture is not None:
                capture.release()
            self.status_changed.emit("Preview stopped")
