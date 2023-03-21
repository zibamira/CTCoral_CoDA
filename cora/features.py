"""
:mod:`features`

This module implements the SPLOM plots for the features and tabel views.
"""


import logging
import pathlib
from pprint import pprint
from typing import List

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

import pandas as pd
import numpy as np

from splom import splom as SplomPlot


__all__ = [
    "splom",
    "table"
]


def selection_callback(attr, old, new):
    """Called when the user selection changes."""
    print("callback")
    # print("  attr", attr)
    # print("  old ", old)
    # print("  new ", new)
    # if _last_update is None or time.time() - _last_update > 1:
    #     print("Write")
    #     mask = np.isin(ipc_segmentation.array, new, assume_unique=True)
    #     ipc_selection.array[:] = mask.astype("u8")
    #     ipc_selection.ipc_write()
    #     _last_update = time.time()
    return None


def splom(
    df: pd.DataFrame,
    source: bokeh.models.ColumnDataSource,
    columns: List[str]
    ):
    """Shows a scatterplot matrix (SPLOM) for the selected
    raw features of the :data:`ipc_features` spreadsheet.
    """
    p = SplomPlot(df, source, columns, "label")
    return p


def table(
    df: pd.DataFrame,
    source: bokeh.models.ColumnDataSource,
    columns: List[str]
    ):
    """Shows the :data:`ipc_spreadsheet` raw features as a spreadsheet.
    Only the columns which are currently selected by the user are displayed.
    """
    # Create a column for each feature.
    table_columns = [
        bokeh.models.TableColumn(field=name, title=name) for name in columns
    ]
    table = bokeh.models.DataTable(
        source=source, columns=table_columns, sizing_mode="stretch_both",
        selectable=True, sortable=True, syncable=True,
        scroll_to_selection=True, reorderable=True
    )
    return table