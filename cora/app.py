"""
:mod:`cora.app`

This module contains the bootstrapping for the WSGI application.
"""

import pathlib

from aiohttp import web

from . import api
from . import view


async def create_app(instance_dir: pathlib.Path):
    """Creates the WSGI application."""
    app = web.Application(debug=True)

    # Register all routes.
    app.add_routes([
        web.get("/", view.index.index)
    ])
    return app