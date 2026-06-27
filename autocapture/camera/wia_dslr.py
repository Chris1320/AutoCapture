from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from loguru import logger

from .base import CameraUnavailableError, CaptureFailedError


class WiaCaptureSource:
    _jpeg_format_id = "{B96B3CAF-0728-11D3-9D7B-0000F81EF32E}"

    def __init__(self, device_name: str) -> None:
        self._device_name = device_name.strip()

    def capture(self, destination: Path) -> Path:
        if sys.platform != "win32":
            raise CameraUnavailableError("WIA capture is only available on Windows")

        try:
            from win32com.client import Dispatch
        except Exception as exc:  # pragma: no cover - runtime dependency guard
            raise CameraUnavailableError(
                "pywin32 is not available for WIA capture"
            ) from exc

        destination.parent.mkdir(parents=True, exist_ok=True)

        try:
            device = self._connect_device(Dispatch)
            item = self._first_item(device)
            transfer = self._transfer_item(Dispatch, item)
            self._save_transfer(transfer, destination)
            logger.debug("Saved WIA capture to {}", destination)
            return destination
        except CameraUnavailableError:
            raise
        except Exception as exc:
            logger.exception("WIA capture failed")
            raise CaptureFailedError(f"WIA capture failed: {exc}") from exc

    def _connect_device(self, dispatch: Any) -> Any:
        manager = dispatch("WIA.DeviceManager")
        device_infos = getattr(manager, "DeviceInfos", None)
        if device_infos is None:
            raise CameraUnavailableError(
                "WIA device manager did not expose any devices"
            )

        count = int(getattr(device_infos, "Count", 0))
        if count < 1:
            raise CameraUnavailableError("No WIA devices were found")

        selected = None
        for index in range(1, count + 1):
            info = device_infos.Item(index)
            if self._matches_device(info):
                selected = info
                break

        if selected is None:
            raise CameraUnavailableError(
                f"Unable to find WIA device matching '{self._device_name}'"
            )

        return selected.Connect()

    def _matches_device(self, device_info: Any) -> bool:
        if not self._device_name:
            return True
        try:
            properties = device_info.Properties
            name = str(properties("Name").Value)
        except OSError:
            try:
                name = str(device_info.Properties.Item("Name").Value)
            except OSError:
                name = ""
        return self._device_name.casefold() in name.casefold()

    def _first_item(self, device: Any) -> Any:
        items = getattr(device, "Items", None)
        if items is None:
            raise CaptureFailedError("WIA device did not expose any capture items")
        count = int(getattr(items, "Count", 0))
        if count < 1:
            raise CaptureFailedError("WIA device has no available items to transfer")
        return items.Item(1)

    def _transfer_item(self, dispatch: Any, item: Any) -> Any:
        dialog = dispatch("WIA.CommonDialog")
        transfer = getattr(dialog, "ShowTransfer", None)
        if transfer is None:
            raise CaptureFailedError("WIA common dialog does not support transfer")

        try:
            return transfer(item, self._jpeg_format_id)
        except TypeError:
            return transfer(item)

    def _save_transfer(self, image_file: Any, destination: Path) -> None:
        save_file = getattr(image_file, "SaveFile", None)
        if save_file is None:
            raise CaptureFailedError("WIA transfer did not return a savable image")
        save_file(str(destination))
