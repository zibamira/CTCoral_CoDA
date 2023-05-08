"""
:mod:`splom`

This module implements a new SPLOM (scatter plot matrix) in Bokeh,
given a Pandas DataFrame and a list of columns.

The user can interactively select the columns in the Bokeh
ColumnDataSource that should be displayed in the plot. The SPLOM
plot support scalar as well as categorical data. 
"""

from typing import List, Dict

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

import numpy as np

from cora.application import Application
from cora.view.base import ViewBase
from cora.view.histogram import HistogramPlot
import cora.utils
from cora.utils import FactorMap


__all__ = [
    "SplomView"
]


class SplomView(ViewBase):
    """A custom SPLOM plot class for Bokeh because it didn't have one. 
    The user can interactively choose which columns should be shown in the SPLOM.
    Additionally, the diagonal plots may be chose as scatter plots or more sophisticated
    cross-tabular histgorams.
    """

    # TODO: Implement the gridplot using "sizing_mode=stretch_both". This results
    #       in a responsive layout. However, in Bokeh version 3.1.0. the responsive
    #       layout also allocated the same space for the smaller dummy axis plots,
    #       resulting in wasted screen space. 

    def __init__(self, app: Application):
        super().__init__(app)
        
        #: Menu for selecting the columns that should be visible in the SPLOM.
        self.ui_multichoice_columns = bokeh.models.MultiChoice(
            title="Columns",
            sizing_mode="stretch_width"
        )
        self.ui_multichoice_columns.on_change("value", self.on_multichoice_columns_change)

        #: The width and height of each plot in the SPLOM.
        #:
        #: :todo: Determine this value automatic depenending on the available
        #:        screen space. Or check if Bokeh layouts are capable of 
        #:        handling this in a responsive way.
        self.width = 200

        #: The shared x range for each column in the data frame.
        self.x_ranges: Dict[str, bokeh.models.Range1d] = dict()

        #: The shared y range for each column in the data frame.
        self.y_ranges: Dict[str, bokeh.models.Range1d] = dict()
        
        #: Small figures which only displays the x-axis. These figures
        #: are placed at the top of the SPLOM in each column.
        #:
        #:      column name -> x axis dummy plot
        self.x_axes_plots: Dict[str, bokeh.models.Model] = dict()

        #: Small figures which only display the y-axes. These figures
        #: are placed at the left side of the SPLOM in each row.
        #:
        #:      column name -> y axis dummy plot
        self.y_axes_plots: Dict[str, bokeh.models.Model] = dict()

        #: The figures for each histogram plot.
        #:
        #:      column name -> histogram plot
        self.histogram_plots: Dict[str, bokeh.models.Model] = dict()

        # (column name x, column name y) -> scatter plot
        self.scatter_plots: Dict[str, bokeh.models.Model] = dict()

        # Init.
        self.layout_sidebar.children = [
            self.ui_multichoice_columns
        ]
        return None
    

    def reload_df(self):
        """Reload the dataframe."""
        columns = cora.utils.scalar_columns(self.app.df)

        selection = self.ui_multichoice_columns.value
        selection = [column for column in selection if column in columns]

        self.ui_multichoice_columns.options = columns
        self.ui_multichoice_columns.value = selection
        return None

    def reload_cds(self):
        """Recreate the SPLOM as soon as all data is available."""
        self.update_layout()
        return None

    
    def create_range(self, column_name: str):
        """Creates the x and y range for the column with the name *column_name*.
        The x range is shared by all plots in the same column of the SPLOM and 
        the y range is shared by all plots in the same row.
        """
        if column_name in self.x_ranges:
            return None

        values = self.app.df[column_name]
        vmin = values.min()
        vmax = values.max()
        if vmin == vmax:
            vmin -= 1.0
            vmax += 1.0
        
        x_range = bokeh.models.Range1d(
            vmin, vmax, name=f"x_range_{column_name}"
        )
        y_range = bokeh.models.Range1d(
            vmin, vmax, name=f"y_range_{column_name}"
        )

        self.x_ranges[column_name] = x_range
        self.y_ranges[column_name] = y_range
        return None

    def create_axes_plots(self, column_name: str):
        """Creates the axis "dummy" plots that only show an x or y axis
        for the column with the name *column_name*.
        """
        if column_name in self.x_axes_plots:
            return None

        # Create the range if not yet done.
        self.create_range(column_name)

        # y axis
        py = bokeh.plotting.figure(
            width=60, 
            height=self.width,
            sizing_mode="fixed",
            x_range=self.x_ranges[column_name], 
            y_range=self.y_ranges[column_name],
            y_axis_location="left", 
            outline_line_color=None,
            toolbar_location=None
        )
        py.scatter([], [])
        py.xaxis.visible = False
        py.xgrid.visible = False
        py.ygrid.visible = False

        py.yaxis.axis_label = column_name
        py.yaxis.ticker.desired_num_ticks = 4

        self.y_axes_plots[column_name] = py

        # x axis
        px = bokeh.plotting.figure(
            width=self.width,
            height=60, 
            x_range=self.x_ranges[column_name], 
            y_range=self.y_ranges[column_name], 
            x_axis_location="above", 
            outline_line_color=None,
            sizing_mode="fixed",
            toolbar_location=None
        )
        px.scatter([], [])
        px.yaxis.visible = False
        px.xgrid.visible = False
        px.ygrid.visible = False

        px.xaxis.axis_label = column_name
        px.xaxis.ticker.desired_num_ticks = 4

        self.x_axes_plots[column_name] = px
        return None

    def create_histogram(self, column_name):
        """Creates the histogram plot for the specified column."""
        if column_name in self.histogram_plots:
            return None

        # Create the range if not yet done.
        self.create_range(column_name)
        x_range = self.x_ranges[column_name]

        # Create the histogram.
        p = bokeh.plotting.figure(
            width=self.width,
            height=self.width,
            sizing_mode="fixed",
            x_range=x_range,
            outline_line_color=None
        )
        p.xaxis.visible = False
        p.xgrid.visible = False
        p.yaxis.visible = False

        phist = HistogramPlot(
            source=self.app.cds,
            field=column_name,
            nbins=10,
            factor_map=self.app.fmap_color,
            figure=p
        )

        self.histogram_plots[column_name] = phist
        return None

    def create_scatter(self, column_name_x, column_name_y):
        """Creates the scatter plot for the features in the column *column_name_x* 
        and *column_name_y*.
        """
        if (column_name_x, column_name_y) in self.scatter_plots:
            return None

        # Create the range if not yet done.
        self.create_range(column_name_x)
        self.create_range(column_name_y)

        # Create the figure.
        p = bokeh.plotting.figure(
            width=self.width,
            height=self.width,
            sizing_mode="fixed",
            syncable=True,
            x_range=self.x_ranges[column_name_x], 
            y_range=self.y_ranges[column_name_y],
            tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover",
            toolbar_location=None
        )

        p.xaxis.visible = False
        p.yaxis.visible = False

        # Create the scatter plot.
        pscatter = p.scatter(
            x=column_name_x,
            y=column_name_y, 
            source=self.app.cds,
            color="cora:color:glyph",
            marker="cora:marker:glyph"
        )

        # Link the appearance settings.
        pscatter.glyph.size = self.app.ui_slider_size.value
        pscatter.glyph.fill_alpha = self.app.ui_slider_opacity.value
        pscatter.glyph.line_alpha = self.app.ui_slider_opacity.value

        self.app.ui_slider_size.js_link("value", pscatter.glyph, "size")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "fill_alpha")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "line_alpha")

        # Done.
        self.scatter_plots[(column_name_x, column_name_y)] = p
        return None

    def update_layout(self):
        """Updates the grid layout.
        
        This usually happens after the user adds or removes a column from
        the plot or directly after creating the SplomView.
        """
        column_names_x = self.ui_multichoice_columns.value
        column_names_y = list(reversed(column_names_x))
        ncolumns = len(column_names_x)

        # Nothing to do.
        if ncolumns == 0:
            self.layout_panel.children = []
            return None

        # We create the SPLOM row wise. Using Bokeh's gridplot directly
        # allocated too much space for the dummy x and
        rows = []

        # x axis
        row = [None]

        for column_name in column_names_x:
            self.create_axes_plots(column_name)
            p = self.x_axes_plots[column_name]
            row.append(p)

        rows.append(row)

        # scatter plots + y axes
        for irow, column_name_y in enumerate(column_names_y):
            row = []

            # y axis
            self.create_axes_plots(column_name_y)
            p = self.y_axes_plots[column_name_y]
            row.append(p)

            # scatter plots
            for icol, column_name_x in enumerate(column_names_x):
                if irow == ncolumns - icol - 1:
                    self.create_histogram(column_name_x)
                    p = self.histogram_plots[column_name_x]
                    row.append(p.figure)
                elif irow < ncolumns - icol:
                    self.create_scatter(column_name_x, column_name_y)
                    p = self.scatter_plots[(column_name_x, column_name_y)]
                    row.append(p)
                else:
                    row.append(None)
            rows.append(row)

        # Create the gridplot and update the layout.
        gridplot = bokeh.layouts.gridplot(
            children=rows, 
            toolbar_location="above", 
            merge_tools=True
        )
        self.layout_panel.children = [
            gridplot
        ]
        return None
    

    def on_multichoice_columns_change(self, attr, old, new):
        """The user removed/added a column from/to the plot."""
        if self.is_reloading:
            return None
        self.update_layout()
        return None