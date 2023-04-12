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

        #: The number of bins to use in the histogram.
        self.nbins: int = 10

        #: The column in the data frame :attr:`df` which is binned
        #: and shown in the histogram.
        self.histogram_column_name: str = None

        #: A list with all unique names in the label column. The order
        #: determines their position in the stack and their id.
        self.labels: list = None

        #: The name with the column of the discrete label ids (numeric)
        #: in the data frame :attr:`df`.
        self.label_id_column_name: str = None

        #: A colormap, mapping the label name to their color.
        self.label_to_color: Dict[str, Any] = None

        #: The ColumnDataSource for the total, overall histogram.
        self.cds_all = bokeh.models.ColumnDataSource()
        self.cds_all.selected.on_change("indices", self.on_cds_all_selection_change)

        #: The ColumnDataSource for the histogram showing the selected data.
        self.cds_selected = bokeh.models.ColumnDataSource()
        self.cds_selected.selected.on_change("indices", self.on_cds_selected_selection_change)

        #: The ColumnDataSource for the histogram showing the not selected data.
        self.cds_unselected = bokeh.models.ColumnDataSource()
        self.cds_unselected.selected.on_change("indices", self.on_cds_unselected_selection_change)

        #: The figure displaying the histogram.
        self.figure: bokeh.models.Model = None
        return None

    def set_label_column_name(self, name):
        """Sets the name of the column to use as label. The histogram bars 
        are stacks of these label-wise histograms.
        """
        # Nothing to do.
        if name == self.label_column_name:
            return None

        # Compute the unique labels.
        labels = self.df[name]
        unique = np.unique(labels)

        # Map the labels to unique ids.
        self.label_to_id = {label: i for i, label in enumerate(unique)}

        # Create the id column.
        self.label_ids = np.array([self.label_to_id(label) for label in labels])
        return None

    def range(self):
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
        """Computes a stacked histogram. A histogram is computed for each 
        pair of (selected/unselected, label, bin).
        """
        xmin, xmax = self.range()
        nbins = self.nbins
        nfactors = len(self.label_to_color)
        
        xvalues = self.df[self.histogram_column_name]
        yvalues = self.df[self.label_id_column_name]

        xedges = np.linspace(xmin, xmax, num=nbins + 1, endpoint=True)
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
        self.update_cds_selected(hist2d_selected, xedges)
        self.update_cds_unselected(hist2d_unselected, xedges)
        return None

    def update_cds_all(self, hist, xedges):
        """Updates the render information for the overall histogram."""
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
    
    def update_cds_selected(self, hist2d, xedges):
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
            "label": []
        }

        # Create a quad for each factor and bin pair in the selection.
        nbins = self.nbins
        left = xedges[:-1]
        right = xedges[1:]
        top = np.zeros_like(left)

        for ifactor, factor in enumerate(self.labels):
            bottom = top
            hist = hist2d[:, ifactor]
            top = bottom + hist
            color = self.label_to_color[factor]

            data["left"].extend(left)
            data["right"].extend(right)
            data["bottom"].extend(bottom)
            data["top"].extend(top)
            data["color"].extend([color]*nbins)
            data["count"].extend(hist)
            data["label"].extend([factor]*nbins)

        # Update the Bokeh source at once.
        self.cds_selected.data = data
        return None    

    def update_cds_unselected(self, hist2d, xedges):
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
            "label": []
        }

        # Create a quad for each factor and bin pair in the selection.
        nbins = self.nbins
        left = xedges[:-1]
        right = xedges[1:]
        bottom = np.zeros_like(left)

        for ifactor, factor in enumerate(self.labels):
            hist = hist2d[:, ifactor]
            top = bottom
            bottom = top - hist
            color = self.label_to_color[factor]

            data["left"].extend(left)
            data["right"].extend(right)
            data["bottom"].extend(bottom)
            data["top"].extend(top)
            data["color"].extend([color]*nbins)
            data["count"].extend(hist)
            data["label"].extend([factor]*nbins)

        # Update the Bokeh source at once.
        self.cds_unselected.data = data
        return None       
    
    def on_cds_all_selection_change(self, attr, old, new):
        """The user selected a bin in the inverted selection (unselected) histogram."""
        # TODO: Link the selection with the global index selection.
        print(attr, old, new)
        return None
    
    def on_cds_selected_selection_change(self, attr, old, new):
        """The user selected a bin in the selection histogram."""
        # TODO: Link the selection with the global index selection.
        print(attr, old, new)
        return None
    
    def on_cds_unselected_selection_change(self, attr, old, new):
        """The user selected a bin in the inverted selection (unselected) histogram."""
        # TODO: Link the selection with the global index selection.
        print(attr, old, new)
        return None
    
    def init_figure(self):
        """Creates the :attr:`figure` displaying the histogram."""
        self.figure = bokeh.plotting.figure(
            width=600, 
            height=600,
            tools="reset,hover,tap,save",
            tooltips=[
                ("Label", "@label"),
                ("Count", "@count")
            ]
        )
        p = self.figure

        # Disable the grid.
        p.xaxis.visible = False
        p.xgrid.visible = False
        # p.yaxis.visible = False
        # p.ygrid.visible = False

        # Overall histogram
        p.quad(
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
        p.quad(
            left="left",
            right="right",
            top="top",
            bottom="bottom",
            fill_color="color",
            line_color="white",
            source=self.cds_selected
        )        

        # Inverted selection
        p.quad(
            left="left",
            right="right",
            top="top",
            bottom="bottom",
            fill_color="color",
            fill_alpha=0.1,
            line_color="white",
            source=self.cds_unselected
        )
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