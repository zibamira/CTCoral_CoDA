"""
:mod:`cora.view.graph`

This module implements the graph plot in Bokeh. The vertices are given
as rows in a pandas DataFrame. The edge information, i.e. connectivity
and edge attributes, are given in a separate DataFrame.

The graph layouts are computed with the networkx package.
"""

from typing import List, Literal

import bokeh
import bokeh.layouts
import bokeh.models
import bokeh.plotting

import pandas as pd
import numpy as np
import networkx as nx

from cora.application import Application
from cora.view.base import ViewBase


__all__ = [
    "GraphView"
]


class GraphView(ViewBase):
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
        "spring"
    ]

    def __init__(self, app: Application):
        """ """        
        super().__init__(app)

        # -- UI sidebar --

        #: Widget for switching between directed and undirected graph 
        #: visulization. 
        #: A directed graph is drawn with arrows but has the drawback
        #: that the selection does not work. So for now we mitigate this
        #: drawback by letting the user choose.
        self.ui_switch_arrow = bokeh.models.Switch(active=False)

        #: Menu for selecting the graph layout algorithm.
        self.ui_select_graph_layout = bokeh.models.Select(
            title="Layout Algorithm",
            options=self.LAYOUT_ALGORITHMS,
            sizing_mode="stretch_width"
        )
        self.ui_select_graph_layout.on_change(
            "value", self.on_ui_select_graph_layout_change
        )

        #: Button for recomputing the graph layout.
        self.ui_button_recompute_graph_layout = bokeh.models.Button(
            label="Recompute layout",
            sizing_mode="stretch_width",
            button_type="primary"
        )
        self.ui_button_recompute_graph_layout.on_click(
            self.on_ui_button_recompute_layout_click
        )

        self.layout_sidebar.children = [
            bokeh.models.Paragraph(text="Draw Arrows"),
            self.ui_switch_arrow,
            self.ui_select_graph_layout,
            self.ui_button_recompute_graph_layout
        ]

        # -- Plot --
        
        #: The networkx graph used to compute the layout. It is computed
        #: from the :attr:`df_vertices` and :attr:`df_edges` data frames.
        self.nx_graph: nx.DiGraph = None

        #: The Bokeh plot displaying the graph layout.
        self.figure: bokeh.models.Model = None

        #: The multiline renderer showing the graph edges.
        self.pedges_line: bokeh.models.Model = None

        #: The arrow layouts for the directed edges.
        self.pedges_arrow: bokeh.models.Model = None

        #: The scatter plot renderer showing the vertices.
        self.pvertices = bokeh.models.Model = None

        # Init.
        self.update_nx_graph()
        self.update_graph_layout()
        self.update_plot()
        return None
    
    
    def on_ui_select_graph_layout_change(self, attr, old, new):
        """The user selected a new graph layout algorithm."""
        self.update_graph_layout()
        self.update_plot()
        return None

    def on_ui_button_recompute_layout_click(self):
        """The user wants to compute the layout again, with a new seed."""
        self.update_graph_layout()
        self.update_plot()
        return None
    

    def update_nx_graph(self):
        """Replaces the networkx graph :attr:`nx_graph` with the current
        graph stored in the pandas DataFrames.
        """
        # We only need the networkx graph to compute the layout.
        self.nx_graph = nx.from_pandas_edgelist(
            self.app.df_edges, source="source", target="target",
            edge_attr=None, create_using=nx.DiGraph
        )
        return None
        
    def update_graph_layout(self):
        """Computes the layout using layout algorithm chosen by the user.

        This method is passed as layout algorithm to the bokeh 
        :func:`bokeh.plotting.from_networkx`.

        TODO: Perform this task in a thread or coroutine.
        """
        # Compute the positions of all vertices.
        layout_algorithm = self.ui_select_graph_layout.value

        if layout_algorithm == "dot":
            positions = nx.drawing.nx_pydot.graphviz_layout(self.nx_graph, prog="dot")
        elif layout_algorithm == "twopi":
            positions = nx.drawing.nx_pydot.graphviz_layout(self.nx_graph, prog="twopi")
        elif layout_algorithm == "circo":
            positions = nx.drawing.nx_pydot.graphviz_layout(self.nx_graph, prog="circo")
        elif layout_algorithm == "circular":
            positions = nx.drawing.circular_layout(self.nx_graph)
        elif layout_algorithm == "kamada_kawai":
            positions = nx.drawing.kamada_kawai_layout(self.nx_graph)
        elif layout_algorithm == "planar":
            positions = nx.drawing.planar_layout(self.nx_graph)
        elif layout_algorithm == "random":
            positions = nx.drawing.random_layout(self.nx_graph)
        elif layout_algorithm == "shell":
            positions = nx.drawing.shell_layout(self.nx_graph)
        elif layout_algorithm == "spectral":
            positions = nx.drawing.spectral_layout(self.nx_graph)
        elif layout_algorithm == "spiral":
            positions = nx.drawing.spiral_layout(self.nx_graph)
        else:
            positions = nx.drawing.spring_layout(self.nx_graph)

        # Normalize the scale.
        positions = np.array(list(positions.values()))
        positions -= np.mean(positions, axis=0)
        positions /= np.std(positions, axis=0)

        # Update the vertex positions.
        self.app.cds.data["cora:vertex_position_x"] = positions[:, 0]
        self.app.cds.data["cora:vertex_position_y"] = positions[:, 1]

        # Update the edge lines.
        xs = [
            [positions[edge["source"], 0], positions[edge["target"], 0]]\
            for _, edge in self.app.df_edges.iterrows()
        ]
        ys = [
            [positions[edge["source"], 1], positions[edge["target"], 1]]\
            for _, edge in self.app.df_edges.iterrows()
        ]

        self.app.cds_edges.data["cora:xs"] = xs
        self.app.cds_edges.data["cora:ys"] = ys

        # Update the edge arrows.
        x0 = positions[self.app.df_edges["source"], 0]
        y0 = positions[self.app.df_edges["source"], 1]

        x1 = positions[self.app.df_edges["target"], 0]        
        y1 = positions[self.app.df_edges["target"], 1]

        dx = x1 - x0
        dy = y1 - y0

        angle = np.arctan2(dy, dx) + np.pi/6.0 

        self.app.cds_edges.data["cora:arrow_x"] = x1
        self.app.cds_edges.data["cora:arrow_y"] = y1

        self.app.cds_edges.data["cora:arrow_x0"] = x0
        self.app.cds_edges.data["cora:arrow_y0"] = y0

        self.app.cds_edges.data["cora:arrow_x1"] = x1
        self.app.cds_edges.data["cora:arrow_y1"] = y1

        self.app.cds_edges.data["cora:arrow_angle"] = angle
        return positions
    
    def update_plot(self):
        """Creates the Bokeh plot showing the graph."""
        # XXX: Bokeh 3.1 does not allow to specifiy another column name
        #      for the edge source and target column. In Bokeh, they are
        #      always called "start" and "end". 
        #      Because the renderes also created somehow new data sources
        #      by themselves, I decided to just reimplemented the
        #      network drawing features needed in Cora. Unfortunetly,
        #      this means to forgo the selection tool capabilities.
        p = bokeh.plotting.figure(
            syncable=True,
            tools="pan,lasso_select,box_zoom,wheel_zoom,reset,hover,tap,save,box_select",
            tooltips=[
                ("index", "$index"),
                ("source", "@source"),
                ("target", "@target"),
                ("input:col A", "@{input:col A}")
            ],
            sizing_mode="scale_both",
            toolbar_location="above",
            title="Graph"
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
        head = bokeh.models.NormalHead(
            size=12, 
            fill_color="cora:edge:color:glyph", 
            line_color="transparent"
        )
        pedges_arrow = bokeh.models.Arrow(
            end=head,
            x_start="cora:arrow_x0",
            y_start="cora:arrow_y0",
            x_end="cora:arrow_x1",
            y_end="cora:arrow_y1",
            line_color="cora:edge:color:glyph",
            source=self.app.cds_edges
        )
        p.add_layout(pedges_arrow)

        pedges_arrow.line_alpha = self.app.ui_slider_edge_opacity.value
        pedges_arrow.line_width = self.app.ui_slider_edge_size.value
        pedges_arrow.end.fill_alpha = self.app.ui_slider_edge_opacity.value
        pedges_arrow.visible = self.ui_switch_arrow.active

        self.app.ui_slider_edge_opacity.js_link("value", pedges_arrow, "line_alpha")
        self.app.ui_slider_edge_size.js_link("value", pedges_arrow, "line_width")
        self.app.ui_slider_edge_opacity.js_link("value", pedges_arrow.end, "fill_alpha")
        self.ui_switch_arrow.js_link("active", pedges_arrow, "visible")

        # edges (multiline)
        pedges_line = p.multi_line(
            xs="cora:xs",
            ys="cora:ys",
            line_color="cora:edge:color:glyph",
            syncable=True,
            line_cap="round",
            source=self.app.cds_edges
        )
        pedges_line.visible = not self.ui_switch_arrow.active

        pedges_line.glyph.line_alpha = self.app.ui_slider_edge_opacity.value
        pedges_line.glyph.line_width = self.app.ui_slider_edge_size.value
        pedges_line.visible = not self.ui_switch_arrow.active

        self.app.ui_slider_edge_opacity.js_link("value", pedges_line.glyph, "line_alpha")
        self.app.ui_slider_edge_size.js_link("value", pedges_line.glyph, "line_width")
        self.ui_switch_arrow.js_on_change(
            "active", bokeh.models.callbacks.CustomJS(
                args=dict(pedges_line=pedges_line), 
                code="pedges_line.visible = !cb_obj.active;"
        ))

        # vertices        
        pvertices = p.scatter(
            x="cora:vertex_position_x",
            y="cora:vertex_position_y",
            source=self.app.cds,
            color="cora:color:glyph",
            marker="cora:marker:glyph"
        )

        pvertices.glyph.size = self.app.ui_slider_size.value
        pvertices.glyph.fill_alpha = self.app.ui_slider_opacity.value
        pvertices.glyph.line_alpha = self.app.ui_slider_opacity.value

        self.app.ui_slider_size.js_link("value", pvertices.glyph, "size")
        self.app.ui_slider_opacity.js_link("value", pvertices.glyph, "fill_alpha")
        self.app.ui_slider_opacity.js_link("value", pvertices.glyph, "line_alpha")

        # Done.
        # self.pedges_arrow = pedges_arrow
        # self.pedges_line = pedges_line
        self.pvertices = pvertices
        self.figure = p

        self.layout_panel = self.figure
        return None
    