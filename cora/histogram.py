"""
:mod:`histogram`

This module implements an interactive Bokeh histogram plot. The user can zoom
in and out and pan the histogram.

If a second label group is given, then the histogram is drawn as a stacked
area bar chart. Each bar split into the different labels.
"""

import functools
import itertools
from pprint import pprint
from typing import Dict, List, Any, Literal

import bokeh
import bokeh.plotting
import bokeh.model
import bokeh.models
import bokeh.layouts
import bokeh.palettes

import pandas as pd
import numpy as np


__all__ = [
    "HistogramPlot"
]


class HistogramPlot(object):
    """The interactive Histogram."""

    def __init__(self):
        """ """
        #: The raw, not aggregated data.
        self.df: pd.DataFrame = None

        #: The indices of the current selection.
        self.selection: list = None

        #: The Bokeh ColumnDataSource containing the histogram data
        #: and other render information.
        self.cds: bokeh.models.ColumnDataSource = None

        #: The column in the data frame :attr:`df` which is binned
        #: and shown in the histogram.
        self.histogram_column_name: str = None

        #: The column in the data frame :attr:`df` which is used
        #: to create the subgroups in each bin.
        self.label_column_name: str = None

        #: The figure displaying the histogram.
        self.figure: bokeh.models.Model = None
        return None

    def bin_range(self):
        """Returns the range of the histogram. If the plot already 
        exists, then this is just the range that is visible. Otherwise,
        the (min, max) of the data column is used.
        """
        # if self.figure is not None:
        #     r = self.figure.x_range
        #     return (r.start, r.end)
        
        col = self.df[self.histogram_column_name]
        return (col.min(), col.max())
    
    def compute_histogram(self):
        """Computes a non-stacked histogram and ignores the label column
        :attr:`label_column_name`.
        """        
        vmin, vmax = self.bin_range()
        nbins = 10

        xedges = np.linspace(vmin, vmax, num=nbins + 1)
        xvalues = self.df[self.histogram_column_name]

        print("range", vmin, vmax)

        # Compute the histogram. One for the selected samples and one for 
        # the not selected ones.
        if not self.selection:
            hist_all, _ = np.histogram(xvalues, bins=xedges)
            hist_selected = hist_all
            hist_unselected = np.zeros_like(hist_all)
        else:
            mask_selection = np.full_like(xvalues, False, dtype=bool)
            mask_selection[self.selection] = True

            hist_selected, _ = np.histogram(xvalues[mask_selection], bins=xedges)
            hist_unselected, _ = np.histogram(xvalues[~mask_selection], bins=xedges)
            hist_all = hist_selected + hist_unselected

        self.hist_max = hist_all.max()

        # Store the relevant render information in the data dictionary.
        data = {
            "xleft": xedges[:-1],
            "xright": xedges[1:],
            "xwidth": np.diff(xedges),
            "y_all": hist_all,
            "y_selected": hist_selected,
            "y_unselected": -hist_unselected
        }

        if not self.cds:
            self.cds = bokeh.models.ColumnDataSource(data)
        else:
            self.cds.data = data
        return None    
    
    def compute_histogram_stacked(self):
        """Computes a stacked histogram."""
        self.compute_histogram()
        return None

    def init_figure(self):
        """Creates the :attr:`figure` displaying the histogram."""
        self.figure = bokeh.plotting.figure(
            width=600, 
            height=600
        )
        p = self.figure

        # Disable the grid.
        # p.xaxis.visible = False
        # p.yaxis.visible = False
        p.xgrid.visible = False
        # p.ygrid.visible = False
        
        # Outline with **all** values.
        p.quad(
            bottom=0,
            left="xleft",
            right="xright",
            top="y_all",
            line_color="grey",
            fill_alpha=0.0,
            source=self.cds
        )

        # Histogram of the current selection.
        p.quad(
            bottom=0,
            left="xleft",
            right="xright",
            top="y_selected",
            line_color="grey",
            fill_color="blue",
            fill_alpha=1.0,
            source=self.cds
        )

        # Histogram of the inverted selection.
        p.quad(
            bottom=0,
            left="xleft",
            right="xright",
            top="y_unselected",
            line_color=None,
            fill_color="blue",
            fill_alpha=0.2,
            source=self.cds
        )
        return None

    def set_selection(self, indices=None):
        """Sets the current selection."""
        self.selection = indices
        return None

    def update(self):
        """Recomputes the histogram."""
        if self.label_column_name:
            self.compute_histogram_stacked()
        else:
            self.compute_histogram()

        if self.figure is None:
            self.init_figure()

        self.figure.y_range.start = -1.05*self.hist_max
        self.figure.y_range.end = 1.05*self.hist_max
        return None
    
