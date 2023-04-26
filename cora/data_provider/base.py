"""
:mod:`cora.data_provider.base`

This module implements the :class:`DataProvider` interface which is a simple
abstraction allowing to adapt different data source into Cora, pre-process
and aggregate them. 
"""


import pathlib
from typing import Callable

import pandas as pd
import numpy as np


__all__ = [
    "DataProvider",
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
        super().__init__()
        
        print("INIT PROVIDER", self)
        #: The data frame with the vertex data.
        self.df = pd.DataFrame()

        #: The data frame containing the edges information linking
        #: the vertices.
        self.df_edges = pd.DataFrame()

        #: A label field (mask) with indices corresponding to the rows
        #: in the vertex dataframe.
        self.label_field = np.empty(0)

        #: A label field (mask) with indices corresponding to the rows
        #: in the edge dataframe.
        self.label_field_edges = np.empty(0)

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