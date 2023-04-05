"""
:mod:`cora.app`

Bootstraps and launches the Bokeh application.
"""

import sys
sys.path.insert(1, "/srv/public/bschmitt/py_ipc")

import itertools
import logging
import pathlib
from pprint import pprint   
import shutil
from typing import Dict, List, Optional
import random

import bokeh
import bokeh.plotting
import bokeh.model
import bokeh.models
import bokeh.layouts

import hxipc as amira
import hxipc.data

import natsort

import pandas as pd
import numpy as np
import scipy as sp
import networkx as nx
import sklearn
import sklearn.preprocessing
import umap

from flower import FlowerPlot, FlowerWedge, FlowerCurve
from graph import GraphPlot


class Application(object):
    """Demo application."""

    def __init__(self):
        """ """
        #: The raw pandas DataFrame input enriched 
        #: with the glyph and color column.
        self.df: pd.DataFrame = None

        #: The raw pandas DataFrame input for the edges and 
        #: edge attribute information, enriched with glyph and
        #: styling data by Cora.
        self.df_edges: pd.DataFrame = None

        #: The Bokeh ColumnDataSource wrapping the DataFrame.
        self.cds: bokeh.models.ColumnDataSource = None

        #: The Bokeh ColumnDataSource wrapping the edges DataFrame.
        self.cds_edges: bokeh.models.ColumnDataSource = None

        #: Menu for selecting the x-axis data.
        self.ui_select_x = bokeh.models.Select(title="x-axis")
        
        #: Menu for selecting the y-axis data.
        self.ui_select_y = bokeh.models.Select(title="y-axis")

        #: Menu for selecting the column used for the colormap.
        self.ui_select_color = bokeh.models.Select(title="color")

        #: Menu for selecting the column used for the glyphmap.
        self.ui_select_glyph = bokeh.models.Select(title="glyph")

        #: Slider for adjusting the glyph size.
        self.ui_slider_size = bokeh.models.Slider(
            title="size", start=1, end=20, value=8, step=1
        )

        #: Slider for adjusting the opacity.
        self.ui_slider_opacity = bokeh.models.Slider(
            title="opacity", start=0.0, end=1.0, value=1.0, step=0.05
        )

        #: Menu for selecting the graph layout algorithm.
        self.ui_select_graph_layout = bokeh.models.Select(
            title="Graph Layout",
            options=["dot", "circo", "twopi", "spring"]
        )

        #: Button for recomputing the graph layout.
        self.ui_button_recompute_graph_layout = bokeh.models.Button(
            label="Refresh layout"
        )

        #: Button for reloading (generating) the data.
        self.ui_button_reload = bokeh.models.Button(label="Reload")

        #: The plot figure.
        self.figure: bokeh.models.Model = None

        #: The plot figure displaying the flower/star visualization.
        self.figure_flower: FlowerPlot = None

        #: The plot figure displaying the graph.
        self.figure_graph: GraphPlot = None

        #: The layout for all UI control widgets and some help 
        #: information.
        self.layout_sidebar: bokeh.models.Column = None

        #: The layout containing the central view, i.e. the plots.
        self.layout_central: bokeh.models.Row = None

        #: The main layout which just combines the individual layouts.
        self.layout: bokeh.models.Row = None

        # Initialise everything.
        self.update_df()
        self.update_ui()
        self.update_colormap()
        self.update_glyphmap()
        self.update_cds()
        self.update_cds_edges()
        self.update_plot()
        self.update_flower_plot()
        self.update_graph_plot()

        self.layout = bokeh.layouts.row([
            self.layout_sidebar, 
            self.layout_central
        ])
        return None
    
    def update_df(self):
        """Creates random data samples."""
        nsamples = 100
        self.df = pd.DataFrame.from_dict({
            "input:col A": np.random.random(nsamples),
            "input:col B": np.random.standard_normal(nsamples),
            "input:col C": np.random.random(nsamples),
            "input:col D": np.random.random(nsamples),
            "input:col E": np.random.random(nsamples),
            "input:col F": np.random.random(nsamples),
            "input:label A": random.choices(["A1", "A2"], k=nsamples),
            "input:label B": random.choices(["B1", "B2"], k=nsamples),
            "cora:color": random.choices(["red", "blue", "green"], k=nsamples),
            "cora:glyph": random.choices(["asterisk", "circle", "cross", "diamond"], k=nsamples)
        })

        # Generate a random graph for testing.
        self.df_edges = nx.to_pandas_edgelist(
            G=nx.random_regular_graph(d=2, n=nsamples),
            source="source", target="target"
        )
        self.df_edges["cora:color"] = random.choices(["red", "black"], k=len(self.df_edges))
        return None
    
    def update_ui(self):
        """Updates the choices in the control widgets depending
        on the available column data.
        """
        data_columns = [
            name \
            for name in self.df.columns \
            if not name.startswith("cora:")
        ]
        scalar_columns = [
            name \
            for name in data_columns \
            if pd.api.types.is_numeric_dtype(self.df[name].dtype)
        ]
        categorical_columns = [
            name \
            for name in data_columns \
            if pd.api.types.is_string_dtype(self.df[name].dtype)
        ]
        integral_columns = [
            name \
            for name in data_columns \
            if pd.api.types.is_integer_dtype(self.df[name].dtype)
        ]

        label_columns = categorical_columns + integral_columns

        self.ui_select_x.options = scalar_columns
        self.ui_select_y.options = scalar_columns
        self.ui_select_color.options = [""] + label_columns
        self.ui_select_glyph.options = [""] + label_columns

        # plot data
        if self.ui_select_x.value not in scalar_columns:
            self.ui_select_x.value = scalar_columns[0]
        if self.ui_select_y.value not in scalar_columns:
            self.ui_select_y.value = scalar_columns[1]

        # visual attributes
        if self.ui_select_color.value not in label_columns:
            self.ui_select_color.value = label_columns[0]
        if self.ui_select_glyph.value not in label_columns:
            self.ui_select_glyph.value = label_columns[1]
        
        # create the sidebar and connect the callbacks
        if self.layout_sidebar is None:
            self.layout_sidebar = bokeh.layouts.column([
                self.ui_select_x,
                self.ui_select_y,
                self.ui_select_color,
                self.ui_select_glyph,
                self.ui_slider_size,
                self.ui_slider_opacity,
                self.ui_select_graph_layout,
                self.ui_button_recompute_graph_layout,
                self.ui_button_reload
            ])

            # Connect signals and callbacks.
            self.ui_select_x.on_change("value", self.on_ui_select_x_change)
            self.ui_select_y.on_change("value", self.on_ui_select_y_change)
            self.ui_select_color.on_change("value", self.on_ui_select_color_change)
            self.ui_select_glyph.on_change("value", self.on_ui_select_glyph_change)
            self.ui_select_graph_layout.on_change("value", self.on_ui_select_graph_layout_change)
            self.ui_button_recompute_graph_layout.on_click(self.on_ui_graph_recompute_graph_layout_click)
            self.ui_button_reload.on_click(self.on_ui_button_reload_click)
        return None
    
    def update_colormap(self):
        """Updates the color column in the column data source."""
        nrows = len(self.df)
        column = self.ui_select_color.value

        if column not in self.df:
            self.df["cora:color"] = ["blue" for i in range(nrows)]
            return None

        factors = np.unique(self.df[column])
        factors = list(natsort.natsorted(factors))

        palette = itertools.cycle(["blue", "green", "yellow", "red", "black", "grey"])
        colormap = {factor: color for factor, color in zip(factors, palette)}

        self.df["cora:color"] = [colormap[factor] for factor in self.df[column]]
        return None
    
    def update_glyphmap(self):
        """Updates the glyph column in the column data source."""
        nrows = len(self.df)
        column = self.ui_select_glyph.value

        if column not in self.df:
            self.df["cora:glyph"] = ["circle" for i in range(nrows)]
            return None

        factors = np.unique(self.df[column])
        factors = list(natsort.natsorted(factors))

        markers = itertools.cycle(["asterisk", "circle", "cross", "diamond"])
        glyphmap = {factor: marker for factor, marker in zip(factors, markers)}

        self.df["cora:glyph"] = [glyphmap[factor] for factor in self.df[column]]
        return None
    
    def update_cds(self):
        """Updates the ColumnDataSource with the content in the pandas DataFrame."""
        if not self.cds:
            self.cds = bokeh.models.ColumnDataSource(self.df)
            self.cds.selected.on_change("indices", self.on_cds_selection_change)
        else:
            self.cds.data = self.df
        return None

    def update_cds_edges(self):
        """Updates the ColumnDataSource for the edge information."""
        if not self.cds_edges:
            self.cds_edges = bokeh.models.ColumnDataSource(self.df_edges)
            self.cds_edges.selected.on_change("indices", self.on_cds_edges_selection_change)
        else:
            self.cds_edges.data = self.df_edges
        return None

    def update_plot(self):
        """Updates the plot based on the current user settings."""   
        colx = self.ui_select_x.value
        coly = self.ui_select_y.value

        self.figure = bokeh.plotting.figure(
            width=600, height=600, syncable=True,
            tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover"
        )
        s = self.figure.scatter(
            x=colx, y=coly, syncable=True, source=self.cds,
            color="cora:color", marker="cora:glyph",
            size=self.ui_slider_size.value,
            alpha=self.ui_slider_opacity.value
        )

        self.ui_slider_size.js_link("value", s.glyph, "size")
        self.ui_slider_opacity.js_link("value", s.glyph, "fill_alpha")
        self.ui_slider_opacity.js_link("value", s.glyph, "line_alpha")

        # Create the layout if not yet done.
        if self.layout_central is None:
            self.layout_central = bokeh.layouts.row([])

        # Replace the old plot.
        self.update_layout_central()
        return None
    
    def update_flower_plot(self):
        """Updates the flower plot based on the current selection."""  

        if not self.figure_flower:
            # Filter the input columns with scalar values
            # and compute a description of the whole dataset.
            scalar_columns = [
                name \
                for name in self.df.columns \
                if not name.startswith("cora:") and pd.api.types.is_numeric_dtype(self.df[name].dtype)
            ]
            df = self.df[scalar_columns]

            self.figure_flower = FlowerCurve()
            self.figure_flower.set_df(df)
            self.figure_flower.set_selection(indices=[])
            self.figure_flower.update_cds()
            self.figure_flower.create_figure()

            self.update_layout_central()
        else:
            indices = self.cds.selected.indices
            self.figure_flower.set_selection(indices)
            self.figure_flower.update_cds()
        return None

    def update_graph_plot(self):
        """Updates the graph plot."""
        if not self.figure_graph:
            self.figure_graph = GraphPlot()

            p = self.figure_graph
            p.df_vertices = self.df
            p.df_edges = self.df_edges
            p.cds_vertices = self.cds
            p.cds_edges = self.cds_edges
            p.layout_algorithm = self.ui_select_graph_layout.value
            
            p.update_nx_graph()
            p.compute_layout()
            p.create_figure()

            # TODO: Make the application available to all views and let them
            #       access the global controls.
            self.ui_slider_size.js_link("value", p.renderer_vertices.glyph, "size")
            self.ui_slider_opacity.js_link("value", p.renderer_vertices.glyph, "fill_alpha")
            self.ui_slider_opacity.js_link("value", p.renderer_vertices.glyph, "line_alpha")
            
            p.renderer_vertices.glyph.size = self.ui_slider_size.value
            p.renderer_vertices.glyph.fill_alpha = self.ui_slider_opacity.value
            p.renderer_vertices.glyph.line_alpha = self.ui_slider_opacity.value

            self.ui_slider_opacity.js_link("value", p.renderer_edges.glyph, "line_alpha")

            p.renderer_edges.glyph.line_alpha = self.ui_slider_opacity.value

            self.update_layout_central()
        return None
    
    def update_layout_central(self):
        """Updates the plots in the central layout."""
        children = []
        if self.figure is not None:
            children.append(self.figure)
        # if self.figure_flower is not None:
        #     children.append(self.figure_flower.figure)
        if self.figure_graph is not None:
            print("graph in layout")
            children.append(self.figure_graph.figure)

        self.layout_central.children = children
        return None
    
    def on_ui_select_x_change(self, attr, old, new):
        """The user changed the x data column."""
        self.update_plot()
        return None

    def on_ui_select_y_change(self, attr, old, new):
        """The user changed the y data column."""
        self.update_plot()
        return None
    
    def on_ui_select_color_change(self, attr, old, new):
        """The user changed the colormap column."""
        self.update_colormap()
        self.cds.data["cora:color"] = self.df["cora:color"]
        return None

    def on_ui_select_glyph_change(self, attr, old, new):
        """The user changed the glyphmap column."""
        print("glyph change.")
        self.update_glyphmap()
        self.cds.data["cora:glyph"] = self.df["cora:glyph"]
        return None
    
    def on_ui_button_reload_click(self):
        """The user clicked the reload button."""
        self.update_df()
        self.update_ui()
        self.update_colormap()
        self.update_glyphmap()
        self.update_cds()
        self.update_cds_edges()
        # self.update_plot()
        return None
    
    def on_cds_selection_change(self, attr, old, new):
        """The selection changed."""
        print("vertex selection changed.")
        self.update_flower_plot()
        return None
    
    def on_cds_edges_selection_change(self, attr, old, new):
        """The selection changed."""
        print("edges selection changed.")
        return None

    def on_ui_select_graph_layout_change(self, attr, old, new):
        """The graph layout algorithm changed."""    
        self.figure_graph.layout_algorithm = new
        self.figure_graph.compute_layout()
        return None
    
    def on_ui_graph_recompute_graph_layout_click(self):
        """The user wants to refresh the layout."""
        self.figure_graph.compute_layout()
        return None
    

app = Application()
doc = bokeh.plotting.curdoc()
doc.add_root(app.layout)
doc.set_title("Cora - The Coral Explorer")