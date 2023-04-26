"""
:mod:`cora.data_provider.amira`

This module implements a special filesystem based data provider, making
the interaction with Amira smoother and use of the *hxipc* package.
"""

import pathlib

import networkx as nx
import numpy as np
import pandas as pd

from cora.data_provider.base import DataProvider


# Try to import the Amira linking package.
# :todo: Remove the local import and install the Python pacakge
#:       in the local virtual environment once everything works.
import sys
sys.path.insert(1, "/srv/public/bschmitt/py_ipc")
del sys
try:
    import hxipc as amira
    import hxipc.data

    has_amira = True
except ImportError:
    has_amira = False


__all__ = [
    "AmiraDataProvider"
]


class AmiraDataProvider(DataProvider):
    """A data provider linked with an Amira application.
    
    This provider looks for the following Amira *hxipc* meta files in the
    :attr:`data_dir` directory:

    *   :file:`label_analysis.json`
    *   :file:`label_field.json`
    *   :file:`spatialgraph.json`

    :todo: Implement this data provider.
    """

    def __init__(self, data_dir: pathlib.Path):
        """ """
        super().__init__()

        #: The data directory containing the Amira IPC information
        #: files.
        self.data_dir = data_dir

        self.ipc_label_analysis = amira.data.spreadsheet(
            data_dir / "label_analysis.json", 
            mode="r", 
            on_touched=self.notify_change,
            lazy_read=True
        )
        self.ipc_label_field = amira.data.graph(
            data_dir / "label_field.json", 
            mode="r",
            on_touched=self.notify_change,
            lazy_read=True
        )
        self.ipc_spatialgraph = amira.data.array(
            data_dir / "spatialgraph.json", 
            mode="r",
            on_touched=self.notify_change,
            lazy_read=True
        )        

        # Create an output mask corresponding to the current Bokeh selection.
        self.ipc_cora_selection = amira.data.array(
            data_dir / "cora_selection_mask.npy", 
            mode="w",
            shape=self.ipc_segmentation.shape,
            bounding_box=self.ipc_segmentation.bounding_box
        )
        return None

    def reload(self):
        """Reloads and aggregates the Amira input."""
        # Wait until all resources are available.
        if not self.ipc_label_analysis.exists():
            return None
        if not self.ipc_label_field.exists():
            return None
        if not self.ipc_spatialgraph.exists():
            return None

        # Reload if necessary.
        if self.ipc_label_analysis.is_dirty():
            print("Reloading features.")
            self.ipc_label_analysis.read()

        if self.ipc_label_field.is_dirty():
            print("Reloading segmentation.")
            self.ipc_segmentation.read()

        if self.ipc_spatialgraph.is_dirty():
            print("Reloading graph.")
            self.ipc_spatialgraph.read()

        # Aggregate the features from the features spreadsheet 
        # and the spatial graph.
        df_label_analysis = self.ipc_label_analysis.df
        df_spatialgraph_vertices = self.ipc_spatialgraph.df_vertices
        df_spatialgraph_edges = self.ipc_spatialgraph.df_edges

        self.df = pd.merge(
            left=df_label_analysis.add_prefix("label_analysis:"), 
            left_on="label_analysis:index",
            right=df_spatialgraph_vertices.add_prefix("spatialgraph:"), 
            right_on="spatialgraph:label",
            copy=False, 
            how="left", 
            validate="one_to_one",
        )
        self.df_edges = df_spatialgraph_edges
        return None