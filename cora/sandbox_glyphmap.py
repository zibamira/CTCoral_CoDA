"""
:mod:`cora.app`

Bootstraps and launches the Bokeh application.
"""

import sys
sys.path.insert(1, "/srv/public/bschmitt/py_ipc")

import itertools
import logging
import pathlib
from pprint import pprint   
import shutil
from typing import Dict, List, Optional

import bokeh
import bokeh.plotting
import bokeh.model
import bokeh.models
import bokeh.layouts

import hxipc as amira
import hxipc.data

import pandas as pd
import numpy as np
import scipy as sp
import networkx as nx
import sklearn
import sklearn.preprocessing
import umap



df = pd.DataFrame.from_dict({
    "col A": np.random.random(100),
    "col B": np.random.standard_normal(100),
    "col C": np.random.random(100)
})

cds = bokeh.models.ColumnDataSource(df)

p = bokeh.plotting.figure(
    width=500, 
    height=700,
    syncable=True
)
p.scatter(
    x="col A",
    y="col B",
    syncable=True,
    source=cds
)


def change(attr, new, old):
    print("change xy")

    p = bokeh.plotting.figure(
        width=500, 
        height=700,
        syncable=True
    )
    p.scatter(
        x=select_x.value,
        y=select_y.value,
        syncable=True,
        source=cds
    )
    layout.children[1] = p
    return None


select_x = bokeh.models.Select(
    title="X Axis",
    options=cds.column_names[1:]
)
select_x.on_change("value", change)

select_y = bokeh.models.Select(
    title="Y Axis",
    options=cds.column_names[1:]
)
select_y.on_change("value", change)


controls = bokeh.layouts.column([
    select_x, 
    select_y
])

layout = bokeh.layouts.row([
    controls, 
    p
])
doc = bokeh.plotting.curdoc()
doc.add_root(layout)