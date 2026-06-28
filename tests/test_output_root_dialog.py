from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from autocapture.ui.dialogs import OutputRootDialog


def _ensure_app() -> QCoreApplication:
    application = QApplication.instance()
    if application is not None:
        return application

    return QApplication([])


def test_output_root_dialog_combines_parent_and_folder_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _ensure_app()
    selected_parent = tmp_path / "captures"
    selected_parent.mkdir()

    def mock_get_existing_directory(*_args: Any, **_kwargs: Any) -> str:
        return str(selected_parent)

    monkeypatch.setattr(
        "autocapture.ui.dialogs.QFileDialog.getExistingDirectory",
        mock_get_existing_directory,
    )

    dialog = OutputRootDialog(initial_parent=tmp_path, initial_folder_name="Session")
    dialog.browse_for_parent_folder()
    dialog.set_folder_name("Project")

    assert dialog.folder_name() == "Project"
    assert dialog.output_root() == selected_parent / "Project"
