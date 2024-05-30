"""
:mod:`coda.view.umap`

This module implements a view for computing the UMAP embedding
on a user defined subset of the input columns. UMAP is a modern, non-linear
alternative to PCA.

:todo: Perform the computations asynchronously in a worker thread 
       so that the IO loop and server does not block.
"""

import random
from typing import List, Literal

import bokeh
import bokeh.models

import sklearn
import sklearn.preprocessing
import sklearn.pipeline

import pandas as pd
import numpy as np
import umap

import coda.utils
from coda.application import Application
from coda.view.base import ViewBase


__all__ = [
    "UMAPView"
]


class UMAPView(ViewBase):
    """This view allows the user to interactively run the UMap dimensionality
    reduction algorithm on a subset of the input data.

    The UMAP embedding is computed in a worker thread so that the server 
    does not block while waiting for the result.
    """

    def __init__(self, app: Application):
        super().__init__(app)

        #: UI for selecting the columns that should be used in the UMAP
        #: reduction.
        self.ui_columns = bokeh.models.MultiChoice(
            title="Columns",
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

        #: UI with the last random state used to compute
        #: the embedding.
        self.ui_seed = bokeh.models.TextInput(
            title="Random State",
            value=str(random.SystemRandom().randint(0, 2**32)),
            disabled=True
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
            self.ui_seed,
            self.ui_apply
        ]
        return None
    

    def reload_df(self):
        """Reload the data frame and recompute the Umap embedding."""
        columns = coda.utils.scalar_columns(self.app.df)
        
        selection = self.ui_columns.value
        selection = [column for column in selection if column in columns]

        self.ui_columns.options = columns
        self.ui_columns.value = selection

        self.compute_umap()
        return None
    
    
    def compute_umap(self):
        """Computes the UMap embedding."""
        self.ui_apply.disabled = True

        try:
            # Extract the selected columns from the dataframe.
            columns = self.ui_columns.value
            values = self.app.df[columns]

            # Break if no column is selected or at least
            # one column contains a nan value.
            if not columns:
                return None
            if pd.isnull(values).any().any():
                return None
            
            # Apply the standard preprocessing suggested in the UMAP documentation.
            scaler = sklearn.preprocessing.StandardScaler()
            values = scaler.fit_transform(values)

            # Compute the embedding.
            n_components = self.ui_ncomponents.value
            random_state = int(self.ui_seed.value)

            reducer = umap.UMAP(
                n_neighbors=n_components,
                n_components=self.ui_ncomponents.value,
                min_dist=self.ui_min_dist.value,
                spread=self.ui_spread.value,
                random_state=random_state
            )
            embedding = reducer.fit_transform(values)

            # Update the dataframe.
            for i in range(n_components):
                self.app.df[f"umap:feature:{i}"] = embedding[:, i]
            
            self.app.push_df_to_cds(vertex=True)
        finally:
            self.ui_apply.disabled = False
        return None
    

    def on_ui_apply_click(self):
        """Recompute UMap."""
        if self.is_reloading:
            return None
        
        # Create a new seed and recompute the embedding.
        self.ui_seed.value = str(random.SystemRandom().randint(0, 2**32))
        self.compute_umap()
        return None