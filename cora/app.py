"""
:mod:`cora.app`

Bootstraps and launches the Bokeh application.
"""

import sys
sys.path.insert(1, "/srv/public/bschmitt/py_ipc")

import logging
import pathlib
import shutil

import bokeh
import bokeh.plotting
import bokeh.model
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

    logging.basicConfig(handlers=[console], level=logging.DEBUG)
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

print(ipc_features.df["label"])


features_df = ipc_features.df
features_columns = ["Volume3d", "Area3d", "BaryCenterZ", "label"]
features_bokeh = bokeh.models.ColumnDataSource(features_df)


def splom_selection_callback():
    """Called when the user selection changes."""


    return None


def features_splom():
    """Shows a scatterplot matrix (SPLOM) for the selected
    raw features of the :data:`ipc_features` spreadsheet.
    """
    global features_bokeh, features_df, features_columns

    df = features_df
    source = features_bokeh

    columns = features_columns
    ncolumns = len(columns) - 1

    print(df)

    # Create the ranges.
    x_ranges = []
    y_ranges = []
    for i in range(ncolumns):
        column = columns[i]
        df_column = df[column]
        vmin = df_column.min()
        vmax = df_column.max()
        x_ranges.append(bokeh.models.Range1d(vmin, vmax, bounds=(vmin, vmax), name=f"x_range_{column}"))
        y_ranges.append(bokeh.models.Range1d(vmin, vmax, bounds=(vmin, vmax), name=f"y_range_{column}"))

    # Create the axes.
    x_axes = []
    y_axes = []
    for i in range(ncolumns):
        column = columns[i]
        df_column = df[column]
        x_axis = bokeh.models.LinearAxis(
            axis_label=df.columns[i],
            x_range_name=f"x_range_{column}"
        )
        y_axis = bokeh.models.LinearAxis(
            axis_label=df.columns[i],
            y_range_name=f"y_range_{column}"
        )
        x_axes.append(x_axis)
        y_axes.append(y_axis)

    # Initialise the SPLOM grid.
    grid = []

    tools = {
        "pan": bokeh.models.PanTool(),
        "lasso": bokeh.models.LassoSelectTool(),
        "box_zoom": bokeh.models.BoxZoomTool(),
        "wheel_zoom": bokeh.models.WheelZoomTool(),
        "reset": bokeh.models.ResetTool()
    }

    colormap = bokeh.transform.factor_cmap(
        "label", palette=bokeh.palettes.Spectral5, factors=sorted(df["label"].unique())
    )
    

    for irow in range(ncolumns):

        # Add a new row to the grid.
        row = []
        grid.append(row)

        for icol in range(ncolumns):
            x_range = x_ranges[icol]
            y_range = y_ranges[irow]

            if irow == icol:
                
                xvalues = df[columns[icol]]
                xmin = xvalues.min()
                xmax = xvalues.max()
                xrange = (xmin, xmax)
                xbins = 10
                
                labels = df["label"].astype(int).unique()
                label2id = {labels[i]: i for i in range(len(labels))}
                yvalues = np.arange(len(labels))
                ymin = 0
                ymax = len(labels)
                yrange = (ymin, ymax)
                ybins = len(labels)
                
                hist, xedges, yedges = np.histogram2d(
                    x=xvalues, y=df["label"].astype(int),
                    bins=(xbins, ybins), range=(xrange, yrange)
                )

                # hist = np.sum(hist, axis=1)
                
                print()
                print(yedges)
                print(xedges)
                print(hist)

                data = {
                    str(i): hist[:, i] for i in range(len(labels))
                }
                # data["label"] = labels.astype(str)
                data["xedges"] = (xedges[:-1] + xedges[1:])/2.0
                # data["xedges"] = np.arange(10).astype(str)
                from pprint import pprint
                pprint(data)

                colors = bokeh.palettes.Spectral5

                # TODO: 

                # colors = ["#c9d9d3", "#718dbf", "#e84d60", "#c9d9d3", "#718dbf"]

                # TODO: Compute a histogram for each label and draw a stacked bar chart.
                # values = df[df.columns[icol]]
                # hist, bin_edges = np.histogram(values, bins=10)
                # y_range = bokeh.models.Range1d(0, hist.max(), bounds=(0, hist.max()))
                # p = bokeh.plotting.figure(width=250, height=250, x_range=x_range, y_range=y_range)
                # p.quad(top=hist, bottom=0, left=bin_edges[:-1], right=bin_edges[1:], line_color="white")

                max_count = np.max(np.sum(hist, axis=1))
                print(max_count)
                y_range = bokeh.models.Range1d(0, max_count, bounds=(0, max_count))
                p = bokeh.plotting.figure(
                    width=250, height=250, #x_range=np.arange(10).astype(str)
                    x_range=x_range, y_range=y_range)

                p.vbar_stack(labels.astype(str), x="xedges", source=data, fill_color=colors, line_color="white", width=np.max(np.abs(np.diff(data["xedges"]))))

                p.xaxis.visible = False
                p.yaxis.visible = False
                p.xgrid.visible = False
                p.ygrid.visible = False

            elif icol > irow:
                p = bokeh.plotting.figure(
                    width=250, height=250, x_range=x_range, y_range=y_range,
                    tools=list(tools.values())
                )
                p.xaxis.visible = False
                p.yaxis.visible = False

                p.scatter(
                    source=source, x=columns[icol], y=columns[irow], alpha=0.8, size=4.0,
                    color=colormap
                )

            else:
                p = None

            row.append(p)

    # Create "fake" plots for the y-axes.
    for irow in range(ncolumns):
        p = bokeh.plotting.figure(width=80, height=250, x_range=x_ranges[irow], y_range=y_ranges[irow], y_axis_location="right", outline_line_color=None)
        p.scatter([], [])
        p.xaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        p.yaxis.axis_label = df.columns[irow]
        p.yaxis.ticker.desired_num_ticks = 4
        grid[irow].append(p)

    grid.insert(0, [])
    for icol in range(ncolumns):
        p = bokeh.plotting.figure(width=250, height=60, x_range=x_ranges[icol], y_range=y_ranges[icol], x_axis_location="above", outline_line_color=None)
        p.scatter([], [])
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        p.xaxis.axis_label = df.columns[icol]
        p.xaxis.ticker.desired_num_ticks = 4
        grid[0].append(p)
    grid[0].append(None)

    grid = bokeh.layouts.gridplot(grid)

    # grid.toolbar.active_drag = tools["pan"]
    # grid.toolbar.active_inspect = tools["wheel"]
    # grid.toolbar.active_scroll = tools["wheel"]
    grid.toolbar_location = "right"
    
    
    return grid


def features_table():
    """Shows the :data:`ipc_spreadsheet` raw features as a spreadsheet."""
    global features_df, features_bokeh

    df = features_df
    source = features_bokeh
    columns = features_columns


    columns = [
        bokeh.models.TableColumn(field=name, title=name) for name in columns
    ]
    data_table = bokeh.models.DataTable(
        source=source, columns=columns, sizing_mode="stretch_both",
        selectable=True, sortable=True, syncable=True, autosize_mode="fit_columns",
        scroll_to_selection=True
    )
    return data_table


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


def graph():
    """Shows the coral connectivity in a graph."""
    # TODO: Check if there are multiple components.
    #       and color, as well as layout them individually.

    # TODO: Use the same colormap as in Amira.
    # TODO: Add tooltips for edge attributes
    # TODO: Add a selection tool (select vertices)
    # TODO: Add tooltips to the attributes.
    # TODO: Create a custom plot for each connected components,
    #       or add a dropdown.

    graph = bokeh.plotting.from_networkx(
        ipc_connectivity.graph, nx.spring_layout, scale=1.8, center=(0.0, 0.0)
    )
    graph.node_renderer.data_source.data["index"] = list(range(len(ipc_connectivity.graph)))
    graph.node_renderer.glyph = bokeh.models.Rect(width=0.1, height=0.1, fill_color="yellow")
    
    p = bokeh.plotting.figure(
        x_range=(-2, 2), y_range=(-2, 2),
        x_axis_location=None, y_axis_location=None,
        tools="hover", tooltips="index: index"
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


# Splom:
#       Scatter plots for numerical data
#       Histogram for numerical + discrete (labels)

# Umap:
#       Simple Splom

# DataTable
#       Table view of the features

# GraphView
#       Graph Rendering of the connectivity

# Feature selection
#       Features to display
#       Labels to overlay with
#           Color encode class or use different glyphs?
#           Numerical Class: Color
#       Also: Is categorical vs is numeric.

# Image / Mesh Preview?
#       Could also be an annotation/tooltip

# Page
#       Sidebar: Feature Selection
#       Mainview: Tabwidget
#           different plots and visualizations

i = 0 
def callback():
    global i
    print("CALLBACK !", 2*i)
    i += 1
    return None


button = bokeh.models.Button(label="Hit me!")
button.on_click(callback)

tabs = bokeh.models.Tabs(tabs=[
    bokeh.models.TabPanel(child=features_splom(), title="Features SPLOM"),
    bokeh.models.TabPanel(child=features_table(), title="Features Table"),
    bokeh.models.TabPanel(child=umap_splom(), title="UMAP SPLOM"),
    bokeh.models.TabPanel(child=umap_table(), title="UMAP Table"),
    bokeh.models.TabPanel(child=graph(), title="Graph"),
    bokeh.models.TabPanel(child=graph_vertex_table(), title="Graph Vertex Table"),
    bokeh.models.TabPanel(child=graph_edge_table(), title="Graph Edge Table")
], active=1, sizing_mode="stretch_both")

document = bokeh.plotting.curdoc()
document.add_root(tabs)