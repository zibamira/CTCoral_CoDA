"""
:mod:`splom`

This module implements a new SPLOM (scatter plot matrix) in Bokeh,
given a Pandas DataFrame and a list of columns.
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


__all__ = [
    "splom_histogram",
    "splom_scatter",
    "splom"
]


def selection_callback(attr, old, new):
    """Called when the user selection changes."""
    print("cluster selection changed.")
    return None


class Splom(object):
    """A custom SPLOM plot class for Bokeh because it didn't have one.
    """

    def __init__(self):
        self._df = None
        self._source = None

        self.column_names_plots = []
        self.column_name_colormap = ""
        self.column_name_glyph = ""
        self.column_name_size = ""

        self.x_ranges = []
        self.y_ranges = []

        self.x_axes = []
        self.y_axes = []

        self.colormap = None

        self.histograms = []
        self.plots = []
        return None

    def init_ranges(self):
        """Creates the x and y ranges for all available data."""    

        return None

    def init_axes(self):
        """Creates the axes for all available data."""
        return None

    def init_axes_plots(self):
        """Creates the axis "dummy" plots that only show an x or y axis."""
        return None

    def init_histogram(self, column_name):
        """Creates the histogram plot for the specified column."""
        return None

    def init_scatter(self, column_name_x, column_name_y):
        """Creates the scatter plot for the features in the column *column_name_x* 
        and *column_name_y*.
        """
        return None

    def init_grid_layout(self):
        """Aranges all plots and the shared axes in a grid layout."""
        return None


def splom(
    df: pd.DataFrame,
    source: bokeh.models.ColumnDataSource,
    columns: List[str],
    label_column_name: Optional[str] = None
    ):
    """Shows a scatterplot matrix (SPLOM) for the selected
    raw features of the :data:`ipc_features` spreadsheet.
    """
    ncolumns = len(columns) - 1

    # Wait for changes in the selection.
    source.selected.on_change("indices", selection_callback)

    # Create the ranges.
    x_ranges = []
    y_ranges = []
    for i in range(ncolumns):
        column = columns[i]
        values = df[column]
        vmin = values.min()
        vmax = values.max()        
        x_range = bokeh.models.Range1d(vmin, vmax, bounds=(vmin, vmax), name=f"x_range_{column}")
        y_range = bokeh.models.Range1d(vmin, vmax, bounds=(vmin, vmax), name=f"y_range_{column}")
        x_ranges.append(x_range)
        y_ranges.append(y_range)

    # Create the axes.
    x_axes = []
    y_axes = []
    for i in range(ncolumns):
        column = columns[i]
        values = df[column]
        x_axis = bokeh.models.LinearAxis(axis_label=df.columns[i], x_range_name=f"x_range_{column}")
        y_axis = bokeh.models.LinearAxis(axis_label=df.columns[i], y_range_name=f"y_range_{column}")
        x_axes.append(x_axis)
        y_axes.append(y_axis)

    # Prepare the label / classes for the histogram plots.
    if label_column_name is not None:
        labels = df["label"]
        labels_unique = np.sort(np.unique(labels))
        labels2id = {label: i for i, label in enumerate(labels_unique)}
        labels_int = np.array([labels2id[label] for label in df["label"]])

        # Use the labels (classes) as colormap.
        colormap = bokeh.transform.factor_cmap(
            "label", palette=bokeh.palettes.Spectral5, factors=labels_unique.astype(str)
        )
    else:
        colormap = "blue"

    # Create the SPLOT plots.
    grid = []
    for irow in range(ncolumns):
        # Add a new row to the grid.
        row = []
        grid.append(row)

        for icol in range(ncolumns):
            x_range = x_ranges[icol]
            y_range = y_ranges[irow]

            # Create a histogram for the plots on the SPLOM diagonal.
            if irow == icol:

                x_values = df[columns[icol]]
                x_min = x_values.min()
                x_max = x_values.max()
                x_range = (x_min, x_max)
                x_bins = 10

                if label_column_name is not None:
                    
                    y_min = 0
                    y_max = len(labels_unique)
                    y_range = (y_min, y_max)
                    y_bins = len(labels_unique)
                    
                    hist, xedges, yedges = np.histogram2d(
                        x=x_values, 
                        y=labels_int,
                        bins=(x_bins, y_bins), 
                        range=(x_range, y_range)
                    )

                    # Pack the histogram data in a dictionary for bokeh to process.
                    data = {labels_unique[i]: hist[:, i] for i in range(len(labels_unique))}
                    data["xedges"] = (xedges[:-1] + xedges[1:])/2.0

                    # Compute the bin width for the stack area widgets.
                    bin_width = np.min(np.abs(np.diff(data["xedges"])))
                    max_bin_count = np.max(np.sum(hist, axis=1))

                    # TODO: Link the colormap client-side.
                    colors = bokeh.palettes.Spectral5

                    # Create the histogram plot.
                    p = bokeh.plotting.figure(
                        width=250, height=250, x_range=x_ranges[irow], 
                        y_range=bokeh.models.Range1d(0, max_bin_count, bounds=(0, max_bin_count))
                    )
                    p.vbar_stack(
                        labels_unique, x="xedges", source=data, fill_color=colors, 
                        line_color="white", width=bin_width
                    )
                    p.xaxis.visible = False
                    p.yaxis.visible = False
                    p.xgrid.visible = False
                    p.ygrid.visible = False
                else:
                    hist, xedges = np.histogram(x_values, bins=x_bins, range=x_range)

                    bin_width = np.min(np.abs(np.diff(xedges)))
                    max_bin_count = np.max(hist)
                    
                    p = bokeh.plotting.figure(
                        width=250, height=250, x_range=x_ranges[irow],
                        y_range=bokeh.models.Range1d(0, max_bin_count, bounds=(0, max_bin_count))
                    )
                    p.quad(
                        top=hist, bottom=0, left=xedges[:-1], right=xedges[1:],
                        fill_color="navy", line_color="white", alpha=0.5
                    )
                    p.xaxis.visible = False
                    p.yaxis.visible = False
                    p.xgrid.visible = False
                    p.ygrid.visible = False           

            # Create scatter plots for upper-diagonal plots.
            elif icol >= irow:
                p = bokeh.plotting.figure(
                    width=250, height=250, x_range=x_range, y_range=y_range,
                    tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover",
                    syncable=True
                )
                p.scatter(
                    source=source, x=columns[icol], y=columns[irow], 
                    color=colormap, alpha=0.6, size=8.0,
                    syncable=True
                    
                )
                p.xaxis.visible = False
                p.yaxis.visible = False

            else:
                p = None

            row.append(p)

    # Create "fake" plots for the y-axes. The only purpose for these
    # plots is to show the axis on top of the SPLOM.
    for irow in range(ncolumns):
        p = bokeh.plotting.figure(
            width=80, height=250, 
            x_range=x_ranges[irow], y_range=y_ranges[irow], 
            y_axis_location="right", outline_line_color=None
        )
        p.scatter([], [])
        p.xaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        p.yaxis.axis_label = columns[irow]
        p.yaxis.ticker.desired_num_ticks = 4
        grid[irow].append(p)

    # Create "fake" plots for the x-axes. The only purpose for these
    # plots is to show the axis on the right side of the SPLOM.
    grid.insert(0, [])
    for icol in range(ncolumns):
        p = bokeh.plotting.figure(
            width=250, height=60, 
            x_range=x_ranges[icol], y_range=y_ranges[icol], 
            x_axis_location="above", outline_line_color=None
        )
        p.scatter([], [])
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        p.xaxis.axis_label = columns[icol]
        p.xaxis.ticker.desired_num_ticks = 4
        grid[0].append(p)

    # Create an empty plot in the top-right corner.
    grid[0].append(None)

    # Wrap everything in a proper bokeh layout.
    grid = bokeh.layouts.gridplot(grid)
    grid.toolbar_location = "right"
    return grid