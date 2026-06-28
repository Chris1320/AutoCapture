from __future__ import annotations

import os
from pathlib import Path

import polars as pl

from .model import REQUIRED_COLUMN


def _relative_image_path(image_path: str, base_dir: Path) -> str:
    if not image_path:
        return image_path

    path: Path = Path(image_path)
    if not path.is_absolute():
        return image_path

    try:
        return os.path.relpath(path, start=base_dir)

    except ValueError:
        return image_path


def _ordered_frame(frame: pl.DataFrame) -> pl.DataFrame:
    columns: list[str] = list(frame.columns)
    if REQUIRED_COLUMN in columns:
        ordered_columns: list[str] = [REQUIRED_COLUMN] + [
            column for column in columns if column != REQUIRED_COLUMN
        ]

    else:
        ordered_columns = [REQUIRED_COLUMN] + columns
        frame = frame.with_columns(pl.lit("").alias(REQUIRED_COLUMN))

    if not ordered_columns:
        return frame

    return frame.select(ordered_columns)


def _frame_relative_to_destination(
    frame: pl.DataFrame, destination: Path
) -> pl.DataFrame:
    return frame.with_columns(
        pl.col(REQUIRED_COLUMN)
        .cast(pl.Utf8)
        .map_elements(
            lambda value: _relative_image_path(value, destination.parent),
            return_dtype=pl.Utf8,
        )
    )


def export_capture_table(frame: pl.DataFrame, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ordered: pl.DataFrame = _frame_relative_to_destination(
        _ordered_frame(frame), destination
    )

    ordered.write_excel(
        workbook=destination,
        worksheet="Masterlist",
        table_style="Table Style Medium 2",
        include_header=True,
        autofilter=True,
        autofit=True,
        freeze_panes=(1, 0),
        hide_gridlines=True,
        sheet_zoom=110,
    )

    return destination
