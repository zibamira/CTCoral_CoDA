#!/usr/bin/env python3

"""
:mod:`run`

Sets up the WSGI application and starts it.
"""

import argparse
import asyncio
import pathlib
import sys

import aiohttp

import cora.app

# Check the command line for the instance directory.
this_dir = pathlib.Path(__file__).absolute().parent
parser = argparse.ArgumentParser(
    prog = "CORA - The Coral Explorer",
    description = "Launches the explorer into space. The cyber space."
)
parser.add_argument(
    "instance_dir", 
    type=pathlib.Path, 
    default=this_dir / "instance"
)
args = parser.parse_args()

# Create the WSGI application.
app = asyncio.run(cora.app.create_app(args.instance_dir))


if __name__ == "__main__":
    aiohttp.web.run_app(app)
