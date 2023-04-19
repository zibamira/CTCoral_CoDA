"""
:mod:`cora.flower`

This module implements flower glyphs. Not really glyphs, but a single plot
which shows a flower glyph. The flower petals are either wedges (fast
and simple) or parametrized by a curve like the rose curve or tear-drop
curve, which both are more beautiful.
"""

import functools
import itertools
from pprint import pprint
from typing import Dict, List, Any, Literal

import bokeh
import bokeh.plotting
import bokeh.model
import bokeh.models
import bokeh.layouts
import bokeh.palettes

import pandas as pd
import numpy as np


__all__ = [
    "FlowerPlot",
    "FlowerWedge",
    "FlowerCurve"
]


class FlowerPlot(object):
    """Base class for all Flower plots."""

    def __init__(self):
        """ """
        #: *input* The dataframe containing all samples. The data here is used to determine
        #: the overall scale of the petals.
        self.df: pd.DataFrame = None

        #: The dataframe with the current selection. 
        self.df_selection: pd.DataFrame = None

        #: The current selection (indices).
        self.indices: List[int] = None

        #: A description / summary of the whole dataset.
        #: Cached for efficiency.
        self.desc: pd.DataFrame = None

        #: A description / summary of the seletion.
        self.desc_selection: pd.DataFrame = None

        #: The current data dictionary for the column data source.
        #: This dictionary is updated in subclasses and pushed at once
        #: to the ColumnDataSource `cds`.
        self.cds_data: Dict[str, Any] = dict()

        #: The column data source the plot is based on.
        #: If possible, only this source is updated when the selection
        #: changes. This is more performant and less error prone than
        #: recreating the plot every time the user interacts.
        self.cds: bokeh.models.ColumnDataSource = None

        #: The figure displaying the flower.
        self.figure: bokeh.models.Model = None

        #: The renderer for the petals.
        self.petals = bokeh.models.Model = None
        return None

    def set_df(self, df):
        """Replaces the dataframe with the new one."""
        if df is not self.df:
            self.df = df
            self.desc = df.describe()
        return None

    def set_selection(self, indices):
        """Updates the dataframe and description of the selected rows."""
        if indices:
            self.df_selection = self.df.loc[indices]
            self.desc_selection = self.df_selection.describe()
            self.indices = indices
        else:
            self.df_selection = self.df
            self.desc_selection = self.desc
            self.indices = indices
        return None

    def upadte_cds_label_data(self):
        """Updates the positions of the labels.

        The labels are drawn outside each petal, oriented towards
        the center of the flower.
        """
        ncolumns = len(self.df.columns)
        radii = self.cds_data["radius"]

        xs = []
        ys = []
        angles = []
        alignments = []

        for i in range(ncolumns):
            angle = 2.0*np.pi*i/ncolumns

            # Put the text inside the petal if it the petal
            # is "large enough" and draw it outside if it is
            # "too small".
            if radii[i] > 0.7:
                radius = radii[i]/2.0
            else:
                radius = radii[i] + 0.08
            
            # Compute the position of the label 
            # just outside the petal.
            x = np.cos(angle)*radius
            y = np.sin(angle)*radius

            # Orient it towards the center of the flower
            # and make sure it's easy to read. We flip
            # the alignment on the left side of the circle
            # so that the text does not appear upside-down.
            if np.pi/2 <= angle <= np.pi*3/2:
                angle = angle + np.pi
                alignment = "right"
            else:
                alignment = "left"

            xs.append(x)
            ys.append(y)
            angles.append(angle)
            alignments.append(alignment)
    
        self.cds_data.update({
            "label_xs": xs,
            "label_ys": ys,
            "label_angle": angles,
            "label_align": alignments
        })
        return None

    def update_cds_data(self):
        """Recomputes the data :attr:`cds_data` dictionary for the 
        Bokeh ColumnDataSource :attr:`cds`. 
        """
        ncolumns = len(self.df.columns)

        # Extract the attributes relevant for the pedal/wedge size
        # and shape.
        mean_selection = self.desc_selection.loc["mean"]
        min_total = self.desc.loc["min"]
        max_total = self.desc.loc["max"]

        # Divide the circle into segments of the same size.
        # Each column has its own segment. The petals are scaled
        # within 
        delta = 2.0*np.pi/ncolumns
        angles = np.linspace(0.0, 2.0*np.pi, ncolumns, endpoint=False)
        radius = (mean_selection - min_total)/(max_total - min_total)
        start_angle = angles - delta/2.0
        end_angle = angles + delta/2.0
        color = bokeh.palettes.all_palettes["Spectral"][ncolumns]

        # Update the column data source.
        self.cds_data.update({
            "start_angle": start_angle,
            "end_angle": end_angle,
            "radius": radius,
            "fill_color": color,
            "column": self.df.columns,
            "mean": mean_selection,
            "color": bokeh.palettes.all_palettes["Spectral"][ncolumns],
        })

        # Also update the label positions.
        self.upadte_cds_label_data()
        return None
    
    def update_cds(self):
        """Replaces the current Bokeh ColumnDataSource data with the
        data in :attr:`cds_data`, effectively replacing all render data
        at once.
        """
        self.update_cds_data()
        if not self.cds:
            self.cds = bokeh.models.ColumnDataSource(self.cds_data)
            self.cds.selected.on_change("indices", self.on_cds_selection_changed)
        else:
            self.cds.data = self.cds_data
        return None
    
    def draw_petals(self):
        """Draws the petals.
        
        This method must be implemented in subclasses.
        """
        return None
    
    def on_cds_selection_changed(self, attr, old, new):
        """Called when the user selection of the petals changed."""
        columns = self.cds.data["column"]
        columns = [columns[i] for i in new]
        print("selected petals:", columns)
        return None
    
    def create_figure(self):
        """Creates the plot displaying the flower/wedge visualization."""
        # We center the glyph in the ``[-1, -1] x [-1, 1]`` square around
        # the origin.
        # Additional space is allocated for the labels outside the glyph.
        p = bokeh.plotting.figure(
            width=600, 
            height=600, 
            syncable=True,
            tools="reset,save,pan,wheel_zoom"
        )
        p.xaxis.visible = False
        p.yaxis.visible = False
        p.xgrid.visible = False
        p.ygrid.visible = False

        self.figure = p

        # Draw a bounding circle as additional visual hint.
        # For some reason ``circle()`` was not really circular when used
        # with bounded ranges.
        p.ellipse(
            x=0.0, 
            y=0.0,
            width=2.0, 
            height=2.0,
            fill_alpha=0.0,
            line_color="grey",
            line_dash="dotted",
            line_width=1.0
        )

        # The actual glyph drawing is implemented in subclasses, e.g.
        # wedges in FlowerWedge and parametric curves in FlowerCurve.
        self.draw_petals()

        # Draw the origin to hide the overlap region.
        p.ellipse(
            x=0.0, y=0.0, width=0.08, height=0.08, color="grey", line_color="grey"
        )

        # Draw the labels.
        labels = bokeh.models.LabelSet(
            x="label_xs",
            y="label_ys",
            text="column",
            angle="label_angle",
            text_align="label_align",
            text_baseline="middle",
            text_font_size="12px",
            source=self.cds
        )
        p.add_layout(labels)

        # The hover and tap tools should only work on the petals
        # but not on the visual aids. So we have to create them
        # manually.
        hover = bokeh.models.HoverTool(renderers=[self.petals])
        hover.tooltips = [
            ("column", "@column"),
            ("mean", "@mean")
        ]

        tap = bokeh.models.TapTool(renderers=[self.petals])
        
        p.add_tools(hover, tap)
        return None


class FlowerWedge(FlowerPlot):
    """The petals are simple wedges. This visualization is fast,
    easy to compute and visualize.
    """

    def __init__(self):
        """ """
        super().__init__()
        return None
    
    def draw_petals(self):
        """Draws a wedge for each petal."""
        p = self.figure

        # Draw the wedge. Usually, only the cds is updated as long as 
        # the columns of the data frame don't change.
        #
        # All the attributes are already available in the ColumnDataSource
        # so we don't have to compute anything new.
        self.petals = p.wedge(
            x=0.0, 
            y=0.0,
            radius="radius",
            start_angle="start_angle",
            end_angle="end_angle",
            fill_color="fill_color",
            line_color="grey",
            line_width=1.0,
            direction="anticlock",
            source=self.cds
        )
        return None
    

@functools.lru_cache(maxsize=10, typed=False)
def rose_curve_petal(npetals):
    """Creates a point list with the parametrization of a rose petal
    using the parametric version of the Rose curve.
    
    :seealso: https://en.wikipedia.org/wiki/Rose_(mathematics)
    """
    # More points result in a finer sampling.
    npoints = 48

    # Sample only one cycle of the rose curve. This also avoids 
    # complications with the oddness (even vs odd) of n.
    delta = np.pi/(2.0*npetals)
    phi = np.linspace(-delta, delta, npoints)

    x = np.cos(npetals*phi)*np.cos(phi)
    y = np.cos(npetals*phi)*np.sin(phi)
    return (x, y)


@functools.lru_cache(maxsize=10, typed=False)
def drop_curve_petal(npetals):
    """Creates a point list with the parametrization of a water-drop
    curve.

    :seealso: https://mathcurve.com/courbes2d.gb/larme/larme.shtml
    """
    # More points result in a finer sampling.
    npoints = 48

    # n Determines the shape of the drop. Smaller n gives a more
    # circular shape while larger n lets the drop wander to one side
    # of the draw area.
    n = 4

    # Sample the curve and flip it so that is is centered horizontally
    # and has x values betwen 0 and 1.
    t = np.linspace(0.0, 2.0*np.pi, npoints)
    x = np.cos(t)
    y = np.sin(t)*np.sin(t/2)**n
    x = -x/2.0 + 0.5

    # Normalize the curve such that the petals do not overlap, i.e.
    # they should not exceed the circle segment allocated for each
    # of them.
    #
    # We first compute the polar coordinates and normalize the maximal
    # angle `phi` such that it fits into the segment.
    rho = np.sqrt(x*x + y*y)
    phi = np.arctan2(y, x)

    phi_segment = 2.0*np.pi/npetals
    phi_max_curve = np.max(np.abs(phi))
    if phi_max_curve > phi_segment:
        phi = phi*(phi_segment)/phi_max_curve
    
    x = rho*np.cos(phi)
    y = rho*np.sin(phi)
    return (x, y)
    

class FlowerCurve(FlowerPlot):
    """Creates a flower visualization of the current selection."""

    def __init__(self):
        """ """
        super().__init__()

        #: The curve for a single peta.
        self.curve: Literal["rose", "drop"] = "rose"
        return None
    
    def update_cds_data(self):
        """Adds data for the petal polygons to the data dictionary."""
        # Recompute the basic information first.
        super().update_cds_data()

        # Recompute the petals.
        ncolumns = len(self.df.columns)
        if self.curve == "drop":
            x, y = drop_curve_petal(ncolumns)
        else:
            x, y = rose_curve_petal(ncolumns)

        # Rotate and scale each petal.
        xs = []
        ys = []
        for icolumn in range(ncolumns):

            # Rotate the petal.
            rotation = 2.0*np.pi*icolumn/ncolumns    
            xi = np.cos(rotation)*x - np.sin(rotation)*y
            yi = np.sin(rotation)*x + np.cos(rotation)*y

            # Scale it.
            radius = self.cds_data["radius"][icolumn]
            xi = xi*radius
            yi = yi*radius
            
            # We use the MultiPolygon renderer. So we need
            # to use these nested lists here.
            xs.append([[xi]])
            ys.append([[yi]])

        self.cds_data["xs"] = xs
        self.cds_data["ys"] = ys
        return None

    def draw_petals(self):
        """Creates the renderer for the petal polygons."""
        p = self.figure
        ncolumns = len(self.df.columns)

        self.petals = p.multi_polygons(
            xs="xs",
            ys="ys",
            color="color",
            line_color="grey",
            source=self.cds
        )
        return None