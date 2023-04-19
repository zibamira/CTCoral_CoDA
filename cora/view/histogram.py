"""
:mod:`histogram`

This module implements an interactive Bokeh histogram plot. The user can zoom
in and out and pan the histogram.

If a second label group is given, then the histogram is drawn as a stacked
area bar chart. Each bar split into the different labels.
"""

from pprint import pprint
from typing import Dict, Any

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

from natsort import natsorted
import pandas as pd
import numpy as np

from utils import FactorMap


__all__ = [
    "HistogramPlot"
]


class HistogramPlot(object):
    """A high level histogram plotting interface. This class
    takes shows a (stacked) bar chart of the histogram in a given
    column of the data frame. 

    The histogram is drawn as stacked area chart if an additional
    label column is given. Then each stack in the bar of a single
    bin corresponds to a label.

    The histogram is interactive and computed for the current selection
    as well as the inverted selection, so that both histograms can be
    compared directly.
    """

    def __init__(self):
        """ """
        #: *input* The raw, not aggregated data.
        self.df: pd.DataFrame = None

        #: *input* The column data frame corresponding to :attr:`df`.
        self.cds: bokeh.models.ColumnDataSource = None

        #: *input* The figure on which the histogram is plotted.
        self.figure: bokeh.models.Model = None


        #: *input* The column in the data frame :attr:`df` which is binned
        #: and shown in the histogram.
        self.histogram_column_name: str = None


        #: *input*The number of bins to use in the histogram.
        self.nbins: int = 10

        #: *input* The binning range of the histogram. If *None*, 
        #: then the range is infered from the data quantiles.
        self.bin_range = (None, None)


        #: *input* The factor map which determines the stacks in the histogram
        #: bar chart.
        self.factor_map: FactorMap = None

        #: The largest bin count in the histogram. This valus is used
        #: for scaling the visual appearance.
        self.hist_max: int = 0

        #: The ColumnDataSource for the total, overall histogram.
        self.cds_all = bokeh.models.ColumnDataSource()

        #: The ColumnDataSource for the histogram showing the selected data.
        self.cds_selected = bokeh.models.ColumnDataSource()

        #: The ColumnDataSource for the histogram showing the not selected data.
        self.cds_unselected = bokeh.models.ColumnDataSource()
        return None
        
    def compute_histogram(self):
        """Computes a stacked histogram. A histogram is computed for each 
        pair of (selected/unselected, label, bin).
        """
        nbins = self.nbins

        xvalues = self.df[self.histogram_column_name]
        xmin = self.bin_range[0] if self.bin_range[0] else np.min(xvalues)
        xmax = self.bin_range[1] if self.bin_range[1] else np.max(xvalues)
        xedges = np.linspace(xmin, xmax, num=nbins + 1, endpoint=True)

        nfactors = len(self.factor_map.factors)
        yvalues = self.factor_map.id_column
        yedges = np.linspace(-0.5, nfactors - 0.5, nfactors + 1)

        # Compute a stacked histogram for both the selection and inverted
        # selection, *if* data is selected.
        if self.selection:
            selection_mask = np.full_like(xvalues, False, dtype=bool)
            selection_mask[self.selection] = True

            hist2d_selected, _, _ = np.histogram2d(
                x=xvalues[selection_mask], 
                y=yvalues[selection_mask], 
                bins=(xedges, yedges)
            )
            hist2d_unselected, _, _ = np.histogram2d(
                x=xvalues[~selection_mask], 
                y=yvalues[~selection_mask], 
                bins=(xedges, yedges)
            )
        else:
            hist2d_selected, _, _ = np.histogram2d(
                x=xvalues, 
                y=yvalues, 
                bins=(xedges, yedges)
            )
            hist2d_unselected = np.zeros_like(hist2d_selected)

        # Compute the overall histogram, disregarding labels and selection.
        hist_all = np.sum(hist2d_selected, axis=1) + np.sum(hist2d_unselected, axis=1)
        self.hist_max = np.max(hist_all)

        # Update the render information for all three histograms.
        self.update_cds_all(hist_all, xedges)
        self.update_cds_selected(hist2d_selected, hist_all, xedges)
        self.update_cds_unselected(hist2d_unselected, hist_all, xedges)
        return None

    def update_cds_all(self, hist, xedges):
        """Updates the render information for the overall histogram.
        """
        nbins = self.nbins
        data = {
            "left": xedges[:-1],
            "right": xedges[1:],
            "top": hist,
            "bottom": np.zeros(nbins),
            "count": hist,
            "label": ["all"]*nbins
        }

        # Update the Bokeh source at once.
        self.cds_all.data = data
        return None
    
    def update_cds_selected(self, hist2d, hist_all, xedges):
        """Updates the render information for the histogram of the selected
        data.
        """
        # Create a squad for all factor and bin pairs.
        data = {
            "left": [],
            "right": [],
            "top": [],
            "bottom": [],
            "color": [],
            "count": [],
            "label": [],
            "ratio": []
        }

        # Create a quad for each factor and bin pair in the selection.
        nbins = self.nbins
        left = xedges[:-1]
        right = xedges[1:]
        top = np.zeros_like(left)

        for ifactor, factor in enumerate(self.factor_map.factors):
            bottom = top
            hist = hist2d[:, ifactor]
            top = bottom + hist
            color = self.label_to_color[factor]
            ratio = np.where(hist_all > 0, hist/hist_all, 0.0)

            data["left"].extend(left)
            data["right"].extend(right)
            data["bottom"].extend(bottom)
            data["top"].extend(top)
            data["color"].extend([color]*nbins)
            data["count"].extend(hist)
            data["label"].extend([factor]*nbins)
            data["ratio"].extend(ratio)

        # Update the Bokeh source at once.
        self.cds_selected.data = data
        return None    

    def update_cds_unselected(self, hist2d, hist_all, xedges):
        """Updates the render information for the histogram of the unselected
        data.
        """
        # Create a squad for all factor and bin pairs.
        data = {
            "left": [],
            "right": [],
            "top": [],
            "bottom": [],
            "color": [],
            "count": [],
            "label": [],
            "ratio": []
        }

        # Create a quad for each factor and bin pair in the selection.
        nbins = self.nbins
        left = xedges[:-1]
        right = xedges[1:]
        bottom = np.zeros_like(left)

        for ifactor, factor in enumerate(self.factor_map.factors):
            hist = hist2d[:, ifactor]
            top = bottom
            bottom = top - hist
            color = self.label_to_color[factor]
            ratio = np.where(hist_all > 0, hist/hist_all, 0.0)

            data["left"].extend(left)
            data["right"].extend(right)
            data["bottom"].extend(bottom)
            data["top"].extend(top)
            data["color"].extend([color]*nbins)
            data["count"].extend(hist)
            data["label"].extend([factor]*nbins)
            data["ratio"].extend(ratio)

        # Update the Bokeh source at once.
        self.cds_unselected.data = data
        return None       
        
    def init_figure(self):
        """Creates the :attr:`figure` displaying the histogram."""
        # Create and configure the figure.
        p = self.figure = bokeh.plotting.figure(
            width=self.width, 
            height=self.height,
            tools="reset,save"
        )
        p.xaxis.visible = False
        p.xgrid.visible = False
        # p.yaxis.visible = False
        # p.ygrid.visible = False

        # Overall histogram
        poverall = p.quad(
            left="left",
            right="right",
            top="top",
            bottom="bottom",
            fill_color="grey",
            fill_alpha=0.1,
            line_color="white",
            source=self.cds_all
        )

        # Selection
        pselected = p.quad(
            left="left",
            right="right",
            top="top",
            bottom="bottom",
            fill_color="color",
            line_color="white",
            source=self.cds_selected
        )        

        # Inverted selection
        punselected = p.quad(
            left="left",
            right="right",
            top="top",
            bottom="bottom",
            fill_color="color",
            fill_alpha=0.6,
            line_color="white",
            source=self.cds_unselected
        )

        # Create a single hover tool that is only used for the 
        # selection and inverted selection histogram, but not for the
        # overall histogram.        
        hover_tool = bokeh.models.HoverTool(
            renderers=[pselected, punselected],
            tooltips=[
            ("label", "@label"),
            ("count", "@count"),
            ("ratio", "@ratio{%0.2f}"),
            ("min", "@left"),
            ("max", "@right")
        ]
        )
        p.add_tools(hover_tool)
        return None

    def set_selection(self, indices=None):
        """Sets the current selection."""
        self.selection = indices
        return None

    def update(self):
        """Recomputes the histogram."""
        self.compute_histogram()

        if self.figure is None:
            self.init_figure()

        self.figure.y_range.start = -1.05*self.hist_max
        self.figure.y_range.end = 1.05*self.hist_max
        return None 