"""
:mod:`cluster`

This module implements the dimensionality reduction UI. The user can
choose the features which should be used for the reduction. 

The computed embedding is then visualized in a SPLOM plot similar to the 
features SPLOM.
"""

import logging
import pathlib
from pprint import pprint
from typing import List

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.layouts

import pandas as pd
import numpy as np
import sklearn
import sklearn.preprocessing
import sklearn.pipeline
import umap


__all__ = [
    "selection_callback",
    "fit_reduction",
    "eval_reduction",
    "splom",
    "table"
]


#: The sklearn compatible embedder.
reducer = None
embedding = None


def selection_callback(attr, old, new):
    """Called when the user selection changes."""
    print("cluster selection changed.")
    return None


def create_reducer(mode="PCA"):
    """Creates the sklearn pipeline, including pre-processing and
    machine learning algorithm that produce the embedding.
    """
    global reducer

    if reducer is not None:
        return

    if mode == "UMAP":
        reducer = sklearn.pipeline.Pipeline([
            ("scaler", sklearn.preprocessing.StandardScaler()),
            ("reducer", umap.UMAP(n_neighbors=10, min_dist=0.1, n_components=4))
        ])
    else:
        reducer = sklearn.decomposition.PCA()
    return None


def fit_reduction(
    df: pd.DataFrame,
    columns: List[str] 
):
    """Computes a new embedding given the selected columns
    of the data frame.
    """
    global reducer
    global embedding

    # Create the reducer if not yet done.
    create_reducer()

    # Train the model and evaluate.
    values = df[columns].select_dtypes(include=np.number)
    embedding = reducer.fit_transform(values)
    return None


def eval_reduction(
    df: pd.DataFrame,
    columns: List[str]
):
    """Evaluates a previously computed embedding given
    the selected columns of a Data Frame.
    """
    global reducer
    global embedding

    values = df[columns].select_dtypes(include=np.number)
    embedding = reducer.transform(values)
    return None


def splom(
    df: pd.DataFrame,
    columns: List[str],

):
    """Shows a SPLOM plot of the computed embedding."""
    global embedding
    
    # Create a SPLOM with the desired number of components.
    plots = []
    for irow in range(embedding.shape[1]):
        for icol in range(embedding.shape[1]):
            if icol < irow:
                plots.append(None)
            elif icol == irow:
                pass
            else:
                p = bokeh.plotting.figure(width=250, height=250)
                p.scatter(embedding[:, irow], embedding[:, icol])
                plots.append(p)

    grid = bokeh.layouts.gridplot(plots, ncols=embedding.shape[1])
    grid.toolbar_location = "right"
    return grid


def table(
    df: pd.DataFrame,
    columns: List[str]
):
    """Shows the computed embedding components in a tabular
    view.
    
    This view is mostly for completness and usually not of
    particular interest. At least for the UMAP embedding.
    """
    global embedding
    
    data = {f"component {i}": embedding[:, i] for i in range(embedding.shape[1])}
    source = bokeh.models.ColumnDataSource(data)

    # Create a column for each component.
    table_columns = [
        bokeh.models.TableColumn(field=name, title=name) for name in data.keys()
    ]

    # Put everything together.
    table = bokeh.models.DataTable(
        source=source, columns=table_columns, sizing_mode="stretch_both",
        selectable=True, sortable=True, syncable=True,
        scroll_to_selection=True, reorderable=True
    )
    return table