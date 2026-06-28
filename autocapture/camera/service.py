from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal

from ..config import AppConfig, CameraMode
from .base import CameraError, CaptureResult
from .preview import OpenCvPreviewThread
from .webcam import WebcamCaptureSource
from .wia_dslr import WiaCaptureSource


class CaptureJob(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self, capture_callable: Callable[[], CaptureResult], parent: Any = None
    ) -> None:
        super().__init__(parent)
        self._capture_callable = capture_callable

    def run(self) -> None:
        try:
            self.completed.emit(self._capture_callable())

        except CameraError as exc:
            logger.exception("Capture job failed")
            self.failed.emit(str(exc))


class CameraService(QObject):
    preview_frame_received = Signal(object)
    preview_status_changed = Signal(str)
    capture_completed = Signal(object)
    capture_failed = Signal(str)
    status_changed = Signal(str)

    def __init__(self, config: AppConfig, parent: Any = None) -> None:
        super().__init__(parent)
        self._config = config
        self._mode = config.default_mode
        self._preview_thread: OpenCvPreviewThread | None = None
        self._capture_job: CaptureJob | None = None

    @property
    def mode(self) -> CameraMode:
        return self._mode

    def set_mode(self, mode: CameraMode) -> None:
        self._mode = mode

    def start_preview(self, mode: CameraMode | None = None) -> None:
        if mode is not None:
            self._mode = mode

        self.stop_preview()

        device_index: int = self._preview_device_index(self._mode)
        self._preview_thread = OpenCvPreviewThread(
            device_index, preview_fps=self._config.preview_fps
        )
        self._preview_thread.frame_received.connect(self.preview_frame_received.emit)
        self._preview_thread.status_changed.connect(self.preview_status_changed.emit)
        self._preview_thread.failed.connect(self._handle_preview_failure)
        self._preview_thread.start()

    def stop_preview(self) -> None:
        if self._preview_thread is None:
            return

        self._preview_thread.stop()
        self._preview_thread.wait(2000)
        self._preview_thread = None

    def latest_preview_frame(self) -> object | None:
        if self._preview_thread is None:
            return None

        return self._preview_thread.latest_frame()

    def capture_still(
        self, destination: Path, metadata: Mapping[str, str] | None = None
    ) -> bool:
        if self._capture_job is not None and self._capture_job.isRunning():
            self.status_changed.emit("A capture is already in progress")
            return False

        capture_callable: Callable[[], CaptureResult] = self._build_capture_callable(
            destination, metadata or {}
        )
        self._capture_job = CaptureJob(capture_callable)
        self._capture_job.completed.connect(self.capture_completed.emit)
        self._capture_job.failed.connect(self.capture_failed.emit)
        self._capture_job.finished.connect(self._clear_capture_job)
        self._capture_job.start()
        return True

    def shutdown(self) -> None:
        self.stop_preview()
        if self._capture_job is not None:
            self._capture_job.wait(2000)
            self._capture_job = None

    def _preview_device_index(self, mode: CameraMode) -> int:
        if mode == CameraMode.DSLR_WIA:
            return self._config.capture_card_preview_device_index

        return self._config.webcam_preview_device_index

    def _build_capture_callable(
        self, destination: Path, metadata: Mapping[str, str]
    ) -> Callable[[], CaptureResult]:
        mode: CameraMode = self._mode

        def capture() -> CaptureResult:
            image_path: Path
            if mode == CameraMode.DSLR_WIA:
                wia_source: WiaCaptureSource = WiaCaptureSource(
                    self._config.wia_device_name
                )
                image_path = wia_source.capture(destination)

            else:
                webcam_source: WebcamCaptureSource = WebcamCaptureSource(
                    self._config.webcam_preview_device_index
                )
                image_path = webcam_source.capture(
                    destination, self.latest_preview_frame()
                )

            return CaptureResult(
                image_path=image_path,
                camera_mode=mode,
                captured_at=datetime.now(),
                metadata=dict(metadata),
            )

        return capture

    def _handle_preview_failure(self, message: str) -> None:
        logger.warning("Preview error: {}", message)
        self.status_changed.emit(message)

    def _clear_capture_job(self) -> None:
        self._capture_job = None
