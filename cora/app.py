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

import bokeh
import bokeh.plotting
import bokeh.model
import bokeh.models
import bokeh.layouts

import hxipc as amira
import hxipc.data

import pandas as pd
import numpy as np
import scipy as sp
import networkx as nx
import sklearn
import sklearn.preprocessing
import umap

import features
import cluster

# Logger configuration
def init_logging():
    formatter = logging.Formatter("{levelname} :: {filename}:{lineno} :: {message}", style="{")

    console = logging.StreamHandler(stream=sys.stderr)
    console.setLevel(logging.NOTSET)
    console.setFormatter(formatter)

    logging.basicConfig(handlers=[console], level=logging.INFO)
    return None
    
init_logging()

# Path configuration
this_dir = pathlib.Path(__file__).parent
instance_dir = this_dir.parent / "instance"
data_dir = instance_dir / "data"

# Restore the work data.
logging.info("Restoring original data ...")
shutil.copytree(instance_dir / "data_copy", instance_dir / "data", dirs_exist_ok=True)

# Amira resources
logging.info("Loading shared Amira resources.")
ipc_connectivity = amira.data.graph(data_dir / "instance_connectivity.json", mode="r")
ipc_features = amira.data.spreadsheet(data_dir / "instance_features.json", mode="r")
ipc_segmentation = amira.data.array(data_dir / "instance_segmentation.json", mode="r")

# Feature plot
logging.info("Creating SPLOM ...")

# Create some fake labels for testing.
ipc_features.df["label"] = np.random.randint(0, 5, ipc_features.df.shape[0]).astype(str)

# Choose the currently active columns.
features_df = ipc_features.df
features_columns = ["Volume3d", "VoxelFaceArea", "Anisotropy", "Flatness", "Elongation", "label"]
features_bokeh = bokeh.models.ColumnDataSource(features_df)

# Create an IPC sink for the selection mask.
print("Creating output sinks.")
ipc_selection = amira.data.array(
    data_dir / "mask.json", mode="w", shape=ipc_segmentation.array.shape,
    bounding_box=ipc_segmentation.bounding_box, dtype=np.uint8
)


import time
import threading


_last_update = time.time()
def update_thread():
    """Checks periodically if the current Bokeh selection changed
    and propagates the changes to Amira.
    """
    global _last_update
    while True:
        print("CHECK FIRE")
        if _last_update is None:
            return None
        elif abs(time.time() - _last_update) > 0.5:
            ipc_selection.ipc_write()
            _last_update = None
            print("FIRE")
        time.sleep(0.5)
    return None


# ---- graph ----


def graph():
    """Draws the coral connectivity graph. The result is a dendrogram."""
    nxgraph = ipc_connectivity.graph

    # Layout
    def scale_layout(flayout):
        """Decorates a layout function so that the returned positions
        will be normalized, i.e. they are centered at the origin and
        scaled to [-1, 1]^2.
        """
        def wrapped(*args, **kargs):
            pos = flayout(*args, **kargs)
            pos = np.array(list(pos.values()))
            pos -= np.mean(pos, axis=0)
            pos /= np.std(pos, axis=0)
            pos = {i: pos[i] for i in range(pos.shape[0])}
            return pos
        return wrapped
        
    layout = "dot"
    if layout == "dot":
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.nx_pydot.graphviz_layout), 
            prog="dot"
        )
    elif layout == "twopi":
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.nx_pydot.graphviz_layout), 
            prog="twopi"
        )
    elif layout == "circo":
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.nx_pydot.graphviz_layout), 
            prog="circo"
        )
    else:
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.spring_layout)
        )

    source_nodes = graph.node_renderer.data_source
    source_edges = graph.edge_renderer.data_source

    # Colormap
    #
    # * factor_cmap: the label must be of type "str"
    # * factor_cmap: the color palette must be large enogough
    labels = [str(e[0]) for e in source_nodes.data["label"]]
    labels_unique = np.sort(np.unique(labels))

    palette = itertools.cycle(bokeh.palettes.Spectral11)
    palette = [next(palette) for i in labels_unique]

    colormap = bokeh.transform.factor_cmap(
        "label", palette=palette, factors=labels_unique,
    )

    # node renderer

    source_nodes.data["label"] = labels
    graph.node_renderer.glyph = bokeh.models.Ellipse(
        width=0.2, height=0.2, fill_color=colormap
    )
    graph.inspection_policy = bokeh.models.NodesOnly()

    # edge renderer

    graph.edge_renderer.selection_glyph = bokeh.models.MultiLine(line_color="blue", line_width=5)
    graph.edge_renderer.hover_glyph = bokeh.models.MultiLine(line_color="red", line_width=10)

    # plot 
    # x_range = bokeh.models.Range1d(-2.0, 2.0, bounds=())
    # x_axis = bokeh.models.LinearAxis()

    p = bokeh.plotting.figure(
        tooltips=[
            ("index", "@index"),
            ("label", "@label"),
            ("generation", "@shortest_distance")
        ],
        sizing_mode="scale_both",
        match_aspect=True,
        x_axis_location=None,
        y_axis_location=None,

    )
    p.grid.grid_line_color = None
    p.xaxis.bounds = ()
    p.renderers.append(graph)
    return p


def graph_vertex_table():
    """Shows the vertex attributes of the graph."""
    df = nx.to_pandas_edgelist(ipc_connectivity.graph)
    source = bokeh.models.ColumnDataSource(df)

    columns = [
        bokeh.models.TableColumn(field=name, title=name) for name in df.columns
    ]
    table = bokeh.models.DataTable(
        source=source, width=400, columns=columns, sizing_mode="stretch_both"
    )
    return table


def graph_edge_table():
    """Shows the edge attributes of the graph."""
    df = nx.to_pandas_edgelist(ipc_connectivity.graph)
    source = bokeh.models.ColumnDataSource(df)

    columns = [
        bokeh.models.TableColumn(field=name, title=name) for name in df.columns
    ]
    table = bokeh.models.DataTable(
        source=source, width=400, columns=columns, sizing_mode="stretch_both"
    )
    return table


features_splom = features.splom(features_df, features_bokeh, features_columns)
features_table = features.table(features_df, features_bokeh, features_columns)

cluster.create_reducer(mode="PCA")
cluster.fit_reduction(features_df, features_columns)
cluster_splom = cluster.splom(features_df, features_columns)
cluster_table = cluster.table(features_df, features_columns)

tabs = bokeh.models.Tabs(tabs=[
    bokeh.models.TabPanel(child=features_splom, title="Features SPLOM"),
    bokeh.models.TabPanel(child=features_table, title="Features Table"),
    bokeh.models.TabPanel(child=cluster_splom, title="UMAP SPLOM"),
    bokeh.models.TabPanel(child=cluster_table, title="UMAP Table"),
    bokeh.models.TabPanel(child=graph(), title="Graph"),
    bokeh.models.TabPanel(child=graph_vertex_table(), title="Graph Vertex Table"),
    bokeh.models.TabPanel(child=graph_edge_table(), title="Graph Edge Table")
], active=0, sizing_mode="stretch_both", syncable=True)

document = bokeh.plotting.curdoc()
document.add_root(tabs)

# document.add_root(
#     umap_splom()
# )