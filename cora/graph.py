"""
:mod:`cora.graph`

This module implements the graph plot in Bokeh. The vertices are given
as rows in a pandas DataFrame. The edge information, i.e. connectivity
and edge attributes, are given in a separate DataFrame.

The graph layouts are computed with the networkx package.
"""

from pprint import pprint
from typing import List, Literal

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

import pandas as pd
import numpy as np
import networkx as nx


__all__ = [
    "GraphPlot"
]


class GraphPlot(object):
    """Plots the graph and links the vertices with other plots."""

    # TODO: Only the "tap" tool works for selecting edges. All other
    #       tools did not cause an event if a line was in the selection
    #       or crossed.

    LAYOUT_ALGORITHMS = [
        "dot", 
        "twopi", 
        "circo",
        "circular",
        "kamada_kawai",
        "planar",
        "random",
        "shell",
        "spectral",
        "spiral",
        "multipartite",
        "spring"
    ]

    def __init__(self):
        """ """
        #: Pandas DataFrame with the vertex attributes.
        self.df_vertices: pd.DataFrame = None

        #: Pandas DataFrame with the edge information. The
        #: DataFrame has columns `start` and `end` indicating
        #: the edge start and end vertex. All other columns
        #: are additional edge attributes.
        self.df_edges: pd.DataFrame = None

        #: The Bokeh ColumnDataSource wrapping the :attr:`df_vertices`
        #: DataFrame.
        #:
        #: This source also contains columns used by Cora, e.g. the
        #: color for each sample and glyph marker.
        #:
        #: The vertex positions are stored as an additional column
        #: `cora:graph_vertex_position_x` and `cora:graph_vertex_position_y`.
        self.cds_vertices: bokeh.models.ColumnDataSource = None

        #: The Bokeh ColumnDataSource wrapping the :attr:`df_edges`
        #: DataFrame.
        self.cds_edges = bokeh.models.ColumnDataSource = None

        #: The networkx graph used to compute the layout. It is computed
        #: from the :attr:`df_vertices` and :attr:`df_edges` data frames.
        self.nx_graph: nx.DiGraph = None

        #: The layout algorithm used to compute the 
        self.layout_algorithm: Literal["dot", "spring", "circo", "twopi"] = "spring"

        #: The Bokeh plot displaying the graph layout.
        self.figure: bokeh.models.Model = None

        self.renderer_edges: bokeh.models.Model = None
        self.renderer_vertices = bokeh.models.Model = None
        return None

    def update_nx_graph(self):
        """Replaces the networkx graph :attr:`nx_graph` with the current
        graph stored in the pandas DataFrames.
        """
        # We only need the networkx graph to compute the layout.
        self.nx_graph = nx.from_pandas_edgelist(
            self.df_edges, source="source", target="target",
            edge_attr=None, create_using=nx.DiGraph
        )
        return None
        
    def compute_layout(self):
        """Computes the layout using layout algorithm chosen by the user.

        This method is passed as layout algorithm to the bokeh 
        :func:`bokeh.plotting.from_networkx`.

        TODO: Perform this task in a thread or coroutine.
        """
        # Compute the positions of all vertices.
        if self.layout_algorithm == "dot":
            positions = nx.drawing.nx_pydot.graphviz_layout(self.nx_graph, prog="dot")
        elif self.layout_algorithm == "twopi":
            positions = nx.drawing.nx_pydot.graphviz_layout(self.nx_graph, prog="twopi")
        elif self.layout_algorithm == "circo":
            positions = nx.drawing.nx_pydot.graphviz_layout(self.nx_graph, prog="circo")
        elif self.layout_algorithm == "circular":
            positions = nx.drawing.circular_layout(self.nx_graph)
        elif self.layout_algorithm == "kamada_kawai":
            positions = nx.drawing.kamada_kawai_layout(self.nx_graph)
        elif self.layout_algorithm == "planar":
            positions = nx.drawing.planar_layout(self.nx_graph)
        elif self.layout_algorithm == "random":
            positions = nx.drawing.random_layout(self.nx_graph)
        elif self.layout_algorithm == "shell":
            positions = nx.drawing.shell_layout(self.nx_graph)
        elif self.layout_algorithm == "spectral":
            positions = nx.drawing.spectral_layout(self.nx_graph)
        elif self.layout_algorithm == "spiral":
            positions = nx.drawing.spiral_layout(self.nx_graph)
        elif self.layout_algorithm == "multipartite":
            positions = nx.drawing.multipartite_layout(self.nx_graph)
        else:
            positions = nx.drawing.spring_layout(self.nx_graph)

        # Normalize the scale.
        positions = np.array(list(positions.values()))
        positions -= np.mean(positions, axis=0)
        positions /= np.std(positions, axis=0)

        # Update the vertex positions.
        self.cds_vertices.data["cora:vertex_position_x"] = positions[:, 0]
        self.cds_vertices.data["cora:vertex_position_y"] = positions[:, 1]

        # Update the edge lines.
        xs = [
            [positions[edge["source"], 0], positions[edge["target"], 0]]\
            for _, edge in self.df_edges.iterrows()
        ]
        ys = [
            [positions[edge["source"], 1], positions[edge["target"], 1]]\
            for _, edge in self.df_edges.iterrows()
        ]

        self.cds_edges.data["cora:xs"] = xs
        self.cds_edges.data["cora:ys"] = ys

        # Update the edge arrows.
        # XXX: I could not find a way to let Bokeh draw an arrow or line
        # 
        x0 = positions[self.df_edges["source"], 0]
        y0 = positions[self.df_edges["source"], 1]

        x1 = positions[self.df_edges["target"], 0]        
        y1 = positions[self.df_edges["target"], 1]

        dx = x1 - x0
        dy = y1 - y0

        angle = np.arctan2(dy, dx) + np.pi/6.0 

        self.cds_edges.data["cora:arrow_x"] = x1
        self.cds_edges.data["cora:arrow_y"] = y1

        self.cds_edges.data["cora:arrow_x0"] = x0
        self.cds_edges.data["cora:arrow_y0"] = y0

        self.cds_edges.data["cora:arrow_x1"] = x1
        self.cds_edges.data["cora:arrow_y1"] = y1

        self.cds_edges.data["cora:arrow_angle"] = angle
        return positions
    
    def layout_provider(self):
        """Computes a new layout using :meth:`compute_layout` and wraps it 
        in a Bokeh layout provider.
        """
        positions = self.compute_layout()
        provider = bokeh.models.StaticLayoutProvider(graph_layout=positions)
        return provider

    def update_cds(self):
        """Updates the column data source for the edge data."""
        return None

    def create_figure(self):
        """Creates the Bokeh plot showing the graph."""
        # XXX: Bokeh 3.1 does not allow to specifiy another column name
        #      for the edge source and target column. In Bokeh, they are
        #      always called "start" and "end". 
        #      Because the renderes also created somehow new data sources
        #      by themselves, I decided to just reimplemented the partial
        #      network drawing features needed in Cora. Unfortunetly,
        #      this means to forgo the selection tool capabilities.
        p = bokeh.plotting.figure(
            width=600,
            height=600,
            syncable=True,
            tools="pan,lasso_select,box_zoom,wheel_zoom,reset,hover,tap,save,box_select",
            tooltips=[
                ("index", "$index"),
                ("source", "@source"),
                ("target", "@target"),
                ("input:col A", "@{input:col A}")
            ]
        )
        p.xaxis.visible = False
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        # edge arrows
        # This was taken from a Bokeh example "arrow.html" regarding annoations.
        # Unfortunetly, the arrows and addLayout() method glyphs cannot be selected.
        # At least, I didn't make it work. So there's a tradeoff between arrows and
        # multi-line edges.
        # head = bokeh.models.NormalHead(
        #     size=12, 
        #     fill_color="cora:color", 
        #     line_color="transparent"
        # )
        # self.renderer_edges = arrow = bokeh.models.Arrow(
        #     end=head,
        #     x_start="cora:arrow_x0",
        #     y_start="cora:arrow_y0",
        #     x_end="cora:arrow_x1",
        #     y_end="cora:arrow_y1",
        #     line_color="cora:color",
        #     source=self.cds_edges
        # )
        # p.add_layout(arrow)

        # edges
        self.renderer_edges = p.multi_line(
            xs="cora:xs",
            ys="cora:ys",
            line_color="cora:color",
            syncable=True,
            line_cap="round",
            source=self.cds_edges
        )
        
        # vertices        
        self.renderer_vertices = p.scatter(
            x="cora:vertex_position_x",
            y="cora:vertex_position_y",
            source=self.cds_vertices,
            color="cora:color",
            marker="cora:glyph"
        )
        
        # Done.
        self.figure = p
        return None