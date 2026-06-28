from __future__ import annotations

from pathlib import Path

import fastexcel
import polars as pl

from autocapture.data.export import export_capture_table


def test_export_creates_excel_file(tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    image_path = images_dir / "capture.jpg"
    frame = pl.DataFrame(
        {
            "image_path": [str(image_path)],
            "subject": ["Alice"],
        }
    )

    destination = tmp_path / "PSAutomater_Import.xlsx"
    export_capture_table(frame, destination)

    assert destination.exists()

    workbook = fastexcel.read_excel(destination)
    assert workbook.sheet_names == ["PSAutomater Import"]
    sheet = workbook.load_sheet_by_name("PSAutomater Import")
    result = sheet.to_polars()
    assert Path(result["image_path"][0]) == Path("images") / "capture.jpg"
