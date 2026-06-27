from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

from loguru import logger
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog

from .camera import CameraService
from .config import app_logs_dir, load_config
from .data import CaptureTableModel
from .logging_setup import configure_logging
from .storage import CaptureStorage
from .ui import MainWindow


def build_application() -> QApplication:
    application = QApplication.instance()
    if application is not None:
        return cast(QApplication, application)

    qt_application = QApplication(sys.argv)
    qt_application.setApplicationName("AutoCapture")
    qt_application.setOrganizationName("AutoCapture")
    qt_application.setStyle("Fusion")
    return qt_application


def choose_output_root() -> Path | None:
    selected_parent = QFileDialog.getExistingDirectory(
        None,
        "Select where to create the AutoCapture folder",
        str(Path.home()),
    )
    if not selected_parent:
        return None

    folder_name, accepted = QInputDialog.getText(
        None,
        "AutoCapture Folder Name",
        "Enter the name of the folder to create:",
    )
    if not accepted:
        return None

    normalized_name = folder_name.strip()
    if not normalized_name:
        return None

    return Path(selected_parent) / normalized_name


def main() -> int:
    application = build_application()
    selected_root = choose_output_root()
    if selected_root is None:
        return 0

    config = load_config(selected_root)
    storage = CaptureStorage(config.output_root)
    storage.ensure_layout()
    configure_logging(app_logs_dir())

    logger.info("Starting AutoCapture")

    model = CaptureTableModel()
    camera_service = CameraService(config)
    window = MainWindow(config, storage, camera_service, model)
    window.show()

    return application.exec()
