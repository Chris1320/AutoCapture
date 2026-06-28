from __future__ import annotations

from pathlib import Path
from typing import cast

import fastexcel
import polars as pl

from autocapture.data.export import export_capture_table
from autocapture.data.model import REQUIRED_COLUMN


def test_export_creates_excel_file(tmp_path: Path) -> None:
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    image_path = images_dir / "capture.jpg"
    frame = pl.DataFrame(
        {
            REQUIRED_COLUMN: [str(image_path)],
            "subject": ["Alice"],
        }
    )

    destination = tmp_path / "Masterlist.xlsx"
    export_capture_table(frame, destination)

    assert destination.exists()

    workbook = fastexcel.read_excel(destination)
    assert workbook.sheet_names == ["Masterlist"]
    sheet = workbook.load_sheet_by_name("Masterlist")
    exported_rows = cast(list[dict[str, str]], sheet.to_polars().to_dicts())
    assert Path(exported_rows[0][REQUIRED_COLUMN]) == Path("images") / "capture.jpg"
