"""
:mod:`Index`

This module contains the handlers for the landing page.
"""


from aiohttp import web


async def index(request):
    """Delivers the landing page."""
    return web.Response(text="Hello Cora!")