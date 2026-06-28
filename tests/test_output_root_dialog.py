from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from autocapture.ui.dialogs import OutputRootDialog


def _ensure_app() -> QApplication:
    application = QApplication.instance()
    if application is not None:
        return application
    return QApplication([])


def test_output_root_dialog_combines_parent_and_folder_name(monkeypatch, tmp_path: Path) -> None:
    _ensure_app()
    selected_parent = tmp_path / "captures"
    selected_parent.mkdir()

    monkeypatch.setattr(
        "autocapture.ui.dialogs.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(selected_parent),
    )

    dialog = OutputRootDialog(initial_parent=tmp_path, initial_folder_name="Session")
    dialog._browse_for_parent_folder()
    dialog._folder_name_edit.setText("Project")

    assert dialog.folder_name() == "Project"
    assert dialog.output_root() == selected_parent / "Project"