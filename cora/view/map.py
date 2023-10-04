"""
:mod:`cora.view.map`

This module adds a panel view showing the locations associated with
the samples.
"""

from typing import List

import bokeh
import bokeh.models
import bokeh.transform

import xyzservices
import xyzservices.providers

import numpy as np
import pandas as pd

from cora.application import Application
import cora.utils
from cora.view.base import ViewBase


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


def guess_location_columns(columns: List[str]):
    """Guesses columns containing geo location information
    in the dataframe.
    """
    # Deal with case sensitivity by working only on lower case names.
    columns_lc = {column.lower(): column for column in columns}

    # Split the columns into prefix and name.
    prefixes_lc = [column_lc.rsplit(":", 1)[0] for column_lc in columns_lc.values()]
    
    # Common column names (without prefix) for start and end columns
    # of edges.
    names_lc = [
        ("latitude", "longitude")
    ]

    # Try all pairs.
    for prefix_lc in prefixes_lc:
        for source_lc, target_lc in names_lc:
            prefixed_source_lc = f"{prefix_lc}:{source_lc}"
            prefixed_target_lc = f"{prefix_lc}:{target_lc}"

            if prefixed_source_lc not in columns_lc:
                continue
            if prefixed_target_lc not in columns_lc:
                continue
                
            source = columns_lc[prefixed_source_lc]
            target = columns_lc[prefixed_target_lc]
            return (source, target)
    return (None, None)


class MapView(ViewBase):
    """A panel with a single map view. For now, it is assumed that
    each sample has a single location.
    """

    def __init__(self, app: Application):
        super().__init__(app)

        #: Widget for choosing the longitude.
        self.ui_select_column_longitude = bokeh.models.Select(
            title="Longitude",
            sizing_mode="stretch_width"
        )
        self.ui_select_column_longitude.on_change(
            "value", self.on_ui_select_column_latitude_change
        )

        #: Widget for choosing the lattitude.
        self.ui_select_column_latitude = bokeh.models.Select(
            title="Latitude",
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
        return None

    
    def reload_df(self):
        """Update the UI menus with the available columns that may contain
        the geo location information.
        """
        # Candidates for columns containing geo location data.
        columns = cora.utils.scalar_columns(self.app.df)
        self.ui_select_column_longitude.options = columns
        self.ui_select_column_latitude.options = columns

        # Check if the currently selected location columns are still available
        # and set to them to default values if not.
        longitude_column = self.ui_select_column_longitude.value
        latitude_column = self.ui_select_column_latitude.value
        if not (longitude_column in columns and latitude_column in columns):
            latitude_column, longitude_column = guess_location_columns(columns)
            self.ui_select_column_latitude.value = latitude_column
            self.ui_select_column_longitude.value = longitude_column

        # Recompute the dataframe mercator coordinates since they are not
        # present after a reload.
        self.update_df()
        return None
    
    def reload_cds(self):
        """Update the map with the current geo location columns."""
        # The column data source is available, so we may try to create
        # the map view plot. Note that we only have to create the figure
        # one since the actual render data (column data) still remains
        # in the internal *cora:map:mercatorx* and *cora:map:mercatory*
        # columns.
        if self.figure is None:
            self.create_figure()
        return None
    

    def update_df_with_defaults(self):
        """Updates the dataframe with default values for the mercator
        coordinates when the geo location columns are not valid.
        """
        nrows = len(self.app.df.index)
        self.app.df["cora:map:mercatorx"] = np.full(nrows, np.nan)
        self.app.df["cora:map:mercatory"] = np.full(nrows, np.nan)

        # Schedule a column data source update.
        self.app.push_df_to_cds(vertex=True)
        return None
    
    def update_df(self):
        """Updates the mercator coordinates in Cora's global ColumnDataSource."""
        # Check if the location columns exist.
        latitude_column = self.ui_select_column_latitude.value
        longitude_column = self.ui_select_column_longitude.value

        if latitude_column not in self.app.df or longitude_column not in self.app.df:
            self.update_df_with_defaults()
            return None
        
        # Convert to mercator coordinates.
        latitude = self.app.df[latitude_column]
        longitude = self.app.df[longitude_column]
        mercatorx, mercatory = latlong_to_mercator(latitude, longitude)

        self.app.df["cora:map:mercatorx"] = mercatorx
        self.app.df["cora:map:mercatory"] = mercatory

        # Schedule a column data source update.
        self.app.push_df_to_cds(vertex=True)
        return None


    def create_figure(self):
        """Creates the figure showing the worl map overlayed with a scatter
        plot of the geo location data.

        The current figure is replaced with a new one.
        """
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
            x_range=(-x_max, x_max),
            tooltips=[
                ("index", "$index")
            ]
        )

        pfigure.add_tile(
            xyzservices.providers.Stamen.Terrain, 
            retina=True
        )

        # TODO: Perform the Mercator projection on the client-side.
        #       instead of updating and adding new columns to the
        #       application's ColumnDataSource in :func:`update_cds`.
        #       I tried to use Bokeh's CustomJSTransform but could
        #       not make it work.
        pscatter = pfigure.scatter(
            x=bokeh.transform.jitter("cora:map:mercatorx", width=0.1),
            y=bokeh.transform.jitter("cora:map:mercatory", width=0.1),
            color="cora:color:glyph",
            marker="cora:marker:glyph",
            line_color="gray",
            source=self.app.cds
        )

        # Link the marker appearance settings.
        pscatter.glyph.size = self.app.ui_slider_size.value
        pscatter.glyph.fill_alpha = self.app.ui_slider_opacity.value
        pscatter.glyph.line_alpha = self.app.ui_slider_opacity.value

        self.app.ui_slider_size.js_link("value", pscatter.glyph, "size")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "fill_alpha")
        self.app.ui_slider_opacity.js_link("value", pscatter.glyph, "line_alpha")

        # Done.
        self.figure = pfigure
        self.layout_panel.children = [pfigure]
        return None
    
    
    def on_ui_select_column_latitude_change(self, attr, old, new):
        """The user selected a new column containing the latitude information."""
        if self.is_reloading:
            return None        
        self.update_df()
        return None
    
    def on_ui_select_column_longitude_change(self, attr, old, new):
        """The user selected a new column containing the longitude information."""
        if self.is_reloading:
            return None        
        self.update_df()
        return None