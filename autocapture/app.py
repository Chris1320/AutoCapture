from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from loguru import logger
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from .camera import CameraService
from .config import AppConfig, app_logs_dir, load_config
from .data import CaptureTableModel
from .logging import configure_logging
from .storage import CaptureStorage
from .ui import MainWindow, OutputRootDialog


def build_application() -> QCoreApplication:
    application: QCoreApplication | None = QApplication.instance()
    if application is not None:
        return cast(QApplication, application)

    qt_application: QApplication = QApplication(sys.argv)
    qt_application.setApplicationName("AutoCapture")
    qt_application.setOrganizationName("AutoCapture")
    qt_application.setStyle("Fusion")
    return qt_application


def choose_output_root() -> Path | None:
    dialog = OutputRootDialog()
    if dialog.exec() != OutputRootDialog.DialogCode.Accepted:
        return None

    return dialog.output_root()


def main() -> int:
    application: QCoreApplication = build_application()
    selected_root: Path | None = choose_output_root()
    if selected_root is None:
        return 0

    config: AppConfig = load_config(selected_root)
    storage: CaptureStorage = CaptureStorage(config.output_root)
    storage.ensure_layout()
    configure_logging(app_logs_dir())

    logger.info("Starting AutoCapture")

    model: CaptureTableModel = CaptureTableModel()
    camera_service: CameraService = CameraService(config)
    window: MainWindow = MainWindow(config, storage, camera_service, model)
    window.show()

    return application.exec()
