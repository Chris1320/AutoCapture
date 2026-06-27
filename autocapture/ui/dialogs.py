from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from ..data.model import REQUIRED_COLUMN


class ColumnNameDialog(QDialog):
    def __init__(
        self,
        title: str,
        prompt: str,
        initial_value: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._name_edit = QLineEdit(initial_value)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(prompt))
        layout.addWidget(self._name_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._accept_if_valid)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _accept_if_valid(self) -> None:
        if not self.value():
            QMessageBox.warning(
                self, "Invalid column name", "Please enter a non-empty column name."
            )
            return
        self.accept()

    def value(self) -> str:
        return self._name_edit.text().strip()


class RowEditorDialog(QDialog):
    def __init__(
        self,
        columns: Sequence[str],
        values: Mapping[str, str] | None = None,
        *,
        allow_retake: bool = False,
        title: str = "Capture Details",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self._allow_retake = allow_retake
        self._retake_requested = False
        self._editors: dict[str, QLineEdit] = {}

        layout = QVBoxLayout(self)
        subtitle = QLabel("Review the text fields below before saving the capture.")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()
        for column in columns:
            editor = QLineEdit()
            editor.setText("" if values is None else str(values.get(column, "")))
            if column == REQUIRED_COLUMN:
                editor.setReadOnly(True)
                editor.setPlaceholderText("Automatically generated after capture")
            self._editors[column] = editor
            form.addRow(self._pretty_label(column), editor)
        layout.addLayout(form)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        save_button = button_box.button(QDialogButtonBox.StandardButton.Save)
        save_button.setText("Save")

        if allow_retake:
            retake_button = button_box.addButton(
                "Retake Photo", QDialogButtonBox.ButtonRole.ActionRole
            )
            retake_button.clicked.connect(self._request_retake)

        button_box.accepted.connect(self._accept_if_valid)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _pretty_label(self, column: str) -> str:
        return column.replace("_", " ").strip().title()

    def _request_retake(self) -> None:
        self._retake_requested = True
        self.accept()

    def _accept_if_valid(self) -> None:
        self.accept()

    def value_map(self) -> dict[str, str]:
        return {
            column: editor.text().strip() for column, editor in self._editors.items()
        }

    def retake_requested(self) -> bool:
        return self._retake_requested


class CaptureReviewDialog(QDialog):
    def __init__(
        self,
        image_path: str,
        summary_lines: Sequence[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Review Captured Photo")
        self._retake_requested = False

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        preview = QLabel()
        preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview.setMinimumSize(720, 420)
        preview.setWordWrap(True)
        preview.setStyleSheet(
            """
            QLabel {
                background: #101418;
                color: #ced8e3;
                border: 1px solid #2a3541;
                border-radius: 14px;
                padding: 12px;
            }
            """
        )

        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            preview.setText(f"Unable to load captured image:\n{image_path}")
        else:
            preview.setPixmap(
                pixmap.scaled(
                    preview.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            preview.setScaledContents(False)
        layout.addWidget(preview, 1)

        if summary_lines:
            summary = QLabel("\n".join(summary_lines))
            summary.setWordWrap(True)
            layout.addWidget(summary)

        button_box = QDialogButtonBox()
        accept_button = button_box.addButton(
            "Use Photo", QDialogButtonBox.ButtonRole.AcceptRole
        )
        reject_button = button_box.addButton(
            "Retake Photo", QDialogButtonBox.ButtonRole.DestructiveRole
        )
        cancel_button = button_box.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )

        accept_button.clicked.connect(self.accept)
        reject_button.clicked.connect(self._request_retake)
        cancel_button.clicked.connect(self.reject)
        layout.addWidget(button_box)

    def _request_retake(self) -> None:
        self._retake_requested = True
        self.accept()

    def retake_requested(self) -> bool:
        return self._retake_requested


class RemoveConfirmationDialog(QDialog):
    def __init__(self, summary: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Remove Capture")
        self._delete_file_checkbox = QCheckBox("Delete the image file from disk")
        self._delete_file_checkbox.setChecked(False)

        layout = QVBoxLayout(self)
        label = QLabel(f"Remove this record?\n\n{summary}")
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addWidget(self._delete_file_checkbox)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Yes | QDialogButtonBox.StandardButton.No
        )
        button_box.button(QDialogButtonBox.StandardButton.Yes).setText("Remove")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def delete_file_requested(self) -> bool:
        return self._delete_file_checkbox.isChecked()
