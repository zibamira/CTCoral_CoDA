#!/usr/bin/env python3

"""
:mod:`run`

Sets up the WSGI application and starts it.
"""

import bokeh
import bokeh.plotting

import cora
import cora.application
import cora.data_provider


provider = cora.data_provider.RandomDataProvider()
app = cora.application.Application(provider)
app.reload()

doc = bokeh.plotting.curdoc()
doc.add_root(app.layout)
doc.set_title("Cora - The Coral Explorer")