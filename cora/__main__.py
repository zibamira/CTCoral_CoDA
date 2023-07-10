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


# Create the parser.
parser = argparse.ArgumentParser("cora")
subparsers = parser.add_subparsers(
    dest="data_provider", required=True
)

parser.add_argument(
    "--start-browser", action="store_const", const=True,
    help="Open a new tab in the browser with cora."
)

# Create the parser for the filesystem provider. This CLI takes
# explicit paths for all input and output files.
fs_parser = subparsers.add_parser(
    "filesystem", 
    help="A data provider using CSV spreadsheets in the local filesystem."
)
fs_parser.add_argument(
    "--vertex", action="extend", type=pathlib.Path, nargs="*",
    help="Path to a CSV spreadsheet containing vertex data."
)
fs_parser.add_argument(
    "--edge", action="extend", type=pathlib.Path, nargs="*",
    help="Path to a CSV spreadsheet containing edge data."
)
fs_parser.add_argument(
    "--vertex-selection", action="store", type=pathlib.Path,
    help="Path to the CSV file Cora will write the current vertex selection to."
)
fs_parser.add_argument(
    "--edge-selection", action="store", type=pathlib.Path,
    help="Path to the CSV file Cora will write the current edge selection to."
)

# Create a parser for the development, random data provider.
rnd_parser = subparsers.add_parser(
    name="random",
    help="Ignore the provided files and use random test data as input."
)

# Create a parser for the Amira data provider.
amira_parser = subparsers.add_parser(
    name="amira",
    help=(
        "Use a shared directory linked to an active Amira project. "
        "This data provider integrates with the hxcora package. "
        "If no 'directory' is given, then CORA will look for the latest "
        "Amira instance that created an Amira-Cora directory. This works "
        "well if a single Amira instance is running."
    )
)
amira_parser.add_argument(
    "--directory", action="store", type=pathlib.Path,
    help="Path to the directory shared with Amira."
)

# Parse the arguments.
args = parser.parse_args()

# Setup the selected data provider.
if args.data_provider == "random":
    provider = cora.data_provider.RandomDataProvider()

elif args.data_provider == "filesystem":
    provider = cora.data_provider.FilesystemDataProvider()
    if args.vertex:
        for path in args.vertex:
            provider.add_vertex_csv(path)
    if args.edge:
        for path in args.edge:
            provider.add_edge_csv(path)

    provider.path_vertex_selection = args.vertex_selection
    provider.path_edge_selection = args.edge_selection

elif args.data_provider == "amira":
    if not args.directory:
        args.directory = cora.data_provider.AmiraDataProvider.zero_conf_amira_cora_directory()
        if not args.directory:
            print("Could not find an active Amira instance.")
            print("Use the '--directory' option to manually set a data directory.")
            exit(1)
    provider = cora.data_provider.AmiraDataProvider(args.directory)
    
else:
    parser.print_help()
    exit(1)


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