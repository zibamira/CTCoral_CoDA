#!/usr/bin/env python3

"""
:mod:`run`

Sets up the WSGI application and starts it.
"""

import argparse
import pathlib

import bokeh
import bokeh.plotting
import bokeh.server.server

import cora
import cora.application
import cora.data_provider


# Create the argument parser.
parser = argparse.ArgumentParser()
parser.add_argument(
    "--vertex", action="extend", type=pathlib.Path, nargs="*"
)
parser.add_argument(
    "--edge", action="extend", type=pathlib.Path, nargs="*"
)
parser.add_argument(
    "--vertex-field", action="store", type=pathlib.Path
)
parser.add_argument(
    "--edge-field", action="store", type=pathlib.Path
)
parser.add_argument(
    "--dev-random", action="store_const", const=True,
    help="Ignore the provided files and use random test data as input."
)
parser.add_argument(
    "--preset", action="store", choices=["corals"],
    help="Launch Cora using a preset for the settings."
)
parser.add_argument(
    "--start-browser", action="store_const", const=True,
    help="Open a new tab in the browser with cora."
)
args = parser.parse_args()


# Use random test data.
if args.dev_random:
    provider = cora.data_provider.RandomDataProvider()

# Create the FileSystem data provider using the input
# from the argument parser.
else:
    provider = cora.data_provider.FilesystemDataProvider()
    for path in args.vertex:
        provider.add_vertex_csv(path)
    for path in args.edge:
        provider.add_edge_csv(path)
    if args.vertex_field is not None:
        provider.set_vertex_field(args.vertex_field)
    if args.edge_field is not None:
        provider.set_edge_field(args.edge_field)


def cora_doc(doc):
    """Creates the cora document and application."""
    app = cora.application.Application(provider, doc)
    app.reload()

    doc.add_root(app.layout)
    doc.set_title("Cora - The Coral Explorer")
    return None


server = bokeh.server.server.Server(
    {"/": cora_doc},
    num_procs=1
)
server.start()

if args.start_browser:
    server.io_loop.add_callback(server.show, "/")

server.io_loop.start()