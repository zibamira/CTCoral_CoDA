"""
:mod:`cora.data_provider.amira`

This module implements a special filesystem based data provider, making
the interaction with Amira smoother and use of the *hxipc* package.
"""

import pathlib
import re
import tempfile

import watchdog
import watchdog.observers
import watchdog.events

from cora.data_provider.filesystem import FilesystemDataProvider


__all__ = [
    "AmiraDataProvider"
]


class AmiraDataProvider(FilesystemDataProvider):
    """A simplified file system data provider that is tuned 
    to the Amira HxCora interface.
    
    The provider watches a single directory and adds csv spreadsheets
    to Cora based on filename conventions.

    *   Filenames matching ``vertex_*.csv`` are treated as vertex data.
    *   Filenames matching ``edge_*.csv`` are treated as edge data.

    The current Cora selection is stored in ``cora_vertex_selection.csv``
    and ``cora_edge_selection.csv``.
    """

    re_vertex_csv = re.compile("vertex_(?P<prefix>.*).csv")
    re_edge_csv = re.compile("edge_(?P<prefix>.*).csv")

    def __init__(self, amira_cora_directory = pathlib.Path):
        super().__init__()

        #: The shared directory between Amira and Cora.
        self.amira_cora_directory = amira_cora_directory
        self.watch_directory(amira_cora_directory)

        # Set the default selection paths.
        self.path_edge_selection = amira_cora_directory / "cora_edge_selection.csv"
        self.path_vertex_selection = amira_cora_directory / "cora_vertex_selection.csv"

        # Perform an initial search.
        for path in self.amira_cora_directory.iterdir():
            self.try_add_vertex(path)
            self.try_add_edge(path)
        return None

    @classmethod
    def zero_conf_amira_cora_directory(self):
        """Look for the latest directory in the system temporary directory,
        e.g. `/tmp` for an `amira_cora_*` directory. The last one created
        will be returned.

        This zero-conf approach is a convention between the Amira package
        *hxcora* and *py_cora*.
        """
        temp_dir = pathlib.Path(tempfile.gettempdir())
        paths = [
            path \
            for path in temp_dir.glob("amira_cora_*")\
            if path.is_dir()
        ]
        if not paths:
            return None

        path = max(paths, key=lambda path: path.stat().st_ctime)
        return path


    def try_add_vertex(self, path: pathlib.Path):
        """Checks if the path points to a vertex spreadsheet and adds it."""
        if not path.is_file():
            return None
        
        m = self.re_vertex_csv.match(path.name)
        if m is not None:
            self.add_vertex_csv(path, prefix=m.group("prefix"))
        return None

    def try_add_edge(self, path: pathlib.Path):
        """Checks if the path points to an edge spreadsheet and adds it."""
        if not path.is_file():
            return None
        
        m = self.re_edge_csv.match(path.name)
        if m is not None:
            self.add_edge_csv(path, prefix=m.group("prefix"))
        return None
    

    def on_created(self, event: watchdog.events.FileSystemEvent):
        """Check if a new vertex or edge spreadsheet has been created
        and load it eventually.
        """
        src_path = pathlib.Path(event.src_path).absolute()

        self.try_add_vertex(src_path)
        self.try_add_edge(src_path)
        return super().on_created(event)
    
    def on_deleted(self, event: watchdog.events.FileSystemEvent):
        """Check if a vertex or edge spreadsheet has been removed."""
        src_path = pathlib.Path(event.src_path).absolute()

        self.remove_vertex_csv(src_path)
        self.remove_edge_csv(src_path)
        return super().on_deleted(event)