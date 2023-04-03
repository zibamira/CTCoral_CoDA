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


# Graph positions:
#
#   Find out how to use a ColumnDataSource for the edge
#   positions and store the positions in a column
#   `_cora:vertex_position`. The position can be updated
#   interactively from the server side.
#
# SPLOM visibility:
#
#   Puhhhhh. Create all renderers beforehand and change
#   the visibility?
#   How can we set the position? (could be ignored
#   if difficult. But then the position is fixed by
#   the creation order.)
#       
#   Check if "x" and "y" can be changed interactively.
#   Check if "range" (name) can be changed interactively.
#   If yes to all, then everything is good!


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
    

class AmiraData(object):
    """Loads and synchronizes the data with Amira.
    
    We are looking for the following input files in the data folder. The input 
    files are only read and never written to.

    *   :file:`{data_dir}/instance_segmentation.json` 
    
        This 3D label field is read as Numpy array and contains 
        the instance segmentation of the volume of interest.
    *   :file:`{data_dir}/instances_features.json`

        This spreadsheet contains all features extracted that have
        been extracted in Amira, e.g. with the label analysis tool.
    
    *   :file:`{data_dir}/instance_connectivity.json`

        This spatialgraph describes the connectivity (edges) of the
        instances (vertices).

    Cora provides the current user selection back to Amira via the following 
    output files. These are created if they don't exist, but are never read.

    *   :file:`{data_dir}/cora_selection_mask.json`

        A 3D label field, 0 indicating the voxel is not selected, 
        1 indicating that the voxel belongs to the current selection.
    """

    def __init__(self, data_dir: pathlib.Path) -> None:
        logging.info("Loading shared Amira resources.")

        # Load the shared input resources.
        self.ipc_features = amira.data.spreadsheet(
            data_dir / "instance_features.json", 
            mode="r", 
            on_touched=self.on_ipc_features_touched,
            lazy_read=True
        )
        
        self.ipc_graph = amira.data.graph(
            data_dir / "instance_connectivity.json", 
            mode="r",
            on_touched=self.on_ipc_graph_touched,
            lazy_read=True
        )
        self.ipc_segmentation = amira.data.array(
            data_dir / "instance_segmentation.json", 
            mode="r",
            on_touched=self.on_ipc_segmentation_touched,
            lazy_read=True
        )        

        # Create an output mask corresponding to the current Bokeh selection.
        self.ipc_cora_selection = amira.data.array(
            data_dir / "cora_selection_mask.npy", 
            mode="w",
            shape=self.ipc_segmentation.shape,
            bounding_box=self.ipc_segmentation.bounding_box
        )

        #: The actual dataframe containing all features. The ones from the label
        #: analyses and graph vertices.
        self.df_features: pd.DataFrame = None

        #: The dataframe containing all edge features, i.e. the edge attributes
        #: of the spatial graph :attr:`ipc_connectivity`.
        self.df_edges: pd.DataFrame = None

        #: Maps the original attribute/column names to the ones in the aggregated
        #: dataframe.
        self.features_column_display_names: Dict[str, str] = dict()

        #: Mapping from the original edge attribute names to the ones in the
        #: aggregated dataframe.
        self.edges_column_display_names: Dict[str, str] = dict()
        return None
    
    def on_ipc_features_touched(self):
        """Callback. Called when Amira changed the feature spreadsheet."""
        logging.debug("Reloading Amira ipc_features.")
        self.reload()
        return None
    
    def on_ipc_graph_touched(self):
        """Callback. Called when Amira changed the graph spatialgraph."""
        logging.debug("Reloading Amira ipc_graph.")
        self.reload()
        return None
    
    def on_ipc_segmentation_touched(self):
        """Callback. Called when Amira changed the segmentation."""
        logging.debug("Reloading Amira segmentation.")
        self.reload()
        return None
    
    def reload(self):
        """Reloads, cleans and aggregates the Amira input data."""
        # Wait until all resources are available.
        if not self.ipc_features.exists():
            return None
        if not self.ipc_segmentation.exists():
            return None
        if not self.ipc_graph.exists():
            return None

        # Reload if necessary.
        if self.ipc_features.is_dirty():
            logging.info("Reloading features.")
            self.ipc_features.read()

        if self.ipc_segmentation.is_dirty():
            logging.info("Reloading segmentation.")
            self.ipc_segmentation.read()

        if self.ipc_graph.is_dirty():
            logging.info("Reloading graph.")
            self.ipc_gra.read()

        # Aggregate the features from the features spreadsheet 
        # and the spatial graph.
        df_features = self.ipc_features.df
        df_vertices = self.ipc_graph.df_vertices
        df_edges = self.ipc_graph.df_edges

        self.df_features = pd.merge(
            left=df_features.add_prefix("feature:"), 
            left_on="feature:index",
            right=df_vertices.add_prefix("vertex:"), 
            right_on="vertex:label",
            copy=False, 
            how="left", 
            validate="one_to_one",
        )
        self.df_edges = df_edges
        return None
    

class Application(object):
    """The application instance contains all resources (data frames, column 
    data sources, plots, ui widgets) present in the Bokeh application.

    It holds the central ground of truth for all visualization and takes
    care of synchronizing the selection across the Bokeh models and Amira.
    """

    def __init__(self):
        """
        """
        # Connection to Amira.
        self.amira: AmiraData = None

        # Data frames
        self.df_features: pd.DataFrame = None
        self.df_edges: pd.DataFrame = None

        # Column data sources 
        self.cds_features: bokeh.models.ColumnDataSource = None
        self.cds_edges: bokeh.models.ColumnDataSource = None

        # Mapping from internal column names in :attr:`df_features`
        # or :attr:`cds_features` to the displayed names in the UI.
        self.features_column_display_names = dict()

        # Mapping from internal column names in :attr:`df_edges`
        # or :attr:`cds_edges` to the displayed names in the UI.
        self.edges_column_display_names = dict()

        # UI
        self.ui_feature_visibility = bokeh.models.MultiChoice(
            title="SPLOM Features",
            options=["Volume3d", "Area3d"],
        )
        self.ui_feature_visibility.on_change(
            "value", 
            self.on_ui_feature_visibility_changed
        )

        self.ui_colormap_column_name = bokeh.models.Select(
            title="Colormap",
            options=["Volume3d", "Area3d"],
        )
        self.ui_colormap_column_name.on_change(
            "value", 
            self.on_ui_colormap_column_name_changed
        )

        self.ui_glyphmap_column_name = bokeh.models.Select(
            title="Glyphmap",
            options=["Volume3d", "Area3d"]
        )
        self.ui_glyphmap_column_name.on_change(
            "value", 
            self.on_ui_glyphmap_column_name_changed
        )

        self.ui_cluster_algorithm = bokeh.models.Select(
            title="Algorithm",
            options=["UMAP", "PCA"]
        )
        self.ui_cluster_algorithm.on_change(
            "value", 
            self.on_ui_cluster_algorithm_changed
        )

        self.ui_cluster_features = bokeh.models.MultiChoice(
            title="Features",
            options=["Volume3d", "Area3d"]
        )
        self.ui_cluster_features.on_change(
            "value", 
            self.on_ui_cluster_features_changed
        )

        self.ui_cluster_do_compute = bokeh.models.Button(
            label="Apply changes", 
            icon=bokeh.models.TablerIcon("check")
        )
        self.ui_cluster_do_compute.on_click(
            self.on_ui_cluster_do_compute_clicked
        )

        self.ui_graph_layout_algorithm = bokeh.models.Select(
            title="Layout",
            options=["dot", "twopi", "circo", "spring"]
        )
        self.ui_graph_layout_algorithm.on_change(
            "value", 
            self.on_ui_graph_layout_algorithm_changed
        )

        self.ui_graph_layout_do_compute = bokeh.models.Button(
            label="Apply changes", 
            icon=bokeh.models.TablerIcon("check")
        )
        self.ui_graph_layout_do_compute.on_click(
            self.on_ui_graph_layout_do_compute_clicked
        )

        # Colormap
        self.colormap = None
        self.glyphmap = None

        # Plots
        self.plot_feature_splom = None
        self.plot_feature_table = None

        self.plot_umap_splom = None
        self.plot_umap_table = None

        self.plot_graph = None
        self.plot_edges_table = None

        self.document = None
        return None

    # Initialization

    def init_amira_data(self, data_dir: pathlib.Path):
        """Loads the Amira resources and waits for changes."""
        self.amira = AmiraData(data_dir)
        return None     

    def init_ui(self):
        """Initialises and layouts the UI widgets."""
        layout = bokeh.layouts.layout([   
            [bokeh.models.Div(text="<strong>Features</strong>")],
            [self.ui_feature_visibility],
            [self.ui_colormap_column_name],
            [self.ui_glyphmap_column_name],
            [bokeh.models.Div(text="<strong>Dimensionality Reduction</strong>")],
            [self.ui_cluster_algorithm],
            [self.ui_cluster_features],
            [self.ui_cluster_do_compute],
            [bokeh.models.Div(text="<strong>Graph View</strong>")],
            [self.ui_graph_layout_algorithm],
            [self.ui_graph_layout_do_compute]
        ])
        self.document = layout
        return None

    def init_colormap(self):
        """Initialises the colormap."""
        return None

    def init_glyphmap(self):
        """Initialises the glyphmap."""
        return None

    def init_plot_feature_splom(self):
        """Creates the SPLOM plot for the features."""
        return None
    
    def init_plot_feature_table(self):
        """Creates the table view for the features."""
        return None
    
    def init_plot_umap_splom(self):
        """Creates the UMAP SPLOM plot."""
        return None
    
    def init_plot_umap_table(self):
        """Creates the UMAP table view."""
        return None
    
    def init_plot_graph(self):
        """Creates the graph plot."""
        return None
    
    def init_plot_edges_table(self):
        """Creates the table view for the edge attributes."""
        return None
    
    def init_layout(self):
        """Arranges all plots in a Bokeh layout."""
        tabs = bokeh.models.Tabs(tabs=[
            bokeh.models.TabPanel(child=self.plot_feature_splom, title="Features SPLOM"),
            bokeh.models.TabPanel(child=self.plot_feature_table, title="Features Table"),
            bokeh.models.TabPanel(child=self.plot_umap_splom, title="UMAP SPLOM"),
            bokeh.models.TabPanel(child=self.plot_umap_table, title="UMAP Table"),
            bokeh.models.TabPanel(child=self.plot_graph, title="Graph"),
            bokeh.models.TabPanel(child=self.plot_edges_table, title="Edge Attributes Table"),
        ], active=4, sizing_mode="stretch_both", syncable=True)

        self.document = tabs
        return None

    # Bokeh client -> Python


    def on_selection_changed(self, indices):
        """The selection in the Bokeh client changed."""
        return None

    def on_ui_feature_visibility_changed(self, attr, old, new):
        print(attr, old, new)
        return None

    def on_ui_colormap_column_name_changed(self, attr, old, new):
        print(attr, old, new)
        return None

    def on_ui_glyphmap_column_name_changed(self, attr, old, new):
        print(attr, old, new)
        return None

    def on_ui_cluster_algorithm_changed(self, attr, old, new):
        print(attr, old, new)
        return None

    def on_ui_cluster_features_changed(self, attr, old, new):
        print(attr, old, new)
        return None

    def on_ui_cluster_do_compute_clicked(self):
        print("clicked cluster")
        return None

    def on_ui_graph_layout_algorithm_changed(self, attr, old, new):
        print(attr, old, new)
        return None

    def on_ui_graph_layout_do_compute_clicked(self):
        print("clicked layout")
        return None


    # Bokeh client

    
    def update_colormap(self):
        """Recomputes the colormap and sends the changes to the client."""
        return None

    def update_glyphmap(self):
        """Recomputes the glyph mapping and sends the changes to the client."""
        return None

    
    def update_cluster_thread(self):
        """Runs the dimensionality reduction and cluster pipeline in the 
        background.
        """
        return None
        
    
    def hide_feature(self, name):
        """Hides the feature with the internal name `name` from all plots
        and the table views.
        """
        return None

    def show_feature(self, name):
        """Shows the feature with the internal name `name` from all plots
        and the table views.
        """
        return None

    
    def select_bokeh(self, indices):
        """Selects the samples in the 'indices' list in the Bokeh client."""
        return None


    # Amira Interoparibility


    def update_amira_mask(self, indices):
        """Updates the label field in Amira which indicates the current
        Bokeh selection.
        """
        return None

    def update_amira_graph_selection(self, vids, eids):
        """Updates the spatial graph selection in Amira to contain the
        given vertex ids 'vids' and edge ids 'eids'.
        """
        return None

    def seek_amira_sample(self, index):
        """Jumps to the location of the instance corresponding to the 'index'
        in the attached Amira viewer. The camera is centered at the instance's
        center of mass and the bounding box fits into the view.
        """
        return None

    def seek_amira_edge(self, index):
        """Seeks the edge in Amira."""
        return None


# Logging
init_logging()

# Path configuration
this_dir = pathlib.Path(__file__).parent
instance_dir = this_dir.parent / "instance"
data_dir = instance_dir / "data"

# Restore the work data.
logging.info("Restoring original data ...")
shutil.copytree(instance_dir / "data_copy", instance_dir / "data", dirs_exist_ok=True)

# Create the CORA application.
app = Application()
app.init_amira(data_dir)
app.init_ui()
app.init_colormap("vertex:shortest_distance")
app.init_glyphmap("vertex:shortest_distance")
app.init_plot_feature_splom()
app.init_plot_feature_table()
app.init_plot_umap_splom()
app.init_plot_umap_table()
app.init_plot_graph()
app.init_plot_edges_table()
app.init_layout()

# Start the Bokeh server.
bokeh.plotting.curdoc().add_root(app.document)