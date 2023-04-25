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
    """

    def __init__(self, app: Application):
        super().__init__(app)

        columns = scalar_columns(self.app.df)

        #: UI for selecting the columns that should be used in the PCA
        #: reduction.
        self.ui_multichoice_columns = bokeh.models.MultiChoice(
            title="Columns",
            options=columns,
            value=columns
        )
        self.ui_multichoice_columns.on_change(
            "value", self.on_ui_multichoice_columns_change
        )
        
        #: UI for selecting the number of components that are of interest.
        self.ui_spinner_ncomponents = bokeh.models.Spinner(
            title="Number of Components",
            value=4,
            low=1,
            high=len(columns),
            step=1
        )
        self.ui_spinner_ncomponents.on_change(
            "value", self.on_ui_spinner_ncomponents_change
        )

        # Panel layout.
        self.layout_panel.children = [
            self.ui_multichoice_columns,
            self.ui_spinner_ncomponents
        ]
        return None

    def compute(self):
        """Computes the PCA."""
        # Compute the PCA.
        columns = self.ui_multichoice_columns.value
        values = self.app.df[columns]

        ncomponents = self.ui_spinner_ncomponents.value
        ncomponents = max(1, ncomponents)

        reducer = sklearn.decomposition.PCA()
        components = reducer.fit_transform(values)

        # Update the dataframe.
        for i in range(ncomponents):
            self.app.df[f"pca:feature:{i}"] = components[:, i]

        # Update the Bokeh data source.
        for i in range(ncomponents):
            self.app.cds.data[f"pca:feature:{i}"] = components[:, i]
        return None
    
    def on_ui_multichoice_columns_change(self, attr, old, new):
        self.compute()
        return None

    def on_ui_spinner_ncomponents_change(self, attr, old, new):
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
            value=columns
        )

        #: UI for selecting the number of neighbours to consider.
        self.ui_nneighbors = bokeh.models.Spinner(
            title="Number of Neighbors",
            value=15,
            low=2,
            high=100,
            step=1
        )
        
        #: UI for selecting the dimensionality of the embedding.
        self.ui_ncomponents = bokeh.models.Spinner(
            title="Number of Components",
            value=2,
            low=2,
            high=4,
            step=1
        )

        #: UI for selecting the minimal distance between embedded points.
        self.ui_min_dist = bokeh.models.Slider(
            title="Minimum Distance",
            value=0.01,
            start=0.0,
            end=1.0,
            step=0.01
        )

        #: UI for selecting the effective scale of embedded points.
        self.ui_spread = bokeh.models.Slider(
            title="Spread",
            value=1.0,
            start=0.0,
            end=10.0,
            step=0.01
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
            value="PCA"
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