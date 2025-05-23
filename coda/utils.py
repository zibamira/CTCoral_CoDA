"""
:mod:`utils`

This module contains some utilities and helper functions which did not 
belong some where else specifically.
"""

import enum
import itertools
from typing import Iterator, List, Any, Dict
import re

import bokeh
import bokeh.models

import blinker
import pandas as pd
import numpy as np
from natsort import natsorted
import matplotlib


__all__ = [
    "data_columns",
    "scalar_columns",
    "categorical_columns",
    "integral_columns",
    "label_columns",
    "is_rgb_column",
    "is_rgba_column",
    "is_color_column",
    "color_columns",
    "FactorMap"
]


def data_columns(df):
    """Returns all data columns in the data frame, sorted by their names
    in natural order.
    """
    return list(natsorted(name for name in df.columns if not name.startswith("coda:")))


def scalar_columns(df, allow_nan=True):
    """Returns all columns with scalar values."""
    columns = [name for name in data_columns(df) if pd.api.types.is_numeric_dtype(df[name].dtype)]
    if not allow_nan:
        columns = [name for name in data_columns(df) if not df[name].isnull().any()]
    return columns


def categorical_columns(df):
    """Returns all columns with categorical values."""
    return [name for name in data_columns(df) if pd.api.types.is_string_dtype(df[name].dtype)]


def integral_columns(df):
    """Returns all columns with integral values."""
    return [name for name in data_columns(df) if pd.api.types.is_integer_dtype(df[name].dtype)]


def label_columns(df):
    """Returns all columns with label (categorical) values."""
    return categorical_columns(df) + integral_columns(df)


def is_rgb_column(col):
    """Returns true if the column contains hexcoded RGB color values."""
    if not pd.api.types.is_string_dtype(col.dtype):
        return False

    re_rgb = re.compile("#[0-9a-fA-F]{6}")
    return col.str.fullmatch(re_rgb).all()


def is_rgba_column(col):
    """Returns true if the column contains hexcoded RGB color values."""
    if not pd.api.types.is_string_dtype(col.dtype):
        return False

    re_rgba = re.compile("#[0-9a-fA-F]{8}")
    return col.str.fullmatch(re_rgba).all()


def rgb_to_hex(value):
    """Converts the rgb tuple value ``(red, green, blue)`` to its corresponding
    hex value.
    """
    r, g, b, *_ = value
    r = max(0, min(255, int(256.0*r)))
    g = max(0, min(255, int(256.0*g)))
    b = max(0, min(255, int(256.0*b)))
    return f"#{r:02X}{g:02X}{b:02X}"


def matplotlib_palette(name: str):
    """Returns the palette of the matplotlib colormap with the name *name*.
    
    .. code-block::

        DEFAULT_PALETTE = matplotlib_palette("Set2")
    """
    cmap = matplotlib.colormaps[name]
    palette = cmap.colors
    return [rgb_to_hex(color) for color in palette]


def is_color_column(col):
    """Returns true if the column contains hexcoded RGB or RGBA data."""
    return is_rgb_column(col) or is_rgba_column(col)


def color_columns(df):
    """Returns all columns with hexcoded RGB or RGBA data."""
    return [name for name in data_columns(df) if is_color_column(df[name])]


def matplotlib_palette(name: str) -> List[str]:
    """Returns the palette of a :mod:`matplotlib` colormap, so that it can 
    be used in a :class:`FactorMap`.
    """
    cmap = matplotlib.colormaps[name]
    hex_colors = [matplotlib.colors.to_hex(color) for color in cmap.colors]
    return hex_colors


class FactorMap(object):
    """Categorical data, e.g. labels or groups, can often not be represented
    directly in Bokeh. 
    
    This class wraps a column in a Bokeh column data source and caches the
    unique factors (labels) present in the column.

    The labels are naturally sorted so that it can be easily visualized
    in a legend in a deterministic order.

    Each categorical label is then assigned a numeric id which can be 
    used in Bokeh's standard transform tools, e.g. a `factor_cmap` which 
    only works with numeric data or a glyph map.

    Additionally, if a palette is given, e.g. a color palette or a set of
    markers, then an additional column with the color or glyph for each
    sample is computed as well.

    .. code::

        cds = bokeh.models.ColumnDataSource(df)

        # Create a color map based on the year column in the dataframe.
        fmap = FactorMap(
            "color", df=df, cds=cds, column_name="year", 
            palette=["blue", "green", "yellow", "red"]
        )
        fmap.update_cds()

        # The column ``coda:factor_map:glyph`` contains the color
        # for each row in the data frame.
        p = bokeh.plotting.figure()
        p.scatter(
            x="x", y="y", source=self.cds, fill_color="coda:factor_map:glyph"
        )
    """

    class Mode(enum.Enum):
        """Defines the behaviour of the factor map when 
        there are too many factors in the dataset and too few
        values in the palette.
        """
        CYCLE = enum.auto()
        REPEAT_LAST = enum.auto()


    def __init__(
        self, *, 
        name: str,
        df: pd.DataFrame, 
        cds: bokeh.models.ColumnDataSource, 
        column_name: str,
        palette: List[Any],
        mode: Mode = Mode.REPEAT_LAST
        ):
        """ """
        #: *input* The name of this factor map. The column names of this map
        #: in the column data source are derived from this name.
        self.name = name

        #: *input* The data frame with the original data.
        self.df = df

        #: *input* The Bokeh data source which will contain the render
        #: information. This source is enriched with information about
        #: the factor map.
        self.cds = cds

        #: *input* The name of the column in :attr:`df` which is used
        #: to create the factor map.
        self.column_name = column_name

        #: *input* A set (palette) of glyphs. Each factor is mapped to a 
        #: glyph in this list.
        self.palette: List[Any] = palette

        #: *input* Defines the out-of-bound behaviour for the palette.
        self.mode = mode

        #: The sorted list with all unique labels (factors).
        #:
        #:      factor -> id
        #:
        self.factors: List[str] = []

        #: The mapping from factor to glyph (palette item).
        #:
        #:      factor -> glyph
        #:
        self.glyph_map: List[Any] = []

        #: Mapping from factor to index in :attr:`factors`.
        #:
        #:      factor -> int
        #:
        self.id_map: Dict[str, int] = {}

        #: The additional data column mapping each label (factor) to its
        #: unique factor id.
        self.id_column: List[int] = []

        #: The additional data column mapping each label (factor) to its
        #: glyph.
        self.glyph_column: List[Any] = []

        #: Emitted when the colormap is updated.
        self.on_update = blinker.Signal()
        return None

    def value_to_factor(self, value):
        """Maps the column data value *value* to a factor.

        This function is primarily used for colormapping when a range is applied.
        In most cases, the column value is the factor itself.

        **This method may be overridden.**
        """
        return value

    def update_df(self):
        """Recomputes the internal factor map.
        
        This method will leave the column data source unchanged.
        """
        nrows = len(self.df)

        # Use default values if the data frame has no column with the
        # given name.
        if self.column_name not in self.df:
            self.factors = ["None"]

            glyph = self.palette[0]
            self.glyph_map = {"None": glyph}
            self.glyph_column = [glyph for i in range(nrows)]
            
            self.id_map = {"None": 0}
            self.id_column = np.zeros(nrows)
            
            df = self.df
            df[f"{self.name}:glyph"] = self.glyph_column
            df[f"{self.name}:id"] = self.id_column
            return None

        # Get all unique factors in the discrete label column and 
        # sort them naturally.
        factors = np.unique(self.df[self.column_name])
        factors = list(natsorted(factors))
        self.factors = factors
        
        # Create the glyph mapping.
        if self.mode == FactorMap.Mode.CYCLE:
            palette = itertools.cycle(self.palette)
        else:
            palette = itertools.chain(self.palette, itertools.repeat(self.palette[-1]))

        self.glyph_map = {factor: glyph for factor, glyph in zip(factors, palette)}
        self.glyph_column = [self.glyph_map[factor] for factor in self.df[self.column_name]]

        # Create the id column.
        self.id_map = {factor: i for i, factor in enumerate(self.factors)}
        self.id_column = [self.id_map[factor] for factor in self.df[self.column_name]]

        # Update the dataframe.
        df = self.df
        df[f"{self.name}:glyph"] = self.glyph_column
        df[f"{self.name}:id"] = self.id_column
        return None
    
    def push_df_to_cds(self):
        """Updates the column data source with the current
        internal state of the data.
        """
        data = self.cds.data
        data[f"{self.name}:glyph"] = self.glyph_column
        data[f"{self.name}:id"] = self.id_column

        # Notify observers.
        self.on_update.send()
        return None