"""
:mod:`splom`

This module implements a new SPLOM (scatter plot matrix) in Bokeh,
given a Pandas DataFrame and a list of columns.
"""

import functools
import itertools
import logging
import pathlib
from pprint import pprint
from typing import List, Optional

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

import pandas as pd
import numpy as np
import networkx as nx
import natsort


__all__ = [
    "Graph"
]


def to_pandas_edgelist(nx_graph: nx.Graph):
    """Converts the graph into a pandas DataFrame containing
    the edges and edge attributes.
    """
    df = nx.to_pandas_edgelist(nx_graph)
    df.rename(columns={"source": "start", "target": "end"}, inplace=True)
    return df


def to_pandas_vertexlist(nx_graph: nx.Graph):
    """Converts the graph int a pandas DataFrame containg
    the vertices and vertex attributes.
    """
    # Get all available attributes.
    attribute_names = set()
    for node, attributes in nx_graph.nodes.items():
        attribute_names.update(attributes.keys())

    # Create the data columns.
    data = {
        name: [] for name in attribute_names
    }

    for node, attributes in nx_graph.nodes.items():
        for name in attribute_names:
            value = attributes.get(name)
            if value is not None and isinstance(value, np.ndarray) and value.size == 1:
                value = value.item()
            data[name].append(value)
            
    # Create the DataFrame.
    df = pd.DataFrame(data)
    return df


class Graph(object):
    """Wraps the graph visualization of a coral tree.
    
    TODO: Put the rendering code here.
    TODO: Add the UI widgets for choosing the layout and recomouting it.
    """

    def __init__(self):
        """
        """
        # The networkx graph synchronized with Amira.
        self.nx_graph: nx.DiGraph = None

        # Pandas DataFrames corresponding to the vertices and edges of the graph.
        self.vertex_df: pd.DataFrame = None
        self.edge_df: pd.DataFrame = None

        # Bokeh ColumnDataSource corresponding to the vertices and edges of the graph.
        self.vertex_source: bokeh.models.ColumnDataSource = None
        self.edge_source: bokeh.models.ColumnDataSource = None

        # Colormap
        self.colormap_column_name = ""
        self.colormap = "blue"

        self._colormap_unique_labels = None
        self._colormap_label_ids = None
        self._colormap_label_to_id = None

        # Choose a layout algorithm for both 
        self.layout_algorithm: str = "dot"

        # The actual Bokeh renderer and plot.
        self.graph_renderer = None
        self.plot = None
        return None

    def init(self):
        """Creates the plot and all resources it depends on."""
        self.init_colormap()
        self.init_glyphmap()
        self.init_plot()
        return None
    
    def init_colormap(self):
        """Initializes the colormap for the vertices. The vertices
        are colored according to the given vertex attribute.
        """
        if not self.colormap_column_name:
            return None

        # The factors in a factor cmap can only be strings. So if our factor cmap
        # is based on integer ids (classes), then we have to convert them to strings
        # first.
        #
        # This is done by collecting all possible integer values first, sorting them
        # and assigning them a new, continous number. These numbers are then converted
        # to strings and added as a new column to the data source.

        labels = self.vertex_df[self.colormap_column_name]
        self._colormap_unique_labels = np.array(natsort.natsorted(np.unique(labels)))
        self._colormap_label_to_id = {label: i for i, label in enumerate(self._colormap_unique_labels)}

        self._colormap_factors = [str(i) for i in range(len(self._colormap_unique_labels))]
        self._colormap_factor_column = [str(self._colormap_label_to_id[label]) for label in labels]
        self.vertex_source.add(self._colormap_factor_column, "_colormap_labels")

        # Repeat the palette, so that it has enough colors for all labels.
        palette = itertools.cycle(bokeh.palettes.Spectral11)
        palette = [next(palette) for _ in self._colormap_unique_labels]

        # Create the actual factor colormap.
        self.colormap = bokeh.transform.factor_cmap(
            "_colormap_labels", palette=palette, factors=self._colormap_factors
        )
        return None
    
    def init_glyphmap(self):
        """Initializes the map used for the vertex glyphs."""
        return None
    
    def recompute_layout(self, graph, *args, **kargs):
        """Recomputes the layout using layout algorithm chosen by the user.

        This method is passed as layout algorithm to the bokeh 
        :func:`bokeh.plotting.from_networkx`.
        """
        # Compute the positions of all vertices.
        if self.layout_algorithm == "dot":
            positions = nx.drawing.nx_pydot.graphviz_layout(graph, prog="dot")
        elif self.layout_algorithm == "twopi":
            positions = nx.drawing.nx_pydot.graphviz_layout(graph, prog="twopi")
        elif self.layout_algorithm == "circo":
            positions = nx.drawing.nx_pydot.graphviz_layout(graph, prog="circo")
        else:
            positions = nx.drawing.spring_layout(graph)

        # Normalize the positions to be centered around the origin
        # with standard deviation of the distance being 1.0.
        positions = np.array(list(positions.values()))
        positions -= np.mean(positions, axis=0)
        positions /= np.std(positions, axis=0)
        positions = {i: positions[i] for i in range(positions.shape[0])}
        return positions

    def layout_provider(self):
        """
        """
        layout = self.recompute_layout(self.nx_graph)
        provider = bokeh.models.StaticLayoutProvider(graph_layout=layout)
        return provider

    # def init_plot(self):
    #     p = bokeh.plotting.figure(
    #         tooltips=[
    #             ("index", "@index"),
    #             ("label", "@label"),
    #             ("generation", "@shortest_distance")
    #         ],
    #         sizing_mode="scale_both",
    #         match_aspect=True,
    #         x_axis_location=None,
    #         y_axis_location=None
    #     )
    #     positions = self.recompute_layout(self.nx_graph)
    #     p.circle(x=positions[:, 0], y=positions[:, 1], size=24)
    #     # Create a line for each edge.
    #     lines_x = []
    #     lines_y = []
    #     for index, row in self.edge_df.iterrows():
    #         start_pos = positions[row["start"]]
    #         end_pos = positions[row["end"]] 
    #         lines_x.append((start_pos[0], end_pos[0]))
    #         lines_y.append((start_pos[1], end_pos[1]))
    #     p.multi_line(xs=lines_x, ys=lines_y)
    #     self.figure = p
    #     return None
    
    def init_plot(self):
        """Creates the figure with the graph plot."""    
        # Create the edge renderer.
        edge_renderer = bokeh.models.GlyphRenderer(data_source=self.edge_source)
        edge_renderer.glyph = bokeh.models.MultiLine(
            line_width=2, line_color="grey"
        )
        edge_renderer.hover_glyph = bokeh.models.MultiLine(
            line_width=4, line_color="black"
        )

        # Create the node renderer.
        node_renderer = bokeh.models.GlyphRenderer(data_source=self.vertex_source)
        node_renderer.glyph = bokeh.models.Circle(
            size=24, fill_color=self.colormap, 
            line_width=2, line_color="grey"
        )
        node_renderer.hover_glyph = bokeh.models.Circle(
            size=24, fill_color=self.colormap, 
            line_width=4, line_color="black"
        )

        # Create the graph renderer with the user chosen layout algorithm.
        self.graph_renderer = bokeh.models.GraphRenderer(
            layout_provider=self.layout_provider(),
            node_renderer=node_renderer,
            edge_renderer=edge_renderer
        )
        self.graph_renderer.selection_policy = bokeh.models.NodesAndLinkedEdges()
        self.graph_renderer.inspection_policy = bokeh.models.NodesAndLinkedEdges()

        # Create the actual plot.
        p = bokeh.plotting.figure(
            tooltips=[
                ("index", "@index"),
                ("label", "@label"),
                ("generation", "@shortest_distance")
            ],
            sizing_mode="scale_both",
            match_aspect=True,
            x_axis_location=None,
            y_axis_location=None
        )
        p.grid.grid_line_color = None
        p.renderers.append(self.graph_renderer)

        self.figure = p
        return None

def plot(
    nx_graph: nx.DiGraph,
    vertex_df: pd.DataFrame,
    vertex_source: bokeh.models.ColumnDataSource,
    edge_df: pd.DataFrame,
    edge_source: bokeh.models.ColumnDataSource
    ):
    """Computes a graph layout and shows the graph in a plot."""
    graph = Graph()
    graph.colormap_column_name = "shortest_distance"
    graph.layout_algorithm = "dot"
    graph.nx_graph = nx_graph
    graph.vertex_df = vertex_df
    graph.vertex_source = vertex_source
    graph.edge_df = edge_df
    graph.edge_source = edge_source
    graph.init()
    return graph.figure


def vertex_table(
    vertices: bokeh.models.ColumnDataSource,
    columns: List[str]
    ):
    """Shows the vertex attributes of the graph in a table."""
    if not columns:
        columns = vertices.column_names

    columns = [
        bokeh.models.TableColumn(field=name, title=name) \
        for name in columns
    ]
    table = bokeh.models.DataTable(
        source=vertices, 
        width=400, 
        columns=columns, 
        sizing_mode="stretch_both"
    )
    return table


def edge_table(
    edges: bokeh.models.ColumnDataSource,
    columns: List[str]
    ):
    """Shows the edge attributes of the graph in a table."""
    if not columns:
        columns = edges.column_names
        
    columns = [
        bokeh.models.TableColumn(field=name, title=name) \
        for name in columns
    ]
    table = bokeh.models.DataTable(
        source=edges, 
        width=400, 
        columns=columns, 
        sizing_mode="stretch_both"
    )
    return table