"""
:mod:`cora.view.table`

This module implements a table (spreadsheet) view using Bokeh's 
:class:`~bokeh.models.DataTable` widget.
"""

from typing import List

import bokeh
import bokeh.models

from cora.application import Application
from cora.view.base import ViewBase
from cora.utils import data_columns


__all__ = [
    "TableView"
]


class TableView(ViewBase):
    """Displays a dataframe or a subset of the columns in 
    a standard spreadsheet view.
    """

    def __init__(self, app: Application):
        super().__init__(app)

        #: The columns to display.
        self.column_names: List[str] = []

        #: The Bokeh table widget displaying the columns.
        self.table: bokeh.models.DataTable = None

        # Init.
        self.update()
        return None

    def update(self):
        """Creates the table if not yet done and updates the set of colums (fields)
        that are shown.
        """
        cds = self.app.cds
        df = self.app.df
        
        # Update the column subset.
        column_names = self.column_names or data_columns(df)
        columns = [
            bokeh.models.TableColumn(field=column_name) \
            for column_name in column_names
        ]
        
        # Create the table if not yet done.
        self.table = bokeh.models.DataTable(
            source=cds, 
            columns=columns,
            sizing_mode="stretch_both"
        )
        self.layout_panel = self.table
        return None
    