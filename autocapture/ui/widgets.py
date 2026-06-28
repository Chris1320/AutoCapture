from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


class VideoPreviewWidget(QLabel):
    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._current_pixmap: QPixmap | None = None
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(480, 320)
        self.setText("Preview is starting...")
        self.setStyleSheet("""
            QLabel {
                background: #101418;
                color: #ced8e3;
                border: 1px solid #2a3541;
                border-radius: 14px;
                padding: 16px;
                font-size: 13px;
            }
            """)

    def set_frame(self, frame: object) -> None:
        if frame is None:
            return

        try:
            import cv2  # pylint: disable=import-outside-toplevel

        except ModuleNotFoundError:
            return

        cv2_any: Any = cv2
        rgb_frame: Any = getattr(cv2_any, "cvtColor")(
            frame, getattr(cv2_any, "COLOR_BGR2RGB")
        )
        height: int
        width: int
        channels: int
        height, width, channels = rgb_frame.shape
        image: QImage = QImage(
            rgb_frame.data, width, height, channels * width, QImage.Format.Format_RGB888
        ).copy()
        self._current_pixmap = QPixmap.fromImage(image)
        self._apply_scaled_pixmap()

    def clear_preview(self, message: str = "No signal") -> None:
        self._current_pixmap = None
        self.setPixmap(QPixmap())
        self.setText(message)

    def resizeEvent(self, event: Any) -> None:
        super().resizeEvent(event)
        self._apply_scaled_pixmap()

    def _apply_scaled_pixmap(self) -> None:
        if self._current_pixmap is None:
            return

        scaled: QPixmap = self._current_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.setText("")
