"""
:mod:`coda.view.legend`

This module adds a panel view showing the legend for the current glyph mapping.
"""

from typing import List

import bokeh
import bokeh.models

from coda.application import Application
from coda.view.base import ViewBase
from coda.utils import scalar_columns


__all__ = [
    "LegendView"
]


class LegendView(ViewBase):
    """A panel with a single legend view."""

    def __init__(self, app: Application):
        super().__init__(app)

        #: The figure displaying the scatter plot.
        self.figure: bokeh.models.Model = None

        #: The actual scatter plot.
        self.pscatter: bokeh.models.Model = None

        # Sidebar layout.
        self.layout_sidebar.children = []
        return None


    def reload_df(self):
        """Updates the UI to match the available columns."""
        return None

    def reload_cds(self):
        """Update the plot if needed."""
        return None


    def update_plot(self):
        """Creates the scatter plot and replaces the current figure."""
        colx = self.ui_select_column_x.value
        coly = self.ui_select_column_y.value
        if not (colx and coly):
            return None

        pfigure = bokeh.plotting.figure(
            title="Scatter",
            sizing_mode="stretch_both",
            tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover",
            toolbar_location="above",
            tooltips=[
                ("index", "$index"),
                ("x", "$x"),
                ("y", "$y")
            ],
            x_axis_label=colx,
            y_axis_label=coly
        )

        pscatter = pfigure.scatter(
            x=colx, 
            y=coly,
            source=self.app.cds,
            color="coda:color:glyph",
            marker="coda:marker:glyph",
            line_color="gray"
        )

        pscatter.glyph.size = self.app.ui_slider_size.value
        pscatter.glyph.fill_alpha = self.app.ui_slider_opacity.value
        pscatter.glyph.line_alpha = self.app.ui_slider_opacity.value

        self.app.ui_slider_size.js_link("value", pscatter.glyph, "size")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "fill_alpha")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "line_alpha")

        self.figure = pfigure
        self.pscatter = pscatter
        
        self.layout_panel.children = [pfigure]
        return None
    
    def on_ui_select_column_x_change(self, attr, old, new):
        """The user changed the x axis column."""
        if self.is_reloading:
            return None        
        
        # XXX: We must replace the whole plot since Bokeh does not allow 
        #      us to just change the *x* field of :attr:`pscatter`.
        self.update_plot()
        return None
    
    def on_ui_select_column_y_change(self, attr, old, new):
        """The user changed the y axis column."""
        if self.is_reloading:
            return None
        
        # XXX: We must replace the whole plot since Bokeh does not allow 
        #      us to just change the *y* field of :attr:`pscatter`.
        self.update_plot()
        return None


# TODO: Whisker
# TODO: Legend