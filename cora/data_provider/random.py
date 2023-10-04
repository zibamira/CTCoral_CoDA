"""
:mod:`cora.data_provider.random`

This module implements a data provider generating random data,
mainly for testing and development purposes.
"""

from pprint import pprint

import networkx as nx
import numpy as np
import pandas as pd

from cora.data_provider.base import DataProvider


__all__ = [
    "RandomDataProvider"
]


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

    def write_vertex_selection(self, indices):
        print("-- begin: vertex selection --")
        pprint(indices)
        print("-- end: vertex selection --")
        return None

    def write_edge_selection(self, indices):
        print("-- begin: edge selection --")
        pprint(indices)
        print("-- end: edge selection --")
        return None

    def write_vertex_colormap(self, colors):
        print("-- begin: vertex colormap --")
        pprint(colors)
        print("-- end: vertex colormap --")
        return None

    def write_edge_colormap(self, colors):
        print("-- begin: edge colormap --")
        pprint(colors)
        print("-- end: edge colormap --")
        return None
        