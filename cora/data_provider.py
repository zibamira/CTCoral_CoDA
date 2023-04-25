"""
:mod:`cora.data_provider`

This module implements the :class:`DataProvider` interface which is a simple
abstraction allowing to adapt different data source into Cora, pre-process
and aggregate them. 

:todo: Implement a data provider which allows uploading datasheets.
:todo: Implement a data provider just using the spreadsheets passed \
       to it via the command line.
"""


import pathlib
from typing import Callable


import pandas as pd
import numpy as np
import networkx as nx


# Try to import the Amira linking package.
# :todo: Remove the local import and install the Python pacakge
#:       in the local virtual environment once everything works.
import sys
sys.path.insert(1, "/srv/public/bschmitt/py_ipc")
del sys
try:
    import hxipc as amira
    import hxipc.data
except ImportError:
    amira = None


__all__ = [
    "DataProvider",
    "RandomDataProvider"
]


class DataProvider(object):
    """Wraps and aggreagates the raw input data to Cora. Multiple
    spreadsheets are combined into a single data frame.
    
    When changes to the original dataframes are detected, they can be
    propagated to Cora so that they are either reloaded automatic
    or after a user confirmation.
    """

    def __init__(self):
        """ """
        #: The data frame with the vertex data.
        self.df = pd.DataFrame()

        #: The data frame containing the edges information linking
        #: the vertices.
        self.df_edges = pd.DataFrame()

        self._on_change: Callable[[], None] = None
        return None

    def reload(self):
        """Reloads the data. 

        Subclasses must call :meth:`notify_change` if the reload was 
        succesful.
        """
        return None

    def notify_change(self):
        """Notifies Cora that the data changed and needs to be reloaded."""
        if self._on_change:
            self._on_change()
        return None
    
    def on_change(self, f: Callable[[], None]):
        """Registers a callback for when the data was modified
        and a reload is needed.
        """
        self._on_change = f
        return None
    

class RandomDataProvider(DataProvider):
    """Test data provider with randomly generated data."""

    def reload(self):
        """Generates new random data."""
        nsamples = 100

        # location data
        # randomly distributed around a nice, local Berlin bakery
        latitude = 52.5211544 + np.random.normal(0.0, scale=0.004, size=nsamples)
        longitude = 13.3469807 + np.random.normal(0.0, scale=0.008, size=nsamples)

        # vertex data
        df = pd.DataFrame.from_dict({
            "input:col A": np.random.random(nsamples),
            "input:col B": np.random.standard_normal(nsamples),
            "input:col C": np.random.random(nsamples),
            "input:col D": np.random.random(nsamples),
            "input:col E": np.random.random(nsamples),
            "input:col F": np.random.random(nsamples),
            "input:label A": np.random.choice(["A1", "A2"], size=nsamples),
            "input:label B": np.random.choice(["B1", "B2", "B3"], size=nsamples),
            "input:latitude": latitude,
            "input:longitude": longitude
        })

        # graph (and thus edge) data
        G = nx.random_regular_graph(d=2, n=nsamples)
        G = nx.minimum_spanning_tree(G)
        df_edges = nx.to_pandas_edgelist(
            G=G, source="source", target="target"
        )

        self.df = df
        self.df_edges = df_edges
        self.notify_change()
        return None


if amira is not None:

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