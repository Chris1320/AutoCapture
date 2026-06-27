from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from ..camera.base import CaptureResult
from ..camera.service import CameraService
from ..config import AppConfig, CameraMode
from ..data.export import export_capture_table
from ..data.model import REQUIRED_COLUMN, CaptureTableModel
from ..storage import CaptureStorage
from .dialogs import (
    CaptureReviewDialog,
    ColumnNameDialog,
    RemoveConfirmationDialog,
    RowEditorDialog,
)
from .widgets import VideoPreviewWidget


@dataclass(slots=True)
class PendingCapture:
    kind: str
    row_index: int | None
    values: dict[str, str]
    destination: Path


class CaptureTableView(QTableView):
    add_column_requested = Signal()
    rename_column_requested = Signal(str)
    remove_column_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.horizontalHeader().setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self.horizontalHeader().customContextMenuRequested.connect(
            self._show_header_menu
        )
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setWordWrap(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )

    def selected_row(self) -> int | None:
        indexes = self.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].row()

    def _show_header_menu(self, position: QPoint) -> None:
        header = self.horizontalHeader()
        section = header.logicalIndexAt(position)
        menu = QMenu(self)
        add_action = menu.addAction("Add text column")
        rename_action = menu.addAction("Rename column")
        remove_action = menu.addAction("Remove column")
        chosen = menu.exec(header.mapToGlobal(position))

        if chosen == add_action:
            self.add_column_requested.emit()
            return
        if section < 0:
            return

        model = self.model()
        column_name = str(
            model.headerData(
                section, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole
            )
        )
        if chosen == rename_action:
            self.rename_column_requested.emit(column_name)
        elif chosen == remove_action:
            self.remove_column_requested.emit(column_name)


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        storage: CaptureStorage,
        camera_service: CameraService,
        table_model: CaptureTableModel,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._storage = storage
        self._camera_service = camera_service
        self._model = table_model
        self._pending_capture: PendingCapture | None = None
        self._busy = False

        self.setWindowTitle("AutoCapture")
        self.resize(1440, 900)
        self.setMinimumSize(1200, 760)

        self._preview_widget = VideoPreviewWidget()
        self._mode_combo = QComboBox()
        self._mode_combo.addItem(CameraMode.WEBCAM.label, CameraMode.WEBCAM)
        self._mode_combo.addItem(CameraMode.DSLR_WIA.label, CameraMode.DSLR_WIA)
        self._mode_combo.currentIndexChanged.connect(self._handle_mode_changed)

        self._table_view = CaptureTableView()
        self._table_view.setModel(self._model)
        self._table_view.add_column_requested.connect(self._add_column)
        self._table_view.rename_column_requested.connect(self._rename_column)
        self._table_view.remove_column_requested.connect(self._remove_column)

        self._add_button = QPushButton("Add")
        self._edit_button = QPushButton("Edit")
        self._remove_button = QPushButton("Remove")
        self._done_button = QPushButton("Done")
        self._buttons = [
            self._add_button,
            self._edit_button,
            self._remove_button,
            self._done_button,
        ]
        self._add_button.clicked.connect(self._add_capture)
        self._edit_button.clicked.connect(self._edit_capture)
        self._remove_button.clicked.connect(self._remove_capture)
        self._done_button.clicked.connect(self._finish_and_export)

        self._status_label = QLabel("Ready")
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.addPermanentWidget(self._status_label, 1)

        self._build_layout()
        self._apply_style()
        self._wire_camera_service()
        self._mode_combo.setCurrentIndex(
            0 if config.default_mode == CameraMode.WEBCAM else 1
        )
        self._camera_service.start_preview(self.current_mode())

    def current_mode(self) -> CameraMode:
        data = self._mode_combo.currentData()
        if isinstance(data, CameraMode):
            return data
        return CameraMode(str(data))

    def _build_layout(self) -> None:
        root = QWidget(self)
        main_layout = QVBoxLayout(root)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = self._build_left_panel()
        right_panel = self._build_right_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        action_bar = self._build_action_bar()
        main_layout.addWidget(splitter, 1)
        main_layout.addWidget(action_bar, 0)
        self.setCentralWidget(root)

    def _build_left_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Camera Source"))
        header_row.addWidget(self._mode_combo, 1)
        layout.addLayout(header_row)
        layout.addWidget(self._preview_widget, 1)
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        title = QLabel("Capture Data")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        layout.addWidget(self._table_view, 1)
        return panel

    def _build_action_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("actionBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        for button in self._buttons:
            button.setMinimumHeight(42)
            layout.addWidget(button)
        layout.addStretch(1)
        return bar

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow {
                background: #0f141a;
                color: #ecf2f8;
            }
            QFrame#card {
                background: #161c24;
                border: 1px solid #273241;
                border-radius: 16px;
                padding: 12px;
            }
            QFrame#actionBar {
                background: #141a22;
                border: 1px solid #273241;
                border-radius: 16px;
            }
            QLabel {
                color: #ecf2f8;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 700;
            }
            QComboBox, QLineEdit, QTableView {
                background: #0f141a;
                color: #ecf2f8;
                border: 1px solid #2f3b4b;
                border-radius: 10px;
                padding: 8px 10px;
                selection-background-color: #2563eb;
            }
            QTableView::item:selected {
                background: #1d4ed8;
                color: white;
            }
            QPushButton {
                background: #1f2937;
                color: #eff6ff;
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 10px 16px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #334155;
            }
            QPushButton:disabled {
                background: #111827;
                color: #64748b;
            }
            QStatusBar {
                background: transparent;
                color: #cbd5e1;
            }
            """)

    def _wire_camera_service(self) -> None:
        self._camera_service.preview_frame_received.connect(
            self._preview_widget.set_frame
        )
        self._camera_service.preview_status_changed.connect(self._status_label.setText)
        self._camera_service.status_changed.connect(self._status_label.setText)
        self._camera_service.capture_completed.connect(self._handle_capture_completed)
        self._camera_service.capture_failed.connect(self._handle_capture_failed)

    def _handle_mode_changed(self, _index: int) -> None:
        if self._busy:
            return
        self._status_label.setText(f"Switching to {self.current_mode().label}")
        self._camera_service.start_preview(self.current_mode())

    def _add_column(self) -> None:
        dialog = ColumnNameDialog(
            "Add Column", "Enter the new text column name:", parent=self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._model.add_column(dialog.value())
        except (IndexError, OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "Column error", str(exc))

    def _rename_column(self, column_name: str) -> None:
        if column_name == REQUIRED_COLUMN:
            QMessageBox.warning(
                self, "Column error", f"{REQUIRED_COLUMN} cannot be renamed."
            )
            return
        dialog = ColumnNameDialog(
            "Rename Column", f"Rename '{column_name}' to:", column_name, self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._model.rename_column(column_name, dialog.value())
        except (IndexError, OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "Column error", str(exc))

    def _remove_column(self, column_name: str) -> None:
        if column_name == REQUIRED_COLUMN:
            QMessageBox.warning(
                self, "Column error", f"{REQUIRED_COLUMN} cannot be removed."
            )
            return
        try:
            self._model.remove_column(column_name)
        except (IndexError, OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "Column error", str(exc))

    def _add_capture(self) -> None:
        if self._busy:
            return
        values = {column: "" for column in self._model.columns}
        dialog = RowEditorDialog(
            self._model.columns,
            values=values,
            allow_retake=False,
            title="Add Capture",
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        edited_values = dialog.value_map()
        destination = self._storage.build_image_path(
            extension=self._config.image_extension
        )
        self._pending_capture = PendingCapture("add", None, edited_values, destination)
        if not self._camera_service.capture_still(destination, metadata=edited_values):
            self._pending_capture = None
            QMessageBox.warning(
                self, "Capture busy", "A capture is already in progress."
            )
            return
        self._set_busy(True, "Capturing new image...")

    def _edit_capture(self) -> None:
        if self._busy:
            return
        row_index = self._selected_row_index()
        if row_index is None:
            QMessageBox.information(
                self, "Select a row", "Please select a row to edit."
            )
            return

        current_values = self._model.row_dict(row_index)
        dialog = RowEditorDialog(
            self._model.columns,
            values=current_values,
            allow_retake=True,
            title="Edit Capture",
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        updated_values = dialog.value_map()
        if dialog.retake_requested():
            destination = Path(current_values[REQUIRED_COLUMN])
            self._pending_capture = PendingCapture(
                "edit", row_index, updated_values, destination
            )
            if not self._camera_service.capture_still(
                destination, metadata=updated_values
            ):
                self._pending_capture = None
                QMessageBox.warning(
                    self, "Capture busy", "A capture is already in progress."
                )
                return
            self._set_busy(True, "Retaking image...")
            return

        try:
            self._model.update_row(
                row_index,
                {
                    key: value
                    for key, value in updated_values.items()
                    if key != REQUIRED_COLUMN
                },
            )
        except (IndexError, OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "Edit failed", str(exc))

    def _remove_capture(self) -> None:
        if self._busy:
            return
        row_index = self._selected_row_index()
        if row_index is None:
            QMessageBox.information(
                self, "Select a row", "Please select a row to remove."
            )
            return

        row_values = self._model.row_dict(row_index)
        dialog = RemoveConfirmationDialog(row_values.get(REQUIRED_COLUMN, ""), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        if dialog.delete_file_requested():
            self._storage.delete_file(Path(row_values[REQUIRED_COLUMN]))
        try:
            self._model.remove_row(row_index)
        except (IndexError, OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "Remove failed", str(exc))

    def _finish_and_export(self) -> None:
        if self._busy:
            return
        try:
            export_path = export_capture_table(
                self._model.frame, self._config.export_path
            )
        except (IndexError, OSError, RuntimeError, ValueError) as exc:
            logger.exception("Export failed")
            QMessageBox.warning(self, "Export failed", str(exc))
            return

        QMessageBox.information(
            self, "Export complete", f"Exported spreadsheet:\n{export_path}"
        )
        self._status_label.setText(f"Exported to {export_path}")

    def _handle_capture_completed(self, result: object) -> None:
        self._set_busy(False, "Capture complete")
        if not isinstance(result, CaptureResult):
            logger.warning("Unexpected capture result: {}", type(result))
            self._pending_capture = None
            return

        pending = self._pending_capture
        if pending is None:
            return

        if pending.kind == "add":
            review = CaptureReviewDialog(
                str(result.image_path),
                summary_lines=[f"Image: {result.image_path}"]
                + [f"{key}: {value}" for key, value in pending.values.items() if value],
                parent=self,
            )
            if review.exec() != QDialog.DialogCode.Accepted:
                self._storage.delete_file(result.image_path)
                self._pending_capture = None
                return

            if review.retake_requested():
                if not self._camera_service.capture_still(
                    pending.destination, metadata=pending.values
                ):
                    self._pending_capture = None
                    QMessageBox.warning(
                        self, "Capture busy", "A capture is already in progress."
                    )
                    return
                self._set_busy(True, "Retaking image...")
                return

            self._pending_capture = None
            row_data = dict(pending.values)
            row_data[REQUIRED_COLUMN] = str(result.image_path)
            try:
                self._model.insert_row(row_data)
            except (IndexError, OSError, RuntimeError, ValueError) as exc:
                QMessageBox.warning(self, "Data update failed", str(exc))
            return

        self._pending_capture = None

        row_data = dict(pending.values)
        row_data[REQUIRED_COLUMN] = str(result.image_path)

        try:
            if pending.kind == "add":
                self._model.insert_row(row_data)
            elif pending.kind == "edit" and pending.row_index is not None:
                self._model.update_row(pending.row_index, row_data)
        except (IndexError, OSError, RuntimeError, ValueError) as exc:
            QMessageBox.warning(self, "Data update failed", str(exc))

    def _handle_capture_failed(self, message: str) -> None:
        self._pending_capture = None
        self._set_busy(False, "Capture failed")
        QMessageBox.warning(self, "Capture failed", message)

    def _selected_row_index(self) -> int | None:
        return self._table_view.selected_row()

    def _set_busy(self, busy: bool, status: str) -> None:
        self._busy = busy
        for button in self._buttons:
            button.setDisabled(busy)
        self._mode_combo.setDisabled(busy)
        self._status_label.setText(status)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._camera_service.shutdown()
        super().closeEvent(event)
