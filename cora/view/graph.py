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
from cora.tools.graph_tools import (
    make_ancestor_tool, 
    make_descendant_tool
)
from cora.view.base import ViewBase
import cora.utils


__all__ = [
    "GraphView"
]


class GraphView(ViewBase):
    """Plots the graph and links the vertices with other plots."""

    # XXX: Only the "tap" tool works for selecting edges. All other
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

        #: Menu for selecting the column with the start indices.
        self.ui_select_column_source = bokeh.models.Select(
            title="Source Column",
            sizing_mode="stretch_width"
        )

        # Menu for selectin the column with the target indices.
        self.ui_select_column_target = bokeh.models.Select(
            title="Target Column",
            sizing_mode="stretch_width"
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
            self.ui_select_column_source,
            self.ui_select_column_target,
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
        return None
    

    def reload_df(self):
        """Reload the graph and recompute the layout."""
        # Candidates for all source and target columns identifiying the 
        # edge orientation.
        integral_columns = cora.utils.integral_columns(self.app.df_edges)
        self.ui_select_column_source.options = integral_columns
        self.ui_select_column_target.options = integral_columns

        # Check if the currently selected source and target columns
        # are still available and set them to default values if not.
        source_column = self.ui_select_column_source.value
        target_column = self.ui_select_column_target.value        
        if not (source_column in integral_columns and target_column in integral_columns):
            source_column, target_column = self.detect_source_target_columns()
            self.ui_select_column_source.value = source_column
            self.ui_select_column_target.value = target_column

        # Update the internal nx graph and recompute the layout if the graph
        # changed.
        changed = self.update_nx_graph()

        # Choose the default layout if this is the first reload.
        if self.nx_graph and self.ui_select_graph_layout.value not in self.LAYOUT_ALGORITHMS:
            if nx.is_forest(self.nx_graph):
                self.ui_select_graph_layout.value = "dot"
            else:
                self.ui_select_graph_layout.value = "spring"
                
        # Recompute the layout.
        if changed:
            self.update_graph_layout()
        return None    
    
    def reload_cds(self):
        """Creates the graph plot if not yet done."""
        if self.figure is None:
            self.create_plot()
        return None
    

    def on_ui_select_graph_layout_change(self, attr, old, new):
        """The user selected a new graph layout algorithm."""
        if self.is_reloading:
            return None
        
        self.update_graph_layout()
        return None

    def on_ui_button_recompute_layout_click(self):
        """The user wants to compute the layout again, with a new seed."""
        if self.is_reloading:
            return None
        
        self.update_graph_layout()
        return None
    
    
    def detect_source_target_columns(self):
        """Detect the *source* and *target* columns in the edge data frame
        automatic by trying it out frequently used names.
        """
        columns = self.app.df_edges.columns

        # Deal with case sensitivity by working only on lower case names.
        columns_lc = {column.lower(): column for column in columns}

        # Split the columns into prefix and name.
        prefixes_lc = [column_lc.rsplit(":", 1)[0] for column_lc in columns_lc.keys()]
        
        # Common column names (without prefix) for start and end columns
        # of edges.
        names_lc = [
            ("source", "target"),
            ("start", "end"),
            ("startnode.id", "endnode.id")
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

    def update_nx_graph(self):
        """Replaces the networkx graph :attr:`nx_graph` with the current
        graph stored in the pandas DataFrames.

        This method returns *True* if the graph changed, i.e. is not 
        isomorphic to the current grap.
        """
        source_column = self.ui_select_column_source.value
        target_column = self.ui_select_column_target.value
        if not (source_column and target_column):
            print(
                "Could not detect the source and target column of the edges."
                " Please state them explicitly or use a standard."
            )
            return None

        # The networkx graph is only used to compute the layout. The 
        # attributes are not not needed.
        new_graph = nx.from_pandas_edgelist(
            self.app.df_edges, 
            source=source_column, 
            target=target_column,
            create_using=nx.DiGraph
        )
        
        # Check if the graph changed.
        changed = self.nx_graph is None \
            or not nx.is_isomorphic(self.nx_graph, new_graph)
                
        self.nx_graph = new_graph
        return changed
        
    def update_graph_layout(self):
        """Computes the layout using layout algorithm chosen by the user.

        This method is passed as layout algorithm to the bokeh 
        :func:`bokeh.plotting.from_networkx`.

        TODO: Perform this task in a thread or coroutine.
        """
        source_column = self.ui_select_column_source.value
        target_column = self.ui_select_column_target.value

        if not (source_column in self.app.df_edges):
            print(f"The source column {source_column} is not in the dataframe.")
            return None
        if not (target_column in self.app.df_edges):
            print(f"The target column {target_column} is not in the dataframe.")
            return None

        df_source = self.app.df_edges[source_column]
        df_target = self.app.df_edges[target_column]

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
        # XXX: Some layout algorithms did not return positions for vertices with no adjacent edges.
        #      Since we need to draw *all* vertices, I opted for a quick fix placing them at the same position.
        #      Eventually, they should be drawn transparent or a proper layout with them should be computed.
        positions = np.array([
            positions[irow] if irow in positions else [-1.0, 0.0] \
            for irow, _ in self.app.df.iterrows()
        ])
        positions -= np.mean(positions, axis=0)
        positions /= np.std(positions, axis=0)

        # Update the edge lines.
        xs = [
            [positions[source_id, 0], positions[target_id, 0]]\
            for source_id, target_id in zip(df_source, df_target)
        ]
        ys = [
            [positions[source_id, 1], positions[target_id, 1]]\
            for source_id, target_id in zip(df_source, df_target)
        ]   

        # Update the edge arrows.
        x0 = positions[df_source, 0]
        y0 = positions[df_source, 1]

        x1 = positions[df_target, 0]        
        y1 = positions[df_target, 1]

        dx = x1 - x0
        dy = y1 - y0

        angle = np.arctan2(dy, dx) + np.pi/6.0 

        # Update the edge data.
        df_edges = self.app.df_edges
        df_edges["cora:graph:xs"] = xs
        df_edges["cora:graph:ys"] = ys
        df_edges["cora:graph:arrow_x0"] = x0
        df_edges["cora:graph:arrow_y0"] = y0
        df_edges["cora:graph:arrow_x1"] = x1
        df_edges["cora:graph:arrow_y1"] = y1
        df_edges["cora:graph:arrow_angle"] = angle

        # Update the vertex data.
        df_vertices = self.app.df
        df_vertices["cora:graph:x"] = positions[:, 0]
        df_vertices["cora:graph:y"] = positions[:, 1]

        # Schedule a column data source update.
        self.app.push_df_to_cds(vertex=True, edge=True)
        return None
    
    def create_plot(self):
        """Creates the Bokeh plot showing the graph using the layout computed
        earlier with :meth:`update_graph_layout`.

        The figure needs to be created only once since all render information
        are stored in the column data source.
        """        
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
            ],
            sizing_mode="scale_both",
            toolbar_location="above",
            title="Graph"
        )
        p.xaxis.visible = False
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        # ancestor_tool = AncestorTool()
        # ancestor_tool.source_vertices = self.app.cds
        # ancestor_tool.source_edges = self.app.cds_edges

        ancestor_tool = make_ancestor_tool(
            colname_source=self.ui_select_column_source.value,
            colname_target=self.ui_select_column_target.value,
            cds_vertices=self.app.cds,
            cds_edges=self.app.cds_edges
        )
        descendant_tool = make_descendant_tool(
            colname_source=self.ui_select_column_source.value,
            colname_target=self.ui_select_column_target.value,
            cds_vertices=self.app.cds,
            cds_edges=self.app.cds_edges
        )
        p.add_tools(ancestor_tool)
        p.add_tools(descendant_tool)

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
            x_start="cora:graph:arrow_x0",
            y_start="cora:graph:arrow_y0",
            x_end="cora:graph:arrow_x1",
            y_end="cora:graph:arrow_y1",
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
            xs="cora:graph:xs",
            ys="cora:graph:ys",
            line_color="cora:edge:color:glyph",
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
            x="cora:graph:x",
            y="cora:graph:y",
            color="cora:color:glyph",
            marker="cora:marker:glyph",
            line_color="gray",
            source=self.app.cds
        )

        pvertices.glyph.size = self.app.ui_slider_size.value
        pvertices.glyph.fill_alpha = self.app.ui_slider_opacity.value
        pvertices.glyph.line_alpha = self.app.ui_slider_opacity.value

        self.app.ui_slider_size.js_link("value", pvertices.glyph, "size")
        self.app.ui_slider_opacity.js_link("value", pvertices.glyph, "fill_alpha")
        self.app.ui_slider_opacity.js_link("value", pvertices.glyph, "line_alpha")

        # Done.
        self.figure = p
        self.pedges_line = pedges_line
        self.pedges_arrow = pedges_arrow
        self.pvertices = pvertices

        self.layout_panel = self.figure
        return None