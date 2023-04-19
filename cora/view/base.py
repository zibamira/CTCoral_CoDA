"""
:mod:`cora.view.base`

This module contains the base class for all views in the Cora application.
A view is just a panel/visualization that can be shown in the central layout
of the overall application.
"""


import bokeh
import bokeh.models

from cora.application import Application


__all__ = [
    "ViewBase"
]


class ViewBase(object):
    """Base class for different "views". These are the panels
    that can be activated in the application. E.g. the SPLOM,
    flower or graph view.
    """

    def __init__(self, app: "Application"):
        """ """
        #: The Cora :class:`Application` with the data source.
        self.app = app

        #: A layout that is added to the sidebar while this view
        #: is active. This layout should contain the control widgets
        #: specific to this view.
        self.layout_sidebar = bokeh.models.Column(
        )

        #: A layout that is shown as column (panel) in the Cora
        #: appplication. 
        self.layout_panel = bokeh.models.Column(sizing_mode="stretch_both")
        return None
    