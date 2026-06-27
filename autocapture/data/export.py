from __future__ import annotations

from pathlib import Path

import polars as pl

from .model import REQUIRED_COLUMN


def _ordered_frame(frame: pl.DataFrame) -> pl.DataFrame:
    columns = list(frame.columns)
    if REQUIRED_COLUMN in columns:
        ordered_columns = [REQUIRED_COLUMN] + [
            column for column in columns if column != REQUIRED_COLUMN
        ]
    else:
        ordered_columns = [REQUIRED_COLUMN] + columns
        frame = frame.with_columns(pl.lit("").alias(REQUIRED_COLUMN))
    if not ordered_columns:
        return frame
    return frame.select(ordered_columns)


def export_capture_table(frame: pl.DataFrame, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    ordered = _ordered_frame(frame)

    ordered.write_excel(
        workbook=destination,
        worksheet="PSAutomater Import",
        table_style="Table Style Medium 2",
        include_header=True,
        autofilter=True,
        autofit=True,
        freeze_panes=(1, 0),
        hide_gridlines=True,
        sheet_zoom=110,
    )

    return destination
