"""
:mod:`cora.view.statistics`

This module provides a table with statistics of the current selection.
"""

from typing import List

import bokeh
import bokeh.models

from cora.application import Application
from cora.view.base import ViewBase
import cora.utils


__all__ = [
    "StatisticsView"
]


class StatisticsView(ViewBase):
    """Displays statistics of the current selection within a dataframe.
    The statistics are shown in a spreadsheet (tablewidget).
    """

    def __init__(self, app: Application):
        super().__init__(app)

        #: The Bokeh table widget displaying the statistics.
        self.table: bokeh.models.DataTable = None

        #: The Bokeh ColumnDataSource that contains the aggregated statistics.
        #: This ColumnDataSource is the *source* of :attr:`table`.
        self.cds_stats: bokeh.models.ColumnDataSource = None

        # Layout.
        self.layout_sidebar.children = []

        # Update the statistics whenenver the column data source changes.
        self.app.cds.selected.on_change("indices", self.on_cds_selection_change)
        return None
    
    def reload_df(self):
        """Update the available columns to display in the spreadsheet."""
        self.update_statistics()
        return None

    def reload_cds(self):
        """Reload the selected columns."""
        self.update_statistics()
        return None    

    def on_cds_selection_change(self, attr, old, new):
        """Update the statistics when the current selection changed."""
        self.update_statistics()
        return None

    def update_statistics(self):
        """Computes the statistics of all (scalar) columns in the dataframe.
        Only the current selection is considered when computing the statistics.
        """
        # Only compute statistics for scalar columns.
        data_columns = cora.utils.scalar_columns(self.app.df)
        df = self.app.df[data_columns]

        # Only compute the statistics for the current selection.
        selection = self.app.cds.selected.indices
        if selection:
            df = df.iloc[selection]

        # Compute the statistics and transpose the dataframe,
        # so that each row contains the statistics for a column in the original 
        # dataframe.
        # I think thats easiert to read, especially when the number of columns
        # is large (it's easier to scroll vertically than horizontally).
        desc = df.describe()
        desc = desc.transpose()
        desc.index.name = "column"

        # Update the table widget source and the widget itself.
        self.cds_stats = bokeh.models.ColumnDataSource(desc)
        self.cds_stats.data["unique"] = df.nunique()
        
        if self.table is None:
            self.create_table()
        self.table.source = self.cds_stats
        return None

    def create_table(self):
        """Creates the table that displays the aggregated statistics."""
        columns = ["column", "count", "unique", "mean", "std", "min", "25%", "50%", "75%", "max"]
        columns = [bokeh.models.TableColumn(field=column) for column in columns]

        self.table = bokeh.models.DataTable(
            source=self.cds_stats,
            columns=columns,
            sizing_mode="stretch_both"
        )
        self.layout_panel = self.table
        return None