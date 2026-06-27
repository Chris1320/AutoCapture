from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import polars as pl
from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt

REQUIRED_COLUMN = "image_path"


def _empty_frame(columns: Sequence[str]) -> pl.DataFrame:
    if not columns:
        return pl.DataFrame(schema={REQUIRED_COLUMN: pl.Utf8})
    return pl.DataFrame(schema={column: pl.Utf8 for column in columns})


def _frame_from_rows(
    rows: list[dict[str, Any]], columns: Sequence[str]
) -> pl.DataFrame:
    if not rows:
        return _empty_frame(columns)

    normalized_rows: list[dict[str, str]] = []
    for row in rows:
        normalized_row = {
            column: "" if row.get(column) is None else str(row.get(column, ""))
            for column in columns
        }
        normalized_rows.append(normalized_row)
    return pl.DataFrame(normalized_rows, schema={column: pl.Utf8 for column in columns})


class CaptureTableModel(QAbstractTableModel):
    def __init__(self, frame: pl.DataFrame | None = None, parent: Any = None) -> None:
        super().__init__(parent)
        self._frame = self._normalize_frame(frame or _empty_frame([REQUIRED_COLUMN]))

    @property
    def frame(self) -> pl.DataFrame:
        return self._frame

    @property
    def columns(self) -> list[str]:
        return list(self._frame.columns)

    def _normalize_frame(self, frame: pl.DataFrame) -> pl.DataFrame:
        columns = list(frame.columns)
        if REQUIRED_COLUMN not in columns:
            columns.insert(0, REQUIRED_COLUMN)
        ordered_columns = [REQUIRED_COLUMN] + [
            column for column in columns if column != REQUIRED_COLUMN
        ]
        if frame.is_empty():
            return _empty_frame(ordered_columns)
        return _frame_from_rows(frame.to_dicts(), ordered_columns)

    def _replace_frame(self, frame: pl.DataFrame) -> None:
        self.beginResetModel()
        self._frame = self._normalize_frame(frame)
        self.endResetModel()

    def rowCount(
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        if parent.isValid():
            return 0
        return self._frame.height

    def columnCount(
        self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()
    ) -> int:
        if parent.isValid():
            return 0
        return self._frame.width

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or role not in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            return None
        value = self._frame.item(index.row(), index.column())
        return "" if value is None else str(value)

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._frame.columns[section]
        return section + 1

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        column_name = self._frame.columns[index.column()]
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if column_name != REQUIRED_COLUMN:
            flags |= Qt.ItemFlag.ItemIsEditable
        return flags

    def setData(
        self,
        index: QModelIndex | QPersistentModelIndex,
        value: Any,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        column_name = self._frame.columns[index.column()]
        if column_name == REQUIRED_COLUMN:
            return False
        rows = self._frame.to_dicts()
        rows[index.row()][column_name] = "" if value is None else str(value)
        self._replace_frame(_frame_from_rows(rows, self._frame.columns))
        return True

    def row_dict(self, row: int) -> dict[str, str]:
        rows = self._frame.to_dicts()
        if row < 0 or row >= len(rows):
            raise IndexError(row)
        return {
            column: "" if value is None else str(value)
            for column, value in rows[row].items()
        }

    def insert_row(self, values: Mapping[str, Any]) -> None:
        rows = self._frame.to_dicts()
        row = {
            column: "" if values.get(column) is None else str(values.get(column, ""))
            for column in self._frame.columns
        }
        rows.append(row)
        self._replace_frame(_frame_from_rows(rows, self._frame.columns))

    def update_row(self, row_index: int, values: Mapping[str, Any]) -> None:
        rows = self._frame.to_dicts()
        if row_index < 0 or row_index >= len(rows):
            raise IndexError(row_index)
        for column in self._frame.columns:
            if column in values:
                rows[row_index][column] = (
                    "" if values[column] is None else str(values[column])
                )
        self._replace_frame(_frame_from_rows(rows, self._frame.columns))

    def remove_row(self, row_index: int) -> None:
        rows = self._frame.to_dicts()
        if row_index < 0 or row_index >= len(rows):
            raise IndexError(row_index)
        del rows[row_index]
        self._replace_frame(_frame_from_rows(rows, self._frame.columns))

    def add_column(self, column_name: str, default_value: str = "") -> None:
        normalized_name = column_name.strip()
        if not normalized_name:
            raise ValueError("Column name cannot be empty")
        if normalized_name in self._frame.columns:
            raise ValueError(f"Column already exists: {normalized_name}")
        rows = self._frame.to_dicts()
        for row in rows:
            row[normalized_name] = default_value
        self._replace_frame(
            _frame_from_rows(rows, [*self._frame.columns, normalized_name])
        )

    def rename_column(self, old_name: str, new_name: str) -> None:
        normalized_name = new_name.strip()
        if not normalized_name:
            raise ValueError("Column name cannot be empty")
        if old_name == REQUIRED_COLUMN:
            raise ValueError(f"{REQUIRED_COLUMN} cannot be renamed")
        if normalized_name in self._frame.columns and normalized_name != old_name:
            raise ValueError(f"Column already exists: {normalized_name}")
        rows = self._frame.to_dicts()
        for row in rows:
            row[normalized_name] = row.pop(old_name, "")
        columns = [
            normalized_name if column == old_name else column
            for column in self._frame.columns
        ]
        self._replace_frame(_frame_from_rows(rows, columns))

    def remove_column(self, column_name: str) -> None:
        if column_name == REQUIRED_COLUMN:
            raise ValueError(f"{REQUIRED_COLUMN} cannot be removed")
        if column_name not in self._frame.columns:
            raise ValueError(f"Unknown column: {column_name}")
        rows = self._frame.to_dicts()
        for row in rows:
            row.pop(column_name, None)
        columns = [column for column in self._frame.columns if column != column_name]
        self._replace_frame(_frame_from_rows(rows, columns))

    def replace_frame(self, frame: pl.DataFrame) -> None:
        self._replace_frame(frame)
