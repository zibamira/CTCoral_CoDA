"""
:mod:`cora.data_provider.filesystem`

This module implements a data provider using files stored in the local filesystem.
The files are watched for modifications so that Cora can be synchronized automatic
with changes occuring in the data.
"""

from collections import namedtuple
import pathlib
from typing import Callable, Optional, List, Dict

import networkx as nx
import numpy as np
import pandas as pd

import watchdog
import watchdog.observers

from cora.data_provider.base import DataProvider


__all__ = [
    "FilesystemDataProvider"
]


class FilesystemDataProvider(DataProvider):
    """This data provider merges several spreadsheets and watches their modification.

    Additionally, it also accepts the path to a label field corresponding to the
    vertices and edges.

    The current selection indices are made available in two spreadsheets, one for the
    vertex and one for the edge data. Similarly, the selections are made available as 
    masks for the label fields.
    """

    #: This named tuple collects information about a watched file.
    FileInfo = namedtuple(
        "file_info", ["path", "type", "prefix", "dirty", "data", "observed_watch"]
    )

    def __init__(self):
        super().__init__(self)

        #: Paths to spreadsheets containing vertex data.
        self.files: Dict[pathlib.Path, FileDataProvider.FileInfo] = dict()

        #: Paths to spreadsheets containing edge data.
        self.files: Dict[pathlib.Path, FileDataProvider.FileInfo] = dict()

        #: Path to the vertex label field.
        self.file_label_field: Optional[FileDataProvider.FileInfo] = None

        #: Path to the edge label field.
        self.file_label_field_edges = Optional[FileDataProvider.FileInfo] = None

        #: Output path for the label field mask.
        self.path_label_field_mask: Optional[pathlib.Path] = None

        #: Output path for the edge field mask.
        self.path_label_field_edges_mask: Optional[pathlib.Path] = None

        #: Watchdog watching for file modifications.
        self.observer = watchdog.observers.Observer()
        return None

    def add_vertex_csv(self, path: pathlib.Path, prefix=""):
        """Adds a new file to the watchlist."""        
        path = path.absolute()
        prefix = prefix or path.stem

        observed_watch = self.observer.schedule(
            self.on_file_change, path, recursive=False
        )

        self.files[path] = FileDataProvider.FileInfo(
            path=path, 
            type="vertex", 
            prefix=prefix, 
            dirty=True, 
            data=None,
            observed_watch=observed_watch
        )

        self._reload_vertex(path)
        return None

    def _reload_vertex(self, info: FileInfo):
        """Reloads the vertex data."""
        assert info.type == "vertex"

        if info.path.exists():
            info.data = pd.read_csv(info.path)
            info.dirty = False 
        return None


    def add_edge_csv(self, path: pathlib.Path, prefix=""):
        """Adds a new file to the watchlist."""
        path = path.absolute()
        prefix = prefix or path.stem

        observed_watch = self.observer.schedule(
            self.on_file_change, path, recursive=False
        )

        self.files[path] = FileDataProvider.FileInfo(
            path=path, 
            type="vertex", 
            prefix=prefix, 
            dirty=True, 
            data=None,
            observed_watch=observed_watch
        )

        self._reload_vertex(path)
        return None

    def _reload_edge(self, info: FileInfo):
        """Reloads the edge data."""
        assert info.type == "edge"

        if info.path.exists():
            info.data = pd.read_csv(info.path)
            info.dirty = False
        return None
    

    def set_label_field_path(self, path: pathlib.Path):
        """Adds tha path to the label field. This file is memory mapped."""
        return None

    def _reload(self, path):
        """Reloads the path."""
        info = self.files[path]

        if info.type == "vertex":
            info.data = pd.read_csv(info.path)
            info.dirty = False            
        elif info.type == "edge":
            info.data = pd.read_csv(info.path)
            info.dirty = False
        return None

    def reload(self):
        """Reloads and merges all paths marked as dirty."""
        # Reload all dirty files.
        for path, info in self.files.items():
            if info.dirty:
                self._reload(path)

        # Merge the single dataframes into the global one.
        dfs_vertex = [
            info.data.add_prefix(info.prefix) \
            for info in self.files.values() \
            if info.type == "vertex"
        ]
        self.df = pd.concat(dfs_vertex, axis="columns")

        dfs_edges = [
            info.data.add_prefix(info.prefix)\
            for info in self.files.values()\
            if info.type == "edge"
        ]
        self.df_edges = pd.concat(dfs_edges, axis="columns")

        # Done.
        self.notify_change()
        return None

        


    def add_vertex_data(self, path: pathlib.Path, prefix=None):
        """Reads the spreadsheet and merges it with the vertex data frame."""
        if prefix is None:
            prefix = path.stem
        
        df = pd.read_csv(path)
        
        return None


    def on_directory_changed(self):
        """Called when a new filed was created in the directory.
        
        This callback is used to check if a path is now available, i.e.
        has been created by another process so that we can load it for 
        the first time.
        """

    def on_modified(self, path):
        """Called when a watched path was modified. This will eventually
        trigger a reload in Cora.
        """
        return None

    def reload(self):
        """Reloads all available data. The reload will block if not all
        paths are available.
        """
        return None
