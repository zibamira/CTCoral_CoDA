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


# Logger configuration
def init_logging():
    formatter = logging.Formatter("{levelname} :: {filename}:{lineno} :: {message}", style="{")

    console = logging.StreamHandler(stream=sys.stderr)
    console.setLevel(logging.NOTSET)    
    console.setFormatter(formatter)

    logging.basicConfig(handlers=[console], level=logging.INFO)
    return None
    
init_logging()

# Path configuration
this_dir = pathlib.Path(__file__).parent
instance_dir = this_dir.parent / "instance"
data_dir = instance_dir / "data"

# Restore the work data.
logging.info("Restoring original data ...")
shutil.copytree(instance_dir / "data_copy", instance_dir / "data", dirs_exist_ok=True)

# Amira resources
logging.info("Loading shared Amira resources.")
ipc_connectivity = amira.data.graph(data_dir / "instance_connectivity.json", mode="r")
ipc_features = amira.data.spreadsheet(data_dir / "instance_features.json", mode="r")
ipc_segmentation = amira.data.array(data_dir / "instance_segmentation.json", mode="r")

# Feature plot
logging.info("Creating SPLOM ...")

# Create some fake labels for testing.
ipc_features.df["label"] = np.random.randint(0, 5, ipc_features.df.shape[0]).astype(str)

# Choose the currently active columns.
features_df = ipc_features.df
features_columns = ["Volume3d", "VoxelFaceArea", "BaryCenterZ", "label"]
features_bokeh = bokeh.models.ColumnDataSource(features_df)

# Create an IPC sink for the selection mask.
print("Creating output sinks.")
ipc_selection = amira.data.array(
    data_dir / "mask.json", mode="w", shape=ipc_segmentation.array.shape,
    bounding_box=ipc_segmentation.bounding_box, dtype=np.uint8
)


import time
import threading


_last_update = time.time()
def update_thread():
    """Checks periodically if the current Bokeh selection changed
    and propagates the changes to Amira.
    """
    global _last_update
    while True:
        print("CHECK FIRE")
        if _last_update is None:
            return None
        elif abs(time.time() - _last_update) > 0.5:
            ipc_selection.ipc_write()
            _last_update = None
            print("FIRE")
        time.sleep(0.5)
    return None


# thread0 = threading.Thread(target=update_thread, daemon=True).start()


def features_splom_selection_callback(attr, old, new):
    """Called when the user selection changes."""
    global _last_update
    print("callback")
    # print("  attr", attr)
    # print("  old ", old)
    # print("  new ", new)
    # if _last_update is None or time.time() - _last_update > 1:
    #     print("Write")
    #     mask = np.isin(ipc_segmentation.array, new, assume_unique=True)
    #     ipc_selection.array[:] = mask.astype("u8")
    #     ipc_selection.ipc_write()
    #     _last_update = time.time()
    return None


def features_splom():
    """Shows a scatterplot matrix (SPLOM) for the selected
    raw features of the :data:`ipc_features` spreadsheet.
    """
    global features_bokeh
    global features_df 
    global features_columns
    
    # Create shortcuts for the data source.
    df = features_df
    source = features_bokeh
    columns = features_columns
    ncolumns = len(columns) - 1

    # Wait for changes in the selection.
    source.selected.on_change("indices", features_splom_selection_callback)

    # Create the ranges.
    x_ranges = []
    y_ranges = []
    for i in range(ncolumns):
        column = columns[i]
        values = df[column]
        vmin = values.min()
        vmax = values.max()        
        x_range = bokeh.models.Range1d(vmin, vmax, bounds=(vmin, vmax), name=f"x_range_{column}")
        y_range = bokeh.models.Range1d(vmin, vmax, bounds=(vmin, vmax), name=f"y_range_{column}")
        x_ranges.append(x_range)
        y_ranges.append(y_range)

    # Create the axes.
    x_axes = []
    y_axes = []
    for i in range(ncolumns):
        column = columns[i]
        values = df[column]
        x_axis = bokeh.models.LinearAxis(axis_label=df.columns[i], x_range_name=f"x_range_{column}")
        y_axis = bokeh.models.LinearAxis(axis_label=df.columns[i], y_range_name=f"y_range_{column}")
        x_axes.append(x_axis)
        y_axes.append(y_axis)

    # Prepare the label / classes for the histogram plots.
    labels = df["label"]
    labels_unique = np.sort(np.unique(labels))
    labels2id = {label: i for i, label in enumerate(labels_unique)}
    labels_int = np.array([labels2id[label] for label in df["label"]])

    # Use the labels (classes) as colormap.
    colormap = bokeh.transform.factor_cmap(
        "label", palette=bokeh.palettes.Spectral5, factors=labels_unique.astype(str)
    )

    # Create the SPLOT plots.
    grid = []
    for irow in range(ncolumns):
        # Add a new row to the grid.
        row = []
        grid.append(row)

        for icol in range(ncolumns):
            x_range = x_ranges[icol]
            y_range = y_ranges[irow]

            # Create a histogram for the plots on the SPLOM diagonal.
            if irow == icol:
                x_values = df[columns[icol]]
                x_min = x_values.min()
                x_max = x_values.max()
                x_range = (x_min, x_max)
                x_bins = 10
                
                y_min = 0
                y_max = len(labels_unique)
                y_range = (y_min, y_max)
                y_bins = len(labels_unique)
                
                hist, xedges, yedges = np.histogram2d(
                    x=x_values, 
                    y=labels_int,
                    bins=(x_bins, y_bins), 
                    range=(x_range, y_range)
                )

                # Pack the histogram data in a dictionary for bokeh to process.
                data = {labels_unique[i]: hist[:, i] for i in range(len(labels_unique))}
                data["xedges"] = (xedges[:-1] + xedges[1:])/2.0

                # Compute the bin width for the stack area widgets.
                bin_width = np.min(np.abs(np.diff(data["xedges"])))
                max_bin_count = np.max(np.sum(hist, axis=1))

                # TODO: Link the colormap client-side.
                colors = bokeh.palettes.Spectral5

                # Create the histogram plot.
                p = bokeh.plotting.figure(
                    width=250, height=250, x_range=x_range, 
                    y_range=bokeh.models.Range1d(0, max_bin_count, bounds=(0, max_bin_count))
                )
                p.vbar_stack(
                    labels_unique, x="xedges", source=data, fill_color=colors, 
                    line_color="white", width=bin_width
                )
                p.xaxis.visible = False
                p.yaxis.visible = False
                p.xgrid.visible = False
                p.ygrid.visible = False

            # Create scatter plots for upper-diagonal plots.
            elif icol > irow:
                p = bokeh.plotting.figure(
                    width=250, height=250, x_range=x_range, y_range=y_range,
                    tools="pan,lasso_select,poly_select,box_zoom,wheel_zoom,reset,hover",
                    syncable=True
                )
                p.scatter(
                    source=source, x=columns[icol], y=columns[irow], 
                    color=colormap, alpha=0.6, size=8.0,
                    syncable=True
                    
                )
                p.xaxis.visible = False
                p.yaxis.visible = False

            else:
                p = None

            row.append(p)

    # Create "fake" plots for the y-axes. The only purpose for these
    # plots is to show the axis on top of the SPLOM.
    for irow in range(ncolumns):
        p = bokeh.plotting.figure(
            width=80, height=250, 
            x_range=x_ranges[irow], y_range=y_ranges[irow], 
            y_axis_location="right", outline_line_color=None
        )
        p.scatter([], [])
        p.xaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        p.yaxis.axis_label = columns[irow]
        p.yaxis.ticker.desired_num_ticks = 4
        grid[irow].append(p)

    # Create "fake" plots for the x-axes. The only purpose for these
    # plots is to show the axis on the right side of the SPLOM.
    grid.insert(0, [])
    for icol in range(ncolumns):
        p = bokeh.plotting.figure(
            width=250, height=60, 
            x_range=x_ranges[icol], y_range=y_ranges[icol], 
            x_axis_location="above", outline_line_color=None
        )
        p.scatter([], [])
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        p.xaxis.axis_label = columns[icol]
        p.xaxis.ticker.desired_num_ticks = 4
        grid[0].append(p)

    # Create an empty plot in the top-right corner.
    grid[0].append(None)

    # Wrap everything in a proper bokeh layout.
    grid = bokeh.layouts.gridplot(grid)
    grid.toolbar_location = "right"
    return grid


def features_table():
    """Shows the :data:`ipc_spreadsheet` raw features as a spreadsheet.
    Only the columns which are currently selected by the user are displayed.
    """
    global features_df
    global features_bokeh
    global features_columns

    # Use some shortcuts.
    df = features_df
    source = features_bokeh
    columns = features_columns
    
    # Create a column for each feature.
    table_columns = [bokeh.models.TableColumn(field=name, title=name) for name in columns]
    table = bokeh.models.DataTable(
        source=source, columns=table_columns, sizing_mode="stretch_both",
        selectable=True, sortable=True, syncable=True, autosize_mode="fit_columns",
        scroll_to_selection=True, reorderable=True
    )
    return table


def umap_thread():
    """Runs UMAP in the background whenenver the data changes or features
    are added or removed.
    """
    return None


def umap_splom():
    """Shows the UMAP components in a SPLOM."""
    p = bokeh.plotting.figure()
    return p


def umap_table():
    """Shows the UMAP components in a dedicated table."""
    p = bokeh.plotting.figure()
    return p


# ---- graph ----


def graph():
    """Draws the coral connectivity graph. The result is a dendrogram."""
    nxgraph = ipc_connectivity.graph

    # Layout
    def scale_layout(flayout):
        """Decorates a layout function so that the returned positions
        will be normalized, i.e. they are centered at the origin and
        scaled to [-1, 1]^2.
        """
        def wrapped(*args, **kargs):
            pos = flayout(*args, **kargs)
            pos = np.array(list(pos.values()))
            pos -= np.mean(pos, axis=0)
            pos /= np.std(pos, axis=0)
            pos = {i: pos[i] for i in range(pos.shape[0])}
            return pos
        return wrapped
        
    layout = "dot"
    if layout == "dot":
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.nx_pydot.graphviz_layout), 
            prog="dot"
        )
    elif layout == "twopi":
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.nx_pydot.graphviz_layout), 
            prog="twopi"
        )
    elif layout == "circo":
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.nx_pydot.graphviz_layout), 
            prog="circo"
        )
    else:
        graph = bokeh.plotting.from_networkx(
            nxgraph, scale_layout(nx.drawing.spring_layout)
        )

    source_nodes = graph.node_renderer.data_source
    source_edges = graph.edge_renderer.data_source

    # Colormap
    #
    # * factor_cmap: the label must be of type "str"
    # * factor_cmap: the color palette must be large enogough
    labels = [str(e[0]) for e in source_nodes.data["label"]]
    labels_unique = np.sort(np.unique(labels))

    palette = itertools.cycle(bokeh.palettes.Spectral11)
    palette = [next(palette) for i in labels_unique]

    colormap = bokeh.transform.factor_cmap(
        "label", palette=palette, factors=labels_unique,
    )

    # node renderer

    source_nodes.data["label"] = labels
    graph.node_renderer.glyph = bokeh.models.Ellipse(
        width=0.2, height=0.2, fill_color=colormap
    )
    graph.inspection_policy = bokeh.models.NodesOnly()

    # edge renderer

    graph.edge_renderer.selection_glyph = bokeh.models.MultiLine(line_color="blue", line_width=5)
    graph.edge_renderer.hover_glyph = bokeh.models.MultiLine(line_color="red", line_width=10)

    # plot 

    p = bokeh.plotting.figure(
        tooltips=[
            ("index", "@index"),
            ("label", "@label"),
            ("generation", "@shortest_distance")
        ],
        sizing_mode="scale_both",
        match_aspect=True,
        x_axis_location=None,
        y_axis_location=None
    )
    p.grid.grid_line_color = None
    p.renderers.append(graph)
    return p


def graph_vertex_table():
    """Shows the vertex attributes of the graph."""
    df = nx.to_pandas_edgelist(ipc_connectivity.graph)
    source = bokeh.models.ColumnDataSource(df)

    columns = [
        bokeh.models.TableColumn(field=name, title=name) for name in df.columns
    ]
    table = bokeh.models.DataTable(
        source=source, width=400, columns=columns, sizing_mode="stretch_both"
    )
    return table


def graph_edge_table():
    """Shows the edge attributes of the graph."""
    df = nx.to_pandas_edgelist(ipc_connectivity.graph)
    source = bokeh.models.ColumnDataSource(df)

    columns = [
        bokeh.models.TableColumn(field=name, title=name) for name in df.columns
    ]
    table = bokeh.models.DataTable(
        source=source, width=400, columns=columns, sizing_mode="stretch_both"
    )
    return table


tabs = bokeh.models.Tabs(tabs=[
    bokeh.models.TabPanel(child=features_splom(), title="Features SPLOM"),
    bokeh.models.TabPanel(child=features_table(), title="Features Table"),
    bokeh.models.TabPanel(child=umap_splom(), title="UMAP SPLOM"),
    bokeh.models.TabPanel(child=umap_table(), title="UMAP Table"),
    bokeh.models.TabPanel(child=graph(), title="Graph"),
    bokeh.models.TabPanel(child=graph_vertex_table(), title="Graph Vertex Table"),
    bokeh.models.TabPanel(child=graph_edge_table(), title="Graph Edge Table")
], active=4, sizing_mode="stretch_both", syncable=True)

document = bokeh.plotting.curdoc()
document.add_root(tabs)