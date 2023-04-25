"""
:mod:`cora.app`

Bootstraps and launches the Bokeh application.
"""


import logging
from typing import Dict, List, Optional
import sys

import bokeh
import bokeh.layouts
import bokeh.models
import bokeh.plotting

import pandas as pd

import cora.utils
from cora.utils import FactorMap
from cora.data_provider import DataProvider


def init_logging():
    """Initialies the logging module and sets the format options."""
    formatter = logging.Formatter(
        "{levelname} :: {filename}:{lineno} :: {message}", style="{"
    )
    
    console = logging.StreamHandler(stream=sys.stderr)
    console.setLevel(logging.NOTSET)
    console.setFormatter(formatter)

    logging.basicConfig(handlers=[console], level=logging.INFO)
    return None


class Application(object):
    """The application object contains the relevant dataframes
    and global configuration and layout.
    """

    def __init__(self, data_provider: DataProvider):
        """ """
        # -- Input Data --

        #: The shared, only truth of source with the vertex and edge
        #: data.
        self.data_provider = data_provider
        self.data_provider.on_change(self.on_data_provider_change)

        #: If true, then the data is reloaded automatic when a change
        #: was detected.
        self.automatic_reload = False

        #: The raw pandas DataFrame input enriched 
        #: with the glyph and color column.
        self.df = data_provider.df

        #: The raw pandas DataFrame input for the edges and 
        #: edge attribute information, enriched with glyph and
        #: styling data by Cora.
        self.df_edges = data_provider.df_edges


        # -- Render Data --

        #: The Bokeh ColumnDataSource wrapping the DataFrame.
        self.cds = bokeh.models.ColumnDataSource(self.df)
        # self.cds.selected.on_change("indices", self.on_cds_selection_change)

        #: The Bokeh ColumnDataSource wrapping the edges DataFrame.
        self.cds_edges = bokeh.models.ColumnDataSource(self.df_edges)
        # self.cds_edges.selected.on_change("indices", self.on_cds_edges_selection_change)
        # self.cds_edges.selected.on_change("multiline_indices", self.on_cds_edges_selection_change)
        

        # -- Glyph mapping --

        #: The vertex color map.
        self.fmap_color = FactorMap(
            name="cora:color",
            df=self.df,
            cds=self.cds,
            column_name=None,
            palette=["blue", "green", "yellow", "red", "black", "grey"]
        )

        #: The vertex glyph map.
        self.fmap_marker = FactorMap(
            name="cora:marker",
            df=self.df,
            cds=self.cds,
            column_name=None,
            palette=["circle", "cross", "diamond", "asterisk"]
        )

        #: The edge color map.
        self.fmap_color_edges = FactorMap(
            name="cora:edge:color",
            df=self.df_edges,
            cds=self.cds_edges,
            column_name=None,
            palette=["black", "grey", "blue", "green", "yellow", "red"]
        )

        # -- UI controls input --

        self.ui_button_reload = bokeh.models.Button(
            label="Reload", button_type="primary",
            sizing_mode="stretch_width"
        )        
        self.ui_button_reload.on_click(self.on_ui_button_reload_click)


        # -- UI controls vertex appearance --

        #: Menu for selecting the column used for the colormap.
        self.ui_select_color = bokeh.models.Select(title="Color", sizing_mode="stretch_width")
        self.ui_select_color.on_change("value", self.on_ui_select_color_change)

        #: Menu for selecting the column used for the glyphmap.
        self.ui_select_marker = bokeh.models.Select(title="Marker", sizing_mode="stretch_width")
        self.ui_select_marker.on_change("value", self.on_ui_select_marker_change)

        #: Slider for adjusting the glyph size.
        self.ui_slider_size = bokeh.models.Slider(
            title="Size", start=10, end=40, value=12, step=1,
            show_value=False
        )

        #: Slider for adjusting the opacity.
        self.ui_slider_opacity = bokeh.models.Slider(
            title="Opacity", start=0.0, end=1.0, value=1.0, step=0.05,
            show_value=False
        )


        # -- UI controls edge appearance --

        #: Menu for selecting the column used for the edge colormap.
        self.ui_select_color_edges = bokeh.models.Select(title="Color", sizing_mode="stretch_width")
        self.ui_select_color_edges.on_change("value", self.on_ui_select_color_edges_change)

        #: Slider for adjusting the size of the edges.
        self.ui_slider_edge_size = bokeh.models.Slider(
            title="Size", start=1.0, end=4, value=1.2, step=0.05,
            show_value=False
        )

        #: Slider for adjusting the opacity of the edges.
        #: This may help to reduce visual clutter in dense graph layouts.
        self.ui_slider_edge_opacity = bokeh.models.Slider(
            title="Opacity", start=0.0, end=1.0, value=1.0, step=0.05,
            show_value=False
        )


        # -- Views --

        VIEWS = [
            "None",
            "SPLOM",
            "Spreadsheet",
            "Graph",
            "Flower",
            "Histogram",
            "Scatter",
            "Map"
        ]

        #: Menu for selecting the view in the left panel.
        self.ui_select_panel_left = bokeh.models.Select(
            title="Plot Type",
            options=VIEWS,
            value="Map", 
            sizing_mode="stretch_width"
        )
        self.ui_select_panel_left.on_change(
            "value", self.on_ui_select_panel_left_change
        )

        #: Menu for selecting the view in the right panel.
        self.ui_select_panel_right = bokeh.models.Select(
            title="Plot Type",
            options=VIEWS,
            value="None", 
            sizing_mode="stretch_width"
        )
        self.ui_select_panel_right.on_change(
            "value", self.on_ui_select_panel_right_change
        )

        #: The :class:`view <ViewBase>` shown in the left panel. 
        self.panel_right: ViewBase = None

        #: The :class:`view <ViewBase>` shown in the right panel.
        self.panel_left: ViewBase = None


        # -- Layout --

        self.layout_sidebar = bokeh.models.Column(
            width=320, 
            sizing_mode="stretch_height"
        )

        self.layout = bokeh.layouts.row([
            self.layout_sidebar
        ], sizing_mode="stretch_both")
        return None
    
    def reload(self):
        """Reloads the data and updates the UI."""
        self.data_provider.reload()
        
        self.df = self.data_provider.df
        self.df_edges = self.data_provider.df_edges

        self.cds.data = self.df
        self.cds_edges.data = self.df_edges

        self.ui_select_color.options = ["None"] + cora.utils.label_columns(self.df)
        self.ui_select_marker.options = ["None"] + cora.utils.label_columns(self.df)
        self.ui_select_color_edges.options = ["None"] + cora.utils.label_columns(self.df_edges)

        self.update_colormap()
        self.update_markermap()
        self.update_edge_colormap()

        if self.panel_left is not None:
            self.panel_left.reload()
        elif self.ui_select_panel_left.value:
            self.panel_left = self.create_view(self.ui_select_panel_left.value)

        if self.panel_right is not None:
            self.panel_right.reload()
        elif self.ui_select_panel_right.value:
            self.panel_right = self.create_view(self.ui_select_panel_right.value)

        self.update_layout_sidebar()
        self.update_layout()

        self.ui_button_reload.disabled = True
        return None
    
    def update_colormap(self):
        """Updates the color column in the column data source."""
        fmap = self.fmap_color
        fmap.df = self.df
        fmap.cds = self.cds
        fmap.column_name = self.ui_select_color.value
        fmap.update_cds()
        return None
    
    def update_markermap(self):
        """Updates the marker column in the column data source."""
        fmap = self.fmap_marker
        fmap.df = self.df
        fmap.cds = self.cds
        fmap.column_name = self.ui_select_marker.value
        fmap.update_cds()
        return None

    def update_edge_colormap(self):
        """Updates the colormap for the edges in the graph view."""
        
        fmap = self.fmap_color_edges
        fmap.df = self.df_edges
        fmap.cds = self.cds_edges
        fmap.column_name = self.ui_select_color_edges.value
        fmap.update_cds()
        return None        
    

    def update_layout_sidebar(self):
        """Updates the layout of the sidebar."""
        children = [
            bokeh.models.Div(text="<strong>Cora</strong>", align="center"),
            self.ui_button_reload,
            bokeh.models.Div(text="<strong>Vertex Appearance</strong>", align="center"),
            self.ui_select_color,
            self.ui_select_marker,
            self.ui_slider_size,
            self.ui_slider_opacity,
            bokeh.models.Div(text="<strong>Edge Appearance</strong>", align="center"),
            self.ui_select_color_edges,
            self.ui_slider_edge_size,
            self.ui_slider_edge_opacity
        ]

        children.append(bokeh.models.Div(text="<strong>Left Panel</strong>", align="center"))
        children.append(self.ui_select_panel_left)
        if self.panel_left is not None and self.panel_left.layout_sidebar.children:
            children.append(self.panel_left.layout_sidebar)

        children.append(bokeh.models.Div(text="<strong>Right Panel</strong>", align="center"))
        children.append(self.ui_select_panel_right)
        if self.panel_right is not None and self.panel_right.layout_sidebar.children:
            children.append(self.panel_right.layout_sidebar)

        self.layout_sidebar.children = children
        return None

    def update_layout(self):
        """Updates the central layout."""
        children = [self.layout_sidebar]

        if self.panel_left is not None:
            children.append(self.panel_left.layout_panel)
        if self.panel_right is not None:
            children.append(self.panel_right.layout_panel)

        self.layout.children = children
        return None
    
    def create_view(self, view_type):
        """Creates a new view instance for the view type 
        and returns it. The view is not yet attached to the 
        application.
        """
        if view_type == "SPLOM":
            from cora.view.splom import SplomView
            return SplomView(self)
        
        if view_type == "Spreadsheet":
            from cora.view.table import TableView
            return TableView(self)
        
        if view_type == "Graph":
            from cora.view.graph import GraphView
            return GraphView(self)
        
        if view_type == "Flower":
            from cora.view.flower import FlowerView
            return FlowerView(self)

        if view_type == "Histogram":
            from cora.view.histogram import HistogramView
            return HistogramView(self)

        if view_type == "Scatter":
            from cora.view.scatter import ScatterView
            return ScatterView(self)

        if view_type == "Map":
            from cora.view.map import MapView
            return MapView(self)
        return None

    # -- UI signals --

    def on_data_provider_change(self):
        """The data frames were modified externally."""
        self.ui_button_reload.disabled = False
        if self.automatic_reload:
            self.reload()
        return None

    def on_ui_button_reload_click(self):
        """The user clicked the reload button."""
        self.reload()
        return None

    def on_ui_select_color_change(self, attr, old, new):
        """The user changed the colormap column."""
        self.update_colormap()
        return None

    def on_ui_select_marker_change(self, attr, old, new):
        """The user changed the glyphmap column."""
        self.update_markermap()
        return None

    def on_ui_select_color_edges_change(self, attr, old, new):
        """The user changed the edge colormap column."""
        self.update_edge_colormap()
        return None

    def on_ui_select_panel_left_change(self, attr, old, new):
        """The user wants to view another plot in the left panel."""
        self.panel_left = self.create_view(new)
        self.update_layout_sidebar()
        self.update_layout()
        return None
    
    def on_ui_select_panel_right_change(self, attr, old, new):
        """The user wants to view another plot in the right panel."""
        self.panel_right = self.create_view(new)
        self.update_layout_sidebar()
        self.update_layout()
        return None

