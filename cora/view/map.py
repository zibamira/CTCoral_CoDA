"""
:mod:`cora.view.map`

This module adds a panel view showing the locations associated with
the samples.
"""

from typing import List

import bokeh
import bokeh.models

import xyzservices
import xyzservices.providers

import numpy as np
import pandas as pd

from cora.application import Application
from cora.view.base import ViewBase
from cora.utils import scalar_columns


__all__ = [
    "MapView"
]


def latlong_to_mercator(lat, long):
    """Converts the latitude and longitude coordinates 
    to Mercator coordinates.
    """
    k = 6378137.0
    x = long*(k*np.pi/180.0)
    y = np.log(np.tan((90.0 + lat)*np.pi/360.0))*k
    return (x, y)


class MapView(ViewBase):
    """A panel with a single map view. For now, it is assumed that
    each sample has a single location.
    """

    def __init__(self, app: Application):
        super().__init__(app)

        #: Widget for choosing the longitude.
        self.ui_select_column_longitude = bokeh.models.Select(
            title="Longitude",
            options=["input:longitude"],
            value="input:longitude",
            sizing_mode="stretch_width"
        )
        self.ui_select_column_longitude.on_change(
            "value", self.on_ui_select_column_latitude_change
        )

        #: Widget for choosing the lattitude.
        self.ui_select_column_latitude = bokeh.models.Select(
            title="Latitude",
            options=["input:latitude"],
            value="input:latitude",
            sizing_mode="stretch_width"
        )
        self.ui_select_column_latitude.on_change(
            "value", self.on_ui_select_column_longitude_change
        )

        # Sidebar layout.
        self.layout_sidebar.children = [
            self.ui_select_column_latitude,
            self.ui_select_column_longitude
        ]

        # Create the actual plot.
        self.figure: bokeh.models.Model = None
        self.update()
        self.create_figure()

        # Update the column layout.
        self.layout_panel.children = [self.figure]
        return None

    def update(self):
        """Updates the mercator coordinates in Cora's global ColumnDataSource."""
        latitude = self.app.df[self.ui_select_column_latitude.value]
        longitude = self.app.df[self.ui_select_column_longitude.value]

        mercatorx, mercatory = latlong_to_mercator(latitude, longitude)

        self.app.cds.data["cora:map:mercatorx"] = mercatorx
        self.app.cds.data["cora:map:mercatory"] = mercatory
        return None

    def create_figure(self):
        """Creates the scatter plot and replaces the current figure."""
        # Obtain the ranges for the Mercator projection.
        x_max, _ = latlong_to_mercator(0.0, 180.0)
        _, y_max = latlong_to_mercator(90.0, 0.0)
        
        pfigure = bokeh.plotting.figure(
            title="Map",
            sizing_mode="stretch_both",
            tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover",
            toolbar_location="above",
            x_axis_type="mercator",
            x_axis_label="Longitude",
            y_axis_type="mercator",
            y_axis_label="Latitude",
        )

        pfigure.add_tile(
            xyzservices.providers.OpenStreetMap.Mapnik, 
            retina=True
        )

        # TODO: Perform the Mercator projection on the client-side.
        #       instead of updating and adding new columns to the
        #       application's ColumnDataSource in :func:`update_cds`.
        #       I tried to use Bokeh's CustomJSTransform but could
        #       not make it work.
        pscatter = pfigure.scatter(
            x="cora:map:mercatorx", 
            y="cora:map:mercatory",
            color="cora:color:glyph",
            marker="cora:marker:glyph",
            source=self.app.cds
        )

        pscatter.glyph.size = self.app.ui_slider_size.value
        pscatter.glyph.fill_alpha = self.app.ui_slider_opacity.value
        pscatter.glyph.line_alpha = self.app.ui_slider_opacity.value

        self.app.ui_slider_size.js_link("value", pscatter.glyph, "size")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "fill_alpha")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "line_alpha")

        self.figure = pfigure
        return None
    
    def on_ui_select_column_latitude_change(self, attr, old, new):
        self.update()
        return None
    
    def on_ui_select_column_longitude_change(self, attr, old, new):
        self.update()
        return None