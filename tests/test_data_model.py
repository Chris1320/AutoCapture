from __future__ import annotations

import polars as pl

from autocapture.data.model import REQUIRED_COLUMN, CaptureTableModel


def test_required_column_is_present_and_fixed() -> None:
    model = CaptureTableModel()

    assert model.columns == [REQUIRED_COLUMN]

    try:
        model.rename_column(REQUIRED_COLUMN, "other")
    except ValueError as exc:
        assert REQUIRED_COLUMN in str(exc)
    else:
        raise AssertionError("expected rename to fail")

    try:
        model.remove_column(REQUIRED_COLUMN)
    except ValueError as exc:
        assert REQUIRED_COLUMN in str(exc)
    else:
        raise AssertionError("expected removal to fail")


def test_row_and_column_mutations() -> None:
    model = CaptureTableModel()
    model.add_column("subject")
    model.insert_row({REQUIRED_COLUMN: "image.jpg", "subject": "Alice"})

    assert model.rowCount() == 1
    assert model.columnCount() == 2
    assert model.row_dict(0)["subject"] == "Alice"

    model.update_row(0, {"subject": "Bob"})
    assert model.row_dict(0)["subject"] == "Bob"

    model.rename_column("subject", "name")
    assert model.columns == [REQUIRED_COLUMN, "name"]
    assert model.row_dict(0)["name"] == "Bob"

    model.remove_column("name")
    assert model.columns == [REQUIRED_COLUMN]
    assert model.rowCount() == 1
