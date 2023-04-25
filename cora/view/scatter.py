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

        # Filter out columns that cannot be displayed in a scatter plot.
        columns = scalar_columns(self.app.df)

        #: UI for selecting the x column.
        self.ui_select_column_x = bokeh.models.Select(
            title="X Column",
            sizing_mode="stretch_width",
            options=columns,
            value=columns[0]
        )
        self.ui_select_column_x.on_change(
            "value", self.on_ui_select_column_x_change
        )

        #: UI for selecting the y column.
        self.ui_select_column_y = bokeh.models.Select(
            title="Y Column",
            sizing_mode="stretch_width",
            options=columns,
            value=columns[1]
        )
        self.ui_select_column_y.on_change(
            "value", self.on_ui_select_column_y_change
        )

        # Sidebar layout.
        self.layout_sidebar.children = [
            self.ui_select_column_x,
            self.ui_select_column_y
        ]

        # Create the actual plot.
        self.update()
        return None

    def update(self):
        """Creates the scatter plot and replaces the current figure."""
        colx = self.ui_select_column_x.value
        coly = self.ui_select_column_y.value

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

        self.layout_panel.children = [pfigure]
        return None
    
    def on_ui_select_column_x_change(self, attr, old, new):
        self.update()
        return None
    
    def on_ui_select_column_y_change(self, attr, old, new):
        self.update()
        return None