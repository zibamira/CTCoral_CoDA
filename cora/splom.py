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
from typing import List, Dict, Optional

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

import pandas as pd
import numpy as np
import natsort

from histogram import HistogramPlot


__all__ = [
    "SplomPlot"
]


class SplomPlot(object):
    """A custom SPLOM plot class for Bokeh because it didn't have one. The user can interactively
    choose which columns should be shown in the SPLOM.
    """

    # TODO: I think most of the shared ranges should be part of the cora application
    #       instance so that it can be synchronized globally, e.g. the ranges.

    def __init__(self):
        """ """
        #: The pandas DataFrame with the original raw data.
        self.df: pd.DataFrame = None

        #: The Bokeh ColumnDataSource enriched with additional rendering information.
        self.cds: bokeh.models.ColumnDataSource = None
        
        #: The column names in :attr:`df` visible in the scatter plot.
        self.plot_column_names: List[str] = []

        self.color_factors: List[str] = None
        self.color_column_name: str = None
        self.color_id_column_name: str = None
        self.colormap: Dict[str] = None

        self.marker_factors: List[str] = None
        self.marker_column_name: str = None
        self.marker_id_column_name: str = None
        self.markermap: Dict[str] = None

        self.width = 400

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

        # The grid layout with all plots.
        self.layout = bokeh.models.Column()
        return None
    
    def create_range(self, column_name: str):
        """Creates the x and y range for the column with the name *column_name*.
        The x range is shared by all plots in the same column of the SPLOM and 
        the y range is shared by all plots in the same row.
        """
        if column_name in self.x_ranges:
            return None

        values = self.df[column_name]
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
            width=80, 
            height=self.width, 
            x_range=self.x_ranges[column_name], 
            y_range=self.y_ranges[column_name],
            y_axis_location="right", 
            outline_line_color=None
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
            outline_line_color=None
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

        # Create the histogram.
        p = HistogramPlot()
        p.df = self.df
        p.histogram_column_name = column_name
        p.width = self.width
        p.height = self.width

        p.labels = self.color_factors
        p.label_id_column_name = self.color_id_column_name
        p.label_to_color = self.colormap

        p.update()
        
        self.histogram_plots[column_name] = p
        return None

    def update_histogram(self, column_name):
        """Updates the histogram plot for the specified column."""
        if column_name not in self.histogram_plots:
            self.create_histogram(column_name)
        else:
            p = self.histogram_plots[column_name]
            p.df = self.df
            p.histogram_column_name = column_name
            p.labels = self.color_factors
            p.label_id_column_name = self.color_id_column_name
            p.label_to_color = self.colormap

            p.selection = self.cds.selected.indices
            p.update()
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

        # Create the scatter plot.
        p = bokeh.plotting.figure(
            width=self.width,
            height=self.width, 
            syncable=True,
            # x_range=self.x_ranges[column_name_x], 
            # y_range=self.y_ranges[column_name_y],
            tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover"
        )
        p.scatter(
            x=column_name_x,
            y=column_name_y, 
            source=self.cds,
            color=self.color_column_name,
            marker=self.marker_column_name
        )

        p.xaxis.visible = False
        p.yaxis.visible = False

        self.scatter_plots[(column_name_x, column_name_y)] = p
        return None

    def update_scatter(self, column_name_x, column_name_y):
        """Updates the scatter plot for the given x axis and y axis."""
        if (column_name_x, column_name_y) not in self.scatter_plots:
            self.create_scatter(column_name_x, column_name_y)
        return None

    def update_layout(self):
        """Updates the grid layout."""
        children = []

        # first row with x-axes
        row = []
        for column_name in self.plot_column_names:
            self.create_axes_plots(column_name)
            p = self.x_axes_plots[column_name]
            row.append(p)   
        
        row.append(None)
        children.append(row)

        # scatter plots + y axes
        for icol, column_name_y in enumerate(self.plot_column_names):
            row = []

            # scatter plots
            for irow, column_name_x in enumerate(self.plot_column_names):
                if icol == irow:
                    self.create_histogram(column_name_x)
                    p = self.histogram_plots[column_name_x]
                    row.append(p.figure)
                elif icol < irow:
                    self.create_scatter(column_name_x, column_name_y)
                    p = self.scatter_plots[(column_name_x, column_name_y)]
                    row.append(p)
                else:
                    row.append(None)

            # y axis
            self.create_axes_plots(column_name_y)
            p = self.y_axes_plots[column_name_y]
            row.append(p)

            children.append(row)

        # Update the layout.
        # if self.layout:
        #     self.layout.children = children
        # else:
        pprint(children)
        self.layout = bokeh.layouts.gridplot(
            children,
            toolbar_location="right"
        )
        return None