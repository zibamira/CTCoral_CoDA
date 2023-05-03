"""
:mod:`cora.view.scatter`

This module adds a panel view displaying a single scatter plot.
"""

from typing import List

import bokeh
import bokeh.models

from cora.application import Application
from cora.view.base import ViewBase
from cora.utils import scalar_columns


__all__ = [
    "ScatterView"
]


class ScatterView(ViewBase):
    """A panel with a single scatter view plot."""

    def __init__(self, app: Application):
        super().__init__(app)

        #: UI for selecting the x column.
        self.ui_select_column_x = bokeh.models.Select(
            title="X Column",
            sizing_mode="stretch_width"
        )
        self.ui_select_column_x.on_change(
            "value", self.on_ui_select_column_x_change
        )

        #: UI for selecting the y column.
        self.ui_select_column_y = bokeh.models.Select(
            title="Y Column",
            sizing_mode="stretch_width"
        )
        self.ui_select_column_y.on_change(
            "value", self.on_ui_select_column_y_change
        )

        #: The figure displaying the scatter plot.
        self.figure: bokeh.models.Model = None

        #: The actual scatter plot.
        self.pscatter: bokeh.models.Model = None

        # Sidebar layout.
        self.layout_sidebar.children = [
            self.ui_select_column_x,
            self.ui_select_column_y
        ]
        return None
    

    def reload_df(self):
        """Updates the UI to match the available columns."""
        # Filter out columns that cannot be displayed in a scatter plot.
        columns = scalar_columns(self.app.df)

        self.ui_select_column_x.options = columns
        self.ui_select_column_y.options = columns

        if self.ui_select_column_x.value not in columns:
            default_column = columns[0] if columns else None
            self.ui_select_column_x.value = default_column

        if self.ui_select_column_y.value not in columns:
            default_column = columns[min(1, len(columns))] if columns else None
            self.ui_select_column_y.value = default_column
        return None

    def reload_cds(self):
        """Update the plot if needed."""
        if self.figure is None:
            self.update_plot()
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
            color="cora:color:glyph",
            marker="cora:marker:glyph",
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