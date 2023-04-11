"""
:mod:`splom`

This module implements a new SPLOM (scatter plot matrix) in Bokeh,
given a Pandas DataFrame and a list of columns.

The user can interactively select the columns in the Bokeh
ColumnDataSource that should be displayed in the plot. The SPLOM
plot support scalar as well as categorical data. 
"""

import logging
import pathlib
from pprint import pprint
from typing import List, Optional

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

import pandas as pd
import numpy as np
import natsort


__all__ = [
    "Splom"
]




class Splom(object):
    """A custom SPLOM plot class for Bokeh because it didn't have one. 
    """

    def __init__(self):
        """ """
        #: The pandas DataFrame with the original raw data.
        self.df: pd.DataFrame = None

        #: The Bokeh ColumnDataSource enriched with additional rendering information.
        self.cds: bokeh.models.ColumnDataSource = None

        #: The column names in :attr:`df` visible in the scatter plot.
        self.plot_column_names = []

        # shared x and y ranges
        self.x_ranges = dict()
        self.y_ranges = dict()
        
        #: Small figures which only displays the x-axis. These figures
        #: are placed at the top of the SPLOM in each column.
        #:
        #:      column name -> x axis dummy plot
        self.x_axes_plots = dict()

        #: Small figures which only display the y-axes. These figures
        #: are placed at the left side of the SPLOM in each row.
        #:
        #:      column name -> y axis dummy plot
        self.y_axes_plots = dict()

        #: The figures for each histogram plot.
        #:
        #:      column name -> histogram plot
        #:
        #: TODO: Move the histogram plot together with the histogram 
        #:       column data source into a new class. Eventually, Bokeh
        #:       will hopefully provide a built-in histogram plot.
        self.histogram_plots = dict()

        # (column name x, column name y) -> scatter plot
        self.scatter_plots = dict()

        # The grid layout with all plots.
        self.grid_layout = None
        return None
    
    def init(self):
        """Creates the plots."""
        self.init_ranges()
        self.init_axes_plots()
        # self.init_histogram()
        # self.init_histogram_label()
        # self.init_scatter()
        self.init_grid_layout()
        return None
    
    def init_ranges(self):
        """Creates the x and y ranges for all available data. The x ranges are
        shared by all plots in the same column of the SPLOM and the y ranges are
        shared by all plots in the same row.
        """
        self.x_ranges = dict()
        self.y_ranges = dict()

        for column_name in self.plot_column_names:            
            values = self._df[column_name]
            vmin = values.min()
            vmax = values.max()

            x_range = bokeh.models.Range1d(
                vmin, vmax, bounds=(vmin, vmax), name=f"x_range_{column_name}"
            )
            y_range = bokeh.models.Range1d(
                vmin, vmax, bounds=(vmin, vmax), name=f"y_range_{column_name}"
            )

            self.x_ranges[column_name] = x_range
            self.y_ranges[column_name] = y_range
        return None

    def init_axes_plots(self):
        """Creates the axis "dummy" plots that only show an x or y axis."""
        # y axes
        for irow, column_name in enumerate(self.plot_column_names):
            p = bokeh.plotting.figure(
                width=80, 
                height=250, 
                x_range=self.x_ranges[column_name], 
                y_range=self.y_ranges[column_name], 
                y_axis_location="right", 
                outline_line_color=None
            )
            p.scatter([], [])
            p.xaxis.visible = False
            p.xgrid.visible = False
            p.ygrid.visible = False

            p.yaxis.axis_label = self.plot_column_names[irow]
            p.yaxis.ticker.desired_num_ticks = 4

            self.y_axes_plots[column_name] = p

        # x axes
        for icol, column_name in enumerate(self.plot_column_names):
            p = bokeh.plotting.figure(
                width=250, 
                height=60, 
                x_range=self.x_ranges[column_name], 
                y_range=self.y_ranges[column_name], 
                x_axis_location="above", 
                outline_line_color=None
            )
            p.scatter([], [])
            p.yaxis.visible = False
            p.xgrid.visible = False
            p.ygrid.visible = False

            p.xaxis.axis_label = self.plot_column_names[icol]
            p.xaxis.ticker.desired_num_ticks = 4

            self.x_axes_plots[column_name] = p
        return None

    def init_histogram(self, column_name):
        """Creates the histogram plot for the specified column.
        
        TODO: It would be much better if Bokeh would support a builtin
              histogram plot. Currently it is quite static.
        """
        # Compute the histogram.
        values = self._df[column_name]
        vmin = values.min()
        vmax = values.max()
        vrange = (vmin, vmax)
        nbins = 20
        hist, edges = np.histogram(values, bins=nbins, range=vrange)
        
        # Create the plot. The plot is quite low level compared to other
        # plots offered by Bokeh and consists of multiple quads.
        bin_width = np.min(np.abs(np.diff(edges)))
        max_bin_count = np.max(hist)
        
        p = bokeh.plotting.figure(
            width=250, 
            height=250, 
            x_range=self.x_ranges[column_name],
            y_range=bokeh.models.Range1d(0, max_bin_count, bounds=(0, max_bin_count))
        )
        p.quad(
            top=hist, 
            bottom=0, 
            left=edges[:-1], 
            right=edges[1:],
            fill_color="navy", 
            line_color="white", 
            alpha=0.5
        )
        p.xaxis.visible = False
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        self.histogram_plots[column_name] = p
        return None

    def init_histogram_label(self, column_name):
        """Creates the stacked histogram plot for the specified column. The histogram
        bars are stacked and divided for each :attr:`colormap_column_name` label.
        """
        # Compute the histogram.
        y_values = self._df[column_name]
        y_min = y_values.min()
        y_max = y_values.max()
        y_range = (y_min, y_max)
        y_bins = 20
        
        x_min = 0
        x_max = len(self._colormap_unique_labels)
        x_range = (x_min, x_max)
        x_bins = len(self._colormap_unique_labels)
        
        hist, xedges, yedges = np.histogram2d(
            x=self._colormap_label_ids,
            y=y_values, 
            bins=(x_bins, y_bins), 
            range=(x_range, y_range)
        )

        # Pack the histogram data in a dictionary for bokeh to process.
        # This is essentially a new data source with one column for each
        # label containing the histogram. The rows correspond to the
        # histogram bins.
        data = {
            self._colormap_unique_labels[i]: hist[i]\
            for i in range(len(self._colormap_unique_labels))
        }

        # Additionally we add the x edges to data source for plotting.
        data["edges"] = (yedges[:-1] + yedges[1:])/2.0

        # Compute the bin width for the stack area widgets.
        bin_width = np.min(np.abs(np.diff(data["edges"])))
        max_bin_count = np.max(np.sum(hist, axis=0))

        # TODO: Link the colormap client-side and use the same one as for the 
        #       scatter plots.
        colors = bokeh.palettes.Spectral5

        # Create the stacked histogram plot.
        p = bokeh.plotting.figure(
            width=250, 
            height=250, 
            x_range=self.x_ranges[column_name], 
            y_range=bokeh.models.Range1d(0, max_bin_count, bounds=(0, max_bin_count))
        )
        p.vbar_stack(
            self._colormap_unique_labels, 
            x="edges", 
            source=data, 
            fill_color=colors, 
            line_color="white", 
            width=bin_width
        )
        p.xaxis.visible = False
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        self.histogram_plots[column_name] = p
        return None

    def init_scatter(self, column_name_x, column_name_y):
        """Creates the scatter plot for the features in the column *column_name_x* 
        and *column_name_y*.
        """
        p = bokeh.plotting.figure(
            width=250, 
            height=250, 
            x_range=self.x_ranges[column_name_x], 
            y_range=self.y_ranges[column_name_y],
            tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover",
            syncable=True
        )
        p.scatter(
            source=self._source, 
            x=column_name_x,
            y=column_name_y, 
            color=self.colormap, 
            alpha=0.6, 
            size=8.0,
            syncable=True,
            marker=self.glyphmap
            
        )
        p.xaxis.visible = False
        p.yaxis.visible = False

        self.scatter_plots[(column_name_x, column_name_y)] = p
        return None

    def init_grid_layout(self):
        """Aranges all plots and the shared axes in a grid layout."""
        grid = []

        # The first row contains the dummy plots for the x-axes.
        for column_name in self.plot_column_names:
            grid.append(self.x_axes_plots[column_name])

        # The last column (top right corner) is empty.
        grid.append(None)

        # Create the scatter and histogram plots.
        for irow, column_name_y in enumerate(self.plot_column_names):
            for icol, column_name_x in enumerate(self.plot_column_names):
                if irow == icol:
                    
                    if self.colormap_column_name:
                        self.init_histogram_label(column_name_x)
                    else:
                        self.init_histogram(column_name_x)
                    p = self.histogram_plots.get(column_name_x)

                    # self.init_scatter(column_name_x, column_name_y)
                    # p = self.scatter_plots.get((column_name_x, column_name_y))
                elif irow < icol:
                    self.init_scatter(column_name_x, column_name_y)
                    p = self.scatter_plots.get((column_name_x, column_name_y))
                else:
                    p = None
                grid.append(p)

            # The shared y-axis is the last plot in a row.
            grid.append(self.y_axes_plots[column_name_y])       

        # Create the actual bokeh grid layout.
        self.grid = bokeh.layouts.gridplot(grid, ncols=len(self.plot_column_names) + 1)
        self.grid.toolbar_location = "right"
        return None


def splom(
    df: pd.DataFrame,
    source: bokeh.models.ColumnDataSource,
    columns: List[str],
    label_column_name: Optional[str] = None
    ):
    """Shows a scatterplot matrix (SPLOM) for the selected
    raw features of the :data:`ipc_features` spreadsheet.

    This function currently only exists for convenience and may be deleted
    at a later point.

    :seealso: :class:`Splom`
    """
    splom = Splom()
    splom._df = df
    splom._source = source
    splom.plot_column_names = columns
    splom.colormap_column_name = label_column_name
    splom.glyph_column_name = label_column_name
    splom.init()
    return splom.grid