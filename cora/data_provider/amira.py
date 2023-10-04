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


#: The Amira colormap "Labels256" as it is.
LABELS256 = [
    '#000000', '#a300cc', '#00ff00', '#ffff00',
    '#ff0000', '#00ffff', '#008080', '#808000', 
    '#0000ff', '#d96666', '#59e666', '#510066',
    '#5966e6', '#008000', '#ffff80', '#80ff00', 
    '#ff8000', '#800000', '#6c7373', '#ff00ff',
    '#ff80ff', '#ff0080', '#c0c040', '#36b9b9', 
    '#0080ff', '#00ff80', '#284033', '#00c040',
    '#ff40c0', '#c00040', '#c04000', '#40c000', 
    '#0040c0', '#ffa0a0', '#ac73b3', '#80ffff',
    '#5100e6', '#000080', '#5533a6', '#6cb3f3', 
    '#6cf3b3', '#763939', '#b659f9', '#9b2c7c',
    '#a0e080', '#569939', '#c08020', '#ec3333', 
    '#2c73b3', '#2cb373', '#2cf333', '#7ca3b3',
    '#ffd050', '#ffd0d0', '#144079', '#90f040', 
    '#36f9d9', '#2800b3', '#842cf0', '#b69979',
    '#c8f820', '#2c33f3', '#b699f9', '#008040', 
    '#000040', '#400020', '#c0ffff', '#00c0ff',
    '#00e0c0', '#ff00c0', '#ff40ff', '#c00000', 
    '#408000', '#a0c000', '#ffc000', '#00c000',
    '#004000', '#cd169e', '#7a0099', '#604000', 
    '#d9ce8e', '#d120e6', '#80b060', '#ff9050',
    '#00a0c0', '#36f999', '#3699f9', '#356c59', 
    '#ff4080', '#e0ffc0', '#907040', '#a839c0',
    '#800040', '#696bac', '#db9ccc', '#dbccfc', 
    '#b04040', '#68d820', '#c8f860', '#ff0040',
    '#40ff00', '#ff4000', '#5f396c', '#a4fcb0', 
    '#20a020', '#e060a0', '#a6637f', '#8880f0',
    '#60c090', '#9bccfc', '#d12066', '#905010', 
    '#90a028', '#4b8f90', '#a8b8a0', '#36c9e9',
    '#ff70d0', '#ffff40', '#ff6040', '#2a1953', 
    '#10d090', '#1ee161', '#3cc343', '#361989',
    '#982020', '#80d0d0', '#1b5cdc', '#d45cd0', 
    '#00ff40', '#0040ff', '#656c29', '#ecaf6f',
    '#e06010', '#d4ac18', '#304000', '#cc9050', 
    '#a80073', '#445c90', '#8020c0', '#8050d0',
    '#8000ff', '#549cd0', '#70b008', '#d090a0',
    '#5be4f4', '#8346a0', '#356c29', '#5639d9',
    '#ffa828', '#ffa8e8', '#ffe8a8', '#8c908c', 
    '#d4fc90', '#142019', '#855060', '#0020a0',
    '#0010d0', '#005050', '#00a868', '#0068a8', 
    '#2b2cbc', '#00e020', '#ffe020', '#ff8080',
    '#e02000', '#ff2060', '#20e000', '#80ff80', 
    '#60ff40', '#e00020', '#ff20a0', '#006020',
    '#ff20e0', '#d100c6', '#002060', '#a1a3d0', 
    '#c000ff', '#c04090', '#1b9c9c', '#524e48',
    '#7d006c', '#5400b9', '#a600a0', '#9df2da', 
    '#509464', '#d46039', '#bfc86c', '#2800f3',
    '#d676f1', '#a39c50', '#209454', '#d331bf', 
    '#602020', '#9f194c', '#d6d7b7', '#90ca2a',
    '#b46b53', '#66c848', '#5bccbc', '#6020ff', 
    '#3070ff', '#b030ff', '#55204c', '#2a807c',
    '#8878c8', '#af77dc', '#1888e0', '#ff78a8', 
    '#ffd878', '#90d8a8', '#c0e000', '#a89808',
    '#e0a0ff', '#5f8cf4', '#7050ff', '#ea862c', 
    '#b84068', '#4156c6', '#957d65', '#758b4f',
    '#cbebdb', '#c82828', '#7bd474', '#1be4f4', 
    '#40ffff', '#0dc2da', '#186000', '#38d884',
    '#224ea8', '#76f9d9', '#e0dc3c', '#a4fc10', 
    '#a0d050', '#db4cfc', '#5bfc8c', '#91a6f6',
    '#7f295c', '#29debc', '#530090', '#6d1c83', 
    '#474c1c', '#2f445e', '#7a00d9', '#99ba7c',
    '#8c6d9e', '#3bfc6c', '#c87484', '#f44356', 
    '#2ed121', '#55ba6a', '#d3b3ab', '#5c8e14',
    '#ae670a', '#e0ad43', '#d40079', '#b5de9e'
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
    re_colormap_csv = re.compile("colormap_(?P<prefix>.*).csv")

    def __init__(self, amira_cora_directory = pathlib.Path):
        super().__init__()

        #: The shared directory between Amira and Cora.
        self.amira_cora_directory = amira_cora_directory
        self.watch_directory(amira_cora_directory)

        # Set the default selection paths.
        self.path_edge_selection = amira_cora_directory / "cora_edge_selection.csv"
        self.path_vertex_selection = amira_cora_directory / "cora_vertex_selection.csv"

        self.path_edge_colormap = amira_cora_directory / "cora_edge_colormap.csv"
        self.path_vertex_colormap = amira_cora_directory / "cora_vertex_colormap.csv"

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

    def try_add_colormap(self, path: pathlib.Path):
        """Checks if the path points to a colormap spreadsheet and adds it."""
        if not path.is_file():
            return None

        m = self.re_colormap_csv.match(path.name)
        if m is not None:
            self.add_colormap_csv(path, prefix=m.group("prefix"))
        return None       

    def on_created(self, event: watchdog.events.FileSystemEvent):
        """Check if a new vertex or edge spreadsheet has been created
        and load it eventually.
        """
        src_path = pathlib.Path(event.src_path).absolute()

        if src_path.is_file() and not event.is_directory:
            self.try_add_vertex(src_path)
            self.try_add_edge(src_path)
            self.try_add_colormap(src_path)
        return super().on_created(event)
    
    def on_deleted(self, event: watchdog.events.FileSystemEvent):
        """Check if a vertex or edge spreadsheet has been removed."""
        src_path = pathlib.Path(event.src_path).absolute()

        if src_path.is_file() and not event.is_directory:
            self.remove_vertex_csv(src_path)
            self.remove_edge_csv(src_path)
            self.remove_colormap_csv(src_path)
        return super().on_deleted(event)