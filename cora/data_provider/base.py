"""
:mod:`cora.data_provider.base`

This module implements the :class:`DataProvider` interface which is a simple
abstraction allowing to adapt different data source into Cora, pre-process
and aggregate them. 
"""


import pathlib
from typing import Callable

import blinker
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

        #: A set of colormaps that may be used inside cora.
        self.colormaps = dict()

        #: This signal is emitted when a resource changed. The emitter
        #: may be called from a different thread.
        #:
        #: :seealso: meth:~cora.application.Application.on_data_provider_change`
        self.on_change = blinker.Signal()
        return None

    def reload(self):
        """Reloads the data. 

        Subclasses must call :meth:`notify_change` if the reload was 
        succesful.
        """
        return None

    def write_vertex_selection(self, indices):
        """This method is called by the cora application when the current vertex
        selection changed. 
        
        Subclasses may override this method and store the current selection 
        at some place, e.g. in a JSON or CSV file.
        """
        return None
    
    def write_edge_selection(self, indices):
        """This method is called by the cora application when the current edge
        selection changed.
        
        Subclasses may override this method and store the current selection
        at some place, e.g. in a JSON or CSV file.
        """
        return None

    def write_vertex_colormap(self, colors):
        """This method is called by the cora application when the vertex colormap
        changed.
        
        Subclasses may override this method and store the current selection
        at some place, e.g. in a JSON or CSV file.
        """
        return None

    def write_edge_colormap(self, colors):
        """This method is called by the cora application when the edge colormap
        changed.
        
        Subclasses may override this method and store the current selection
        at some place, e.g. in a JSON or CSV file.
        """
        return None

    def notify_change(self):
        """Notifies Cora that the data changed and needs to be reloaded."""
        self.on_change.send(self)
        return None