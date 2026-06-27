from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class CameraMode(StrEnum):
    WEBCAM = "webcam"
    DSLR_WIA = "wia"

    @property
    def label(self) -> str:
        if self is CameraMode.WEBCAM:
            return "Webcam/Capture Card"
        return "DSLR via WIA"


@dataclass(slots=True, frozen=True)
class AppConfig:
    output_root: Path
    webcam_preview_device_index: int = 0
    capture_card_preview_device_index: int = 1
    wia_device_name: str = ""
    default_mode: CameraMode = CameraMode.WEBCAM
    preview_fps: int = 30
    image_extension: str = ".jpg"
    export_filename: str = "PSAutomater_Import.xlsx"
    log_filename: str = "autocapture.log"

    @property
    def images_dir(self) -> Path:
        return self.output_root / "images"

    @property
    def export_path(self) -> Path:
        return self.output_root / self.export_filename


def app_data_root() -> Path:
    return Path(__file__).resolve().parents[1] / "data"


def app_logs_dir() -> Path:
    return app_data_root() / "logs"


def default_output_root() -> Path | None:
    override = os.getenv("AUTOCAPTURE_ROOT")
    if override:
        return Path(override).expanduser()
    return None


def load_config(output_root: Path) -> AppConfig:
    return AppConfig(output_root=output_root)
