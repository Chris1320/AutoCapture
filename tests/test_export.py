from __future__ import annotations

from pathlib import Path

import fastexcel
import polars as pl

from autocapture.data.export import export_capture_table


def test_export_creates_excel_file(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "image_path": [str(tmp_path / "images" / "capture.jpg")],
            "subject": ["Alice"],
        }
    )

    destination = tmp_path / "PSAutomater_Import.xlsx"
    export_capture_table(frame, destination)

    assert destination.exists()

    workbook = fastexcel.read_excel(destination)
    assert workbook.sheet_names == ["PSAutomater Import"]
