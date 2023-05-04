"""
:mod:`cora.view.pca`

This module implements a helper for computing the PCA dimensionality reduction
and inspecting it visually.
"""

from typing import List, Literal

import bokeh
import bokeh.models
import bokeh.plotting

import sklearn
import sklearn.decomposition

import pandas as pd
import numpy as np

import cora.utils
from cora.application import Application
from cora.view.base import ViewBase


__all__ = [
    "PCAView"
]


class PCAView(ViewBase):
    """This view allows the user to interactively perform a standard 
    principal component analysis.

    The components are stored in the data column prefixed by

    *   `pca:component:*`.

    The PCAView also visualizes the explained variance in a horizontal,
    stacked bar chart.
    """

    def __init__(self, app: Application):
        super().__init__(app)
        #: UI for selecting the columns that should be used in the PCA
        #: reduction.
        self.ui_multichoice_columns = bokeh.models.MultiChoice(
            title="Columns",
            sizing_mode="stretch_width"
        )
        self.ui_multichoice_columns.on_change(
            "value", self.on_ui_multichoice_columns_change
        )

        #: Data source showing the explained variance.
        self.cds_variance = bokeh.models.ColumnDataSource()
        self.init_cds_variance()

        self.figure_variance: bokeh.models.Model = None
        self.create_figure_variance()

        # Panel layout.
        self.layout_panel.children = [
            self.ui_multichoice_columns,
            self.figure_variance
        ]
        return None


    def reload_df(self):
        """Recompute the PCA when the DF changes."""
        # Update the available columns in the UI and keep the current
        # subset of the columns if possible.
        columns = cora.utils.scalar_columns(self.app.df, allow_nan=False)

        selection = list(self.ui_multichoice_columns.value)
        selection = [column for column in selection if column in columns]

        self.ui_multichoice_columns.options = columns
        self.ui_multichoice_columns.value = selection

        # Recompute the PCA.
        self.update_pca()
        return None
    
    def reload_cds(self):
        """Recomputes the column data source."""
        return None
    

    def update_pca(self):
        """Computes the PCA for the selected columns."""
        columns = self.ui_multichoice_columns.value
        values = self.app.df[columns]

        # Break if no column is selected or at least
        # one column contains a nan value.
        if not columns:
            return None
        if pd.isnull(values).any().any():
            return None

        # Compute the PCA and store the components in the global dataframe.
        reducer = sklearn.decomposition.PCA()
        components = reducer.fit_transform(values)

        for i in range(len(columns)):
            self.app.df[f"pca:feature:{i}"] = components[:, i]

        # Update the plot showing the explained variance.
        self.update_cds_variance(reducer.explained_variance_ratio_)

        # Schedule an update of the Bokeh column data source.
        self.app.push_df_to_cds(vertex=True)
        return None
    
    def update_cds_variance(self, variance: np.array):
        """Updates the data source showing the explained variance."""
        ncolumns = variance.size

        right = np.cumsum(variance)
        left = np.concatenate(([0.0], right[:-1]))
        palette = bokeh.palettes.plasma(ncolumns)

        # Update the column data source.
        data = {
            "left": left,
            "right": right,
            "bottom": np.full_like(left, 0.0),
            "top": np.full_like(left, 1.0),
            "component": [f"component {i}" for i in range(ncolumns)],
            "variance": variance,
            "fill_color": palette
        }
        self.cds_variance.data = data

        print(variance)
        return None
    

    def init_cds_variance(self):
        """Initialises the column data source for the explained variance."""
        data = {
            "left": [],
            "right": [],
            "bottom": [],
            "top": [],
            "component": [],
            "variance": [],
            "fill_color": []
        }
        self.cds_variance.data = data
        return None

    def create_figure_variance(self):
        """Creates the figure showing the explained variance :attr:`figure_variance`.
        """
        p = bokeh.plotting.figure(
            height=80,
            sizing_mode="stretch_width",
            title="Explained Variance",
            tooltips=[
                ("component", "@component"),
                ("variance", "@variance{%0.2f}"),
                ("total variance", "@right{%0.2f}")
            ],
            x_range=(0.0, 1.0),
            y_range=(0.0, 1.0),
            toolbar_location=None
        )        
        p.xaxis.visible = True
        p.xgrid.visible = False

        p.yaxis.visible = False
        p.ygrid.visible = False

        p.xaxis.formatter = bokeh.models.NumeralTickFormatter(format="0 %")
        p.xaxis.minor_tick_line_color = None

        p.quad(
            line_color="white",
            fill_color="fill_color",
            source=self.cds_variance,
        )

        self.figure_variance = p
        return None
    

    def on_ui_multichoice_columns_change(self, attr, old, new):
        """The user changed the columns to consider for the PCA."""
        if self.is_reloading:
            return None
        
        self.update_pca()
        return None
    