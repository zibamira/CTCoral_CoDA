"""
:mod:`cora.data_provider.filesystem`

This module implements a data provider using files stored in the local filesystem.
The files are watched for modifications so that Cora can be synchronized automatic
with changes occuring in the data.
"""

from collections import namedtuple
import pathlib
from typing import Callable, Optional, List, Dict, Set

import networkx as nx
import numpy as np
import pandas as pd

import watchdog
import watchdog.observers
import watchdog.events

from cora.data_provider.base import DataProvider


__all__ = [
    "FileHandle",
    "FilesystemDataProvider"
]


#: The file handle stores information about the path of a file,
#: a prefix used when merging with the global data frames, 
#: a dirty flag indicating that the in memory data is outdated, 
#: the actual data in the file and a watch handle used 
#: by the watchdog library.
FileHandle = namedtuple(
    "FileHandle", 
    ["path", "prefix", "dirty", "data", "observed_watch"]
)


DirectoryHandle = namedtuple(
    "DirectoryHandle",
    ["path", "file_handles", "observed_watch"]
)


class FilesystemDataProvider(DataProvider, watchdog.events.FileSystemEventHandler):
    """This data provider merges several spreadsheets and watches their modification.

    Additionally, it also accepts the path to a label field corresponding to the
    vertices and edges.

    The current selection indices are made available in two spreadsheets, one for the
    vertex and one for the edge data. Similarly, the selections are made available as 
    masks for the label fields.

    The provider will block reloading if not *all* resources are available. So as long
    as a single input has not been created yet or is missing, a reload will not happen.
    Similarly, the reload button is disabled when a resource was removed from the filesystem
    but not from the provider list.
    """

    def __init__(self):
        print("INITI DATAPROVIDER")
        DataProvider.__init__(self)
        watchdog.events.FileSystemEventHandler.__init__(self)

        #: We also watch the parent directories so that we can check wether
        #: a file has been created. 
        self.directory_handles: Dict[pathlib.Path, DirectoryHandle] = dict()

        #: The watched files.
        self.file_handles: Dict[pathlib.Path, FileHandle] = dict()


        #: All file handles corresponding to vertex data.
        self.vertex_handles: Set[FileHandle] = set()

        #: All file handles corresponding to edge data.
        self.edge_handles: Set[FileHandle] = set()

        #: The file handle corresponding to the label field.
        self.vertex_field_handle: Optional[FileHandle] = None

        #: The file handle corresponding to the edge label field.
        self.edge_field_handle: Optional[FileHandle] = None
        

        #: Output path for the label field mask.
        self.path_label_field_mask: Optional[pathlib.Path] = None

        #: Output path for the edge field mask.
        self.path_label_field_edges_mask: Optional[pathlib.Path] = None


        #: Watchdog watching for file modifications.
        self.observer = watchdog.observers.Observer()
        return None

    def add_vertex_csv(self, path: pathlib.Path, prefix=""):
        """Adds a new file to the watchlist."""        
        assert path not in self.file_handles
        assert path not in self.directory_handles

        path = path.absolute()
        prefix = prefix or path.stem

        info = FileHandle(
            path=path,
            prefix=prefix, 
            dirty=True, 
            data=None,
            observed_watch=None
        )

        self.file_handles[path] = info
        self.vertex_handles.add(info)

        self.watch(info)
        return None

    def add_edge_csv(self, path: pathlib.Path, prefix=""):
        """Adds a new file to the watchlist."""
        assert path not in self.file_handles
        assert path not in self.directory_handles

        path = path.absolute()
        prefix = prefix or path.stem

        info = FileHandle(
            path=path, 
            prefix=prefix, 
            dirty=True, 
            data=None,
            observed_watch=None
        )

        self.file_handles[path] = info
        self.edge_handles.add(info)
        
        self.watch(info)
        return None

    def set_vertex_field(self, path: pathlib.Path):
        """Sets the path to the vertex field to the given file."""
        assert path not in self.file_handles
        assert path not in self.directory_handles

        path = path.absolute()
        prefix = "vertex_field"

        info = FileHandle(
            path=path,
            prefix=prefix,
            dirty=True,
            data=None,
            observed_watch=None
        )

        self.file_handles[path] = info
        self.vertex_field_handle = info

        self.watch(info)
        return None

    def set_edge_field(self, path: pathlib.Path):
        """Sets the path to the edge field to the given file."""
        assert path not in self.file_handles
        assert path not in self.directory_handles

        path = path.absolute()
        prefix = "edge_field"

        info = FileHandle(
            path=path,
            prefix=prefix,
            dirty=True,
            data=None,
            observed_watch=None
        )

        self.file_handles[path] = info
        self.edge_field_handle = info

        self.watch(info)
        return None


    # -- Watchdog--

    def watch_directory(self, path: pathlib.Path):
        """Starts wathing the directory."""
        if not path.exists():
            print(f"WARNING: Cannot watch modifications in {path}.")

        # Nothing to do. We are already watching.
        if path in self.directory_handles:
            return None

        # Start watching.
        observed_watch = self.observer.schedule(self, path, recursive=False)
        info = DirectoryHandle(
            path=path, 
            file_handles=set(), 
            observed_watch=observed_watch
        )
        
        self.directory_handles[path] = info
        return None

    def watch(self, info: FileHandle):
        """Starts watching the file and it's parent directory."""
        # Nothing to do, we are already watching.
        if info.observed_watch is not None:
            return None

        # Watch the parent directory.
        self.watch_directory(info.path.parent())

        # Watch the file itself if it exists.
        if info.path.exists():
            info.observed_watch = self.observer.schedule(
                self, info.path, recursive=False
            )
        return None

    def unwatch(self, info: FileHandle):
        """Stops watching the file."""
        if info.observed_watch is not None:
            self.observer.unschedule(info.observed_watch)
            info.observed_watch = None
        return None
        
    def on_closed(self, event: watchdog.events.FileSystemEvent):
        """Watchdog callback, called when a file or directory was closed."""
        # We ignore this event for now.
        return None

    def on_created(self, event: watchdog.events.FileSystemEvent):
        """Watchdog callback, called when a file or directory was created.
        
        If the file belongs to a registered resource, we start watching it
        and mark it as *loadable*.
        """
        info = self.file_handles.get(event.src_path)
        if info is not None:
            self.watch(info)
            self.notify_change()
        return None

    def on_deleted(self, event: watchdog.events.FileSystemEvent):
        """Watchdog callback, called when a file or directory was deleted.

        We mark the resource as *dirty* and *non-existent*. A reload will
        be blocked until the resource becomes available again.
        """
        info = self.file_handles.get(event.src_path)
        if info is not None:
            self.unwatch(info)
            self.notify_change()
        return None

    def on_modified(self, event: watchdog.events.FileSystemEvent):
        """Watchdog callback, called when a file or directory was modified.
        
        A resource was modified, so we mark it as dirty, notify the Cora
        application and eventually trigger a reload.
        """
        info = self.file_handles.get(event.src_path)
        if info is not None:
            info.dirty = True
            self.notify_change()
        return None

    def on_moved(self, event):
        """Watchdog callback, called when a file or directory was moved
        or renamed.
        
        We don't have to do anything since the original paths are still
        used by watchdog.
        """
        return None

    # -- DataProvider --

    def is_ready(self):
        """True if all resources are ready and can be loaded."""
        return all(info.path.exists() for info in self.file_handles)

    def is_dirty(self):
        """True if at least one resource has been modified and 
        the data must be reloaded.
        """
        return any(info.dirty for info in self.file_handles)

    def reload_vertex(self):
        """Reload all vertex data."""
        for info in self.vertex_handles:
            if not info.path.exists():
                info.data = None
                info.dirty = True
            elif info.dirty:
                info.data = pd.read_csv(info.path)
                info.dirty = False

        # Merge all individiual data frames into one.
        dfs = [
            info.data.add_prefix(info.prefix) \
            for info in self.vertex_handles \
            if info.data is not None
            
        ]
        if dfs:
            self.df = pd.concat(dfs, axis="columns")
        return None

    def reload_edge(self):
        """Reload all edge data."""
        for info in self.edge_handles:
            if not info.path.exists():
                info.data = None
                info.dirty = True
            elif info.dirty:
                info.data = pd.read_csv(info.path)
                info.dirty = False

        # Merge all individiual data frames into one.
        dfs = [
            info.data.add_prefix(info.prefix) \
            for info in self.edge_handles \
            if info.data is not None
            
        ]
        if dfs:
            self.df_edges = pd.concat(dfs, axis="columns")
        return None

    def reload_vertex_field(self):
        """Reload the vertex field."""
        info = self.vertex_field_handle
        if info is None:
            return None

        if not info.path.exists():
            info.data = None
            info.dirty = True
        elif info.dirty:
            info.data = np.load(info.path, mmap_mode="r")
        return None

    def reload_edge_field(self):
        """Reload the edge field."""
        info = self.edge_field_handle
        if info is None:
            return None

        if not info.path.exists():
            info.data = None
            info.dirty = True
        elif info.dirty:
            info.data = np.load(info.path, mmap_mode="r")
        return None

    def reload(self):
        """Reloads and merges all paths marked as dirty."""
        self.reload_vertex()
        self.reload_edge()
        self.reload_vertex_field()
        self.reload_edge_field()

        # Done.
        self.notify_change()
        return None