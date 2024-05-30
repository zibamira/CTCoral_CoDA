"""
:mod:`coda.view.base`

This module contains the base class for all views in the Coda application.
A view is just a panel/visualization that can be shown in the central layout
of the overall application.
"""

from contextlib import contextmanager

import bokeh
import bokeh.models

from coda.application import Application


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
        #: The Coda :class:`Application` with the data source.
        self.app = app

        #: A layout that is added to the sidebar while this view
        #: is active. This layout should contain the control widgets
        #: specific to this view.
        self.layout_sidebar = bokeh.models.Column(
            sizing_mode="stretch_width"
        )

        #: A layout that is shown as column (panel) in the Coda
        #: appplication. 
        self.layout_panel = bokeh.models.Column(
            sizing_mode="stretch_both"
        )

        #: True if the whole application (or only the component) is currently
        #: being reloaded. 
        #: Checking this state helps to avoid incosistent states and unnecessary
        #: updates.
        #: The reloading is implemented in a recursive manner, so that it may be
        #: set multiple times. 
        self._reload_counter = 0
        return None
    
    @contextmanager
    def begin_reload(self):
        """A context manager that must be used within a reload."""
        self._reload_counter += 1
        try:
            yield
        finally:
            self._reload_counter -= 1
        return None
    
    @property
    def is_reloading(self):
        """True if the view or application is currently being reloaded."""
        return self._reload_counter > 0 or self.app.is_reloading
    
    def reload_df(self):
        """This method is called after the global data frames have been reloaded from
        the data provider. The view must add view specific render information again to
        the global data frames in this step.
        
        :seealso: :attr:`~coda.application.Application.df`,\
                :attr:`~coda.application.Application.df_edges`
        """
        return None
    
    def reload_cds(self):
        """Called **after** the dataframes have been updated by all views and pushed
        to the column data source. The views may update the plots now since all columns
        and features are now present again in both, the Bokeh column data source *and*
        the data frames.

        :seealso: :meth:`reload_df`
                :attr:`~coda.application.Application.cds`,\
                :attr:`~coda.application.Application.cds_edges`
        """
        return None