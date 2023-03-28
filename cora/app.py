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
import graph


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
features_columns = ["Volume3d", "VoxelFaceArea", "Anisotropy", "Flatness", "Elongation"]
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


# Features
features_splom = features.splom(features_df, features_bokeh, features_columns)
features_table = features.table(features_df, features_bokeh, features_columns)

# Dimensionality reduction
cluster.create_reducer(mode="PCA")
cluster.fit_reduction(features_df, features_columns)
cluster_splom = cluster.splom(features_df, features_columns)
cluster_table = cluster.table(features_df, features_columns)

# Graph
graph_edge_df = graph.to_pandas_edgelist(ipc_connectivity.graph)
graph_vertex_df = graph.to_pandas_vertexlist(ipc_connectivity.graph)

graph_edge_source = bokeh.models.ColumnDataSource(graph_edge_df)
graph_vertex_source = bokeh.models.ColumnDataSource(graph_vertex_df)

graph_plot = graph.plot(
    ipc_connectivity.graph,
    graph_vertex_df, graph_vertex_source, graph_edge_df, graph_edge_source
)
graph_vertex_table = graph.vertex_table(graph_vertex_source, [])
graph_edge_table = graph.edge_table(graph_edge_source, [])

# Document (Tabs)
tabs = bokeh.models.Tabs(tabs=[
    bokeh.models.TabPanel(child=features_splom, title="Features SPLOM"),
    bokeh.models.TabPanel(child=features_table, title="Features Table"),
    bokeh.models.TabPanel(child=cluster_splom, title="UMAP SPLOM"),
    bokeh.models.TabPanel(child=cluster_table, title="UMAP Table"),
    bokeh.models.TabPanel(child=graph_plot, title="Graph"),
    bokeh.models.TabPanel(child=graph_vertex_table, title="Graph Vertex Table"),
    bokeh.models.TabPanel(child=graph_edge_table, title="Graph Edge Table")
], active=4, sizing_mode="stretch_both", syncable=True)

document = bokeh.plotting.curdoc()
document.add_root(tabs)