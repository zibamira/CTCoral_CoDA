"""
:mod:`histogram`

This module implements an interactive Bokeh histogram plot. The user can zoom
in and out and pan the histogram.

If a second label group is given, then the histogram is drawn as a stacked
area bar chart. Each bar split into the different labels.
"""

from pprint import pprint

import bokeh
import bokeh.plotting
import bokeh.models

import numpy as np

from cora.application import Application
from cora.view.base import ViewBase
from cora.utils import FactorMap, scalar_columns


__all__ = [
    "HistogramPlot",
    "HistogramView"
]


class HistogramPlot(object):
    """A high level histogram plotting interface. This class
    shows a (stacked) bar chart of the histogram in a given
    column of the data frame. 

    The histogram is drawn as stacked area chart if an additional
    label column is given. Then each stack in the bar of a single
    bin corresponds to a label.

    The histogram is interactive and computed for the current selection
    as well as the inverted selection, so that both histograms can be
    compared directly.

    This plot maintains its own internal column data source since
    the aggregated data cannot be part of the global source.

    :param source: 
        The column data source used to compute the histogram. The 
        histogram is updated when the selection in this source 
        changes.
    :param field: 
        The field in :attr:`source` shown in the histogram.
    :param figure: 
        The Bokeh figure on which the histogram is drawn onto.
    :param nbins: 
        The number of bins.
    :param factor_map: 
        The factors for the stacks in the stacked bar chart. The
        factor map must be based on a field in the :attr:`source`.
        The histogram is updated when the factor map changes.
    """

    def __init__(
        self, 
        *, 
        source: bokeh.models.ColumnDataSource,
        field: str,
        figure: bokeh.models.Model,
        nbins: int = 10,
        factor_map: FactorMap = None
        ):
        """ """
        super().__init__()
        
        #: *input* The figure on which the histogram is drawn.
        self.figure = figure

        #: *input* The column data frame corresponding to :attr:`df`.
        self.cds = source
        self.cds.selected.on_change("indices", self.on_cds_selected_change)

        #: *input* The column in the data frame :attr:`df` which is binned
        #: and shown in the histogram.
        self.field = field

        #: *input*The number of bins to use in the histogram.
        self.nbins: int = nbins

        #: *input* The binning range of the histogram. If *None*, 
        #: then the range is infered from the data quantiles.
        self.bin_range = (None, None)

        #: *input* The factor map which determines the stacks in the histogram
        #: bar chart.
        self.factor_map = factor_map
        self.factor_map.on_update.connect(self.on_factor_map_update)

        #: The largest bin count in the histogram. This valus is used
        #: for scaling the visual appearance.
        self.hist_max: int = 0

        #: The ColumnDataSource for the total, overall histogram.
        self.cds_all = bokeh.models.ColumnDataSource()

        #: The ColumnDataSource for the histogram showing the selected data.
        self.cds_selected = bokeh.models.ColumnDataSource()

        #: The ColumnDataSource for the histogram showing the not selected data.
        self.cds_unselected = bokeh.models.ColumnDataSource()

        self.update()
        self.draw()
        return None

    def compute_histogram(self):
        """Computes a stacked histogram. A histogram is computed for each 
        pair of (selected/unselected, label, bin).
        """
        nbins = self.nbins

        xvalues = np.asarray(self.cds.data[self.field])
        xmin = self.bin_range[0] if self.bin_range[0] else np.min(xvalues)
        xmax = self.bin_range[1] if self.bin_range[1] else np.max(xvalues)
        xedges = np.linspace(xmin, xmax, num=nbins + 1, endpoint=True)

        nfactors = len(self.factor_map.factors)
        yvalues = np.asarray(self.factor_map.id_column)
        yedges = np.linspace(-0.5, nfactors - 0.5, nfactors + 1)

        # Compute a stacked histogram for both the selection and inverted
        # selection, *if* data is selected.
        selection = self.cds.selected.indices
        if selection:
            selection_mask = np.full_like(xvalues, False, dtype=bool)
            selection_mask[selection] = True

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
            color = self.factor_map.glyph_map[factor]
            ratio = np.divide(hist, hist_all, out=np.zeros_like(hist), where=hist_all != 0)

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
            color = self.factor_map.glyph_map[factor]
            ratio = np.divide(hist, hist_all, out=np.zeros_like(hist), where=hist_all != 0)

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
        
    def update(self):
        """Recomputes the histogram and updates the column data sources."""
        self.compute_histogram()
        return None 

    def draw(self):
        """Creates the glyphs displaying the histogram in the :attr:`figure`."""
        p = self.figure

        # Overall histogram
        poverall = p.quad(
            left="left",
            right="right",
            top="top",
            bottom="bottom",
            fill_color="grey",
            fill_alpha=0.1,
            line_color="gray",
            source=self.cds_all
        )

        # Selection
        pselected = p.quad(
            left="left",
            right="right",
            top="top",
            bottom="bottom",
            fill_color="color",
            line_color="gray",
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
            line_color="gray",
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

    def on_cds_selected_change(self, attr, old, new):
        """Recompute the histogram when the user selection changes."""
        self.update()
        return None

    def on_factor_map_update(self, sender=None):
        """Called when the user changed the factor map."""
        self.update()
        return None


class HistogramView(ViewBase):
    """A view panel displaying a single histogram plot."""

    def __init__(self, app: Application):
        super().__init__(app)

        #: UI widget for choosing the data column.
        self.ui_select_column = bokeh.models.Select(
            title="Column", 
            sizing_mode="stretch_width"
        )
        self.ui_select_column.on_change(
            "value", self.on_ui_select_column_change
        )

        #: The figure showing the histogram.
        self.figure: bokeh.models.Model = None

        #: The :class:`HistogramPlot` drawn onto the :attr:`figure`.
        self.phist: HistogramPlot = None

        # Sidebar layout.
        self.layout_sidebar.children = [
            self.ui_select_column
        ]
        return None    

    def reload_df(self):
        """Update the UI to the available columns."""
        columns = scalar_columns(self.app.df)

        self.ui_select_column.options = columns
        if self.ui_select_column.value not in columns:
            default_column = columns[0] if columns else None
            self.ui_select_column.value = default_column
        return None
    
    def reload_cds(self):
        """Create the figure if not yet done."""
        self.update_plot()
        return None    

    def update_plot(self):
        """Creates a new figure and histogram plot and replaces the old ones."""
        # Create the figure.
        pfigure = bokeh.plotting.figure(
            title="Histogram",
            sizing_mode="stretch_both",
            tools="reset,hover",
            toolbar_location="above",
            y_axis_label="Count",
            x_axis_label=self.ui_select_column.value
        )
        pfigure.xgrid.visible = False

        # Create the histogram.
        phist = HistogramPlot(
            source=self.app.cds,
            field=self.ui_select_column.value,
            nbins=10,
            factor_map=self.app.fmap_color,
            figure=pfigure
        )

        # Scale the axis so that the histogrma is visible.
        pfigure.y_range.start = -1.05*phist.hist_max
        pfigure.y_range.end = 1.05*phist.hist_max

        # Done.
        self.figure = pfigure
        self.phist = phist
        self.layout_panel.children = [pfigure]
        return None
    
    def on_ui_select_column_change(self, attr, old, new):
        """The user selected another column."""
        if self.is_reloading:
            return None
        self.update_plot()
        return None