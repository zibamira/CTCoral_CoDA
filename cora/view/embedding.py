"""
:mod:`cora.view.embedding`

This module implements the dimensionality reduction UI. The user can
choose the features which should be used for the reduction. 

The computed embedding is then visualized in a SPLOM plot similar to the 
features SPLOM.

Contrary to other views, this view/panel contains only the controls 
for the parameters of the machine learning model. The visualization
is done via other panels, e.g. a SPLOM in the left frame.

:todo: Perform the computations asynchronously in a worker thread 
       so that the IO loop and server does not block.
"""

from collections import OrderedDict
import itertools
from pprint import pprint
from typing import List, Literal

import bokeh
import bokeh.models

import sklearn
import sklearn.preprocessing
import sklearn.pipeline

import pandas as pd
import numpy as np
from natsort import natsorted
import networkx as nx
import umap

from cora.application import Application
from cora.utils import scalar_columns
from cora.view.base import ViewBase


__all__ = [
    "PCAView",
    "UMAPView",
    "MLView"
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

        columns = scalar_columns(self.app.df)

        #: UI for selecting the columns that should be used in the PCA
        #: reduction.
        self.ui_multichoice_columns = bokeh.models.MultiChoice(
            title="Columns",
            options=columns,
            value=columns,
            sizing_mode="stretch_width"
        )
        self.ui_multichoice_columns.on_change(
            "value", self.on_ui_multichoice_columns_change
        )

        #: Data source showing the explained variance.
        self.cds_variance = bokeh.models.ColumnDataSource()
        self.figure_variance = None

        # Compute the PCA.
        self.create_variance_figure()
        self.compute()

        # Panel layout.
        self.layout_panel.children = [
            self.ui_multichoice_columns,
            self.figure_variance
        ]
        return None

    def compute(self):
        """Computes the PCA."""
        # Compute the PCA.
        columns = self.ui_multichoice_columns.value
        values = self.app.df[columns]

        reducer = sklearn.decomposition.PCA()
        components = reducer.fit_transform(values)

        # Update the dataframe.
        for i in range(len(columns)):
            self.app.df[f"pca:feature:{i}"] = components[:, i]

        # Update the Bokeh data source.
        for i in range(len(columns)):
            self.app.cds.data[f"pca:feature:{i}"] = components[:, i]

        # Update the variance plot.
        self.update_variance_cds(reducer.explained_variance_ratio_)
        return None
    
    def create_variance_figure(self):
        """Creates the figure and data source displaying the
        variance explained by each component of the PCA.
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
    
    def update_variance_cds(self, variance: np.array):
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
        return None
    
    def on_ui_multichoice_columns_change(self, attr, old, new):
        """The user changed the columns to consider for the PCA."""
        self.compute()
        return None
    

class UMAPView(ViewBase):
    """This view allows the user to interactively run the UMap dimensionality
    reduction algorithm on a subset of the input data.
    """

    def __init__(self, app: Application):
        super().__init__(app)

        columns = scalar_columns(self.app.df)

        #: UI for selecting the columns that should be used in the UMAP
        #: reduction.
        self.ui_columns = bokeh.models.MultiChoice(
            title="Columns",
            options=columns,
            value=columns,
            sizing_mode="stretch_width"
        )

        #: UI for selecting the number of neighbours to consider.
        self.ui_nneighbors = bokeh.models.Spinner(
            title="Number of Neighbors",
            value=15,
            low=2,
            high=100,
            step=1,
            sizing_mode="stretch_width"
        )
        
        #: UI for selecting the dimensionality of the embedding.
        self.ui_ncomponents = bokeh.models.Spinner(
            title="Number of Components",
            value=2,
            low=2,
            high=4,
            step=1,
            sizing_mode="stretch_width"
        )

        #: UI for selecting the minimal distance between embedded points.
        self.ui_min_dist = bokeh.models.Slider(
            title="Minimum Distance",
            value=0.01,
            start=0.0,
            end=1.0,
            step=0.01,
            sizing_mode="stretch_width"
        )

        #: UI for selecting the effective scale of embedded points.
        self.ui_spread = bokeh.models.Slider(
            title="Spread",
            value=1.0,
            start=0.0,
            end=10.0,
            step=0.01,
            sizing_mode="stretch_width"
        )

        #: UI for starting the UMap computation.
        self.ui_apply = bokeh.models.Button(
            label="Apply",
            button_type="primary"
        )
        self.ui_apply.on_click(self.on_ui_apply_click)
        
        # Sidebar layout.
        self.layout_panel.children = [
            self.ui_columns,
            self.ui_nneighbors,
            self.ui_ncomponents,
            self.ui_min_dist,
            self.ui_spread,
            self.ui_apply
        ]
        return None
    
    def compute(self):
        """Computes the UMap embedding."""
        # Extract the selected columns from the dataframe.
        columns = self.ui_columns.value
        values = self.app.df[columns]

        # Apply the standard preprocessing suggested in the UMAP documentation.
        scaler = sklearn.preprocessing.StandardScaler()
        values = scaler.fit_transform(values)

        # Compute the embedding.
        n_components = self.ui_ncomponents.value

        reducer = umap.UMAP(
            n_neighbors=n_components,
            n_components=self.ui_ncomponents.value,
            min_dist=self.ui_min_dist.value,
            spread=self.ui_spread.value
        )
        embedding = reducer.fit_transform(values)

        # Update the dataframe.
        for i in range(n_components):
            self.app.df[f"umap:feature:{i}"] = embedding[:, i]

        # Update the Bokeh data source.
        for i in range(n_components):
            self.app.cds.data[f"umap:feature:{i}"] = embedding[:, i]
        return None

    def on_ui_apply_click(self):
        self.compute()
        return None
    

class MLView(ViewBase):
    """This view acts as a proxy for the actual machine learning method.
    
    Upon selecting the ml-algorithm, the view will activate the corresponding
    view handler.
    """

    ML_METHODS = {
        "UMAP": UMAPView,
        "PCA": PCAView
    }

    def __init__(self, app: Application):
        super().__init__(app)

        #: UI for choosing the machine learning method.
        self.ui_method = bokeh.models.Select(
            title="Method",
            options=list(natsorted(self.ML_METHODS.keys())),
            value="PCA",
            sizing_mode="stretch_width"
        )
        self.ui_method.on_change("value", self.on_ui_method_change)

        #: The handler for the currently chosen machine learning method.
        self.ml_view: ViewBase = None

        # Create the initial handler.
        self.update()
        return None

    def update(self):
        """Loads the controller for the selected machine learning method."""
        view_cls = self.ML_METHODS[self.ui_method.value]
        self.ml_view = view_cls(self.app)
        
        self.layout_panel.children = [
            self.ui_method,
            self.ml_view.layout_panel
        ]
        return None
    
    def on_ui_method_change(self, attr, old, new):
        self.update()
        return None