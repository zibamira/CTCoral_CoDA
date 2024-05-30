"""
:mod:`coda.view.table`

This module implements a table (spreadsheet) view using Bokeh's 
:class:`~bokeh.models.DataTable` widget.
"""

from typing import List

import bokeh
import bokeh.models

from coda.application import Application
from coda.view.base import ViewBase
from coda.utils import data_columns


__all__ = [
    "TableView"
]


class TableView(ViewBase):
    """Displays a dataframe or a subset of the columns in a standard spreadsheet 
    view. The user can select which columns they want to display.
    """

    def __init__(self, app: Application):
        super().__init__(app)

        #: The columns to display.
        self.ui_multichoice_columns = bokeh.models.MultiChoice(
            title="Columns",
            sizing_mode="stretch_width"
        )
        self.ui_multichoice_columns.on_change(
            "value", self.on_multichoice_columns_change
        )

        #: The Bokeh table widget displaying the columns.
        self.table: bokeh.models.DataTable = None

        # Layout.
        self.layout_sidebar.children = [
            self.ui_multichoice_columns
        ]
        return None
    
    def reload_df(self):
        """Update the available columns to display in the spreadsheet."""
        # Filter out columns that are not present anymore in the dataframe.
        columns = data_columns(self.app.df)
        selection = self.ui_multichoice_columns.value
        selection = [column for column in selection if column in columns]

        self.ui_multichoice_columns.options = columns
        self.ui_multichoice_columns.value = selection
        return None

    def reload_cds(self):
        """Reload the selected columns."""
        if self.table is None:
            self.create_table()
        else:
            self.update_columns()
        return None    

    def on_multichoice_columns_change(self, attr, old, new):
        """The user changed the subset of columns to display."""
        if self.is_reloading:
            return None
        self.update_columns()
        return None

    def create_table(self):
        """Creates the spreadsheet table view."""
        self.table = bokeh.models.DataTable(
            source=self.app.cds, 
            columns=self.ui_multichoice_columns.value,
            sizing_mode="stretch_both"
        )
        self.layout_panel = self.table
        return None
    
    def update_columns(self):
        """Changes the subset of displayed column in the table widget."""        
        columns = self.ui_multichoice_columns.value
        columns = [bokeh.models.TableColumn(field=column) for column in columns]
        self.table.columns = columns
        return None
    