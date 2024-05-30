"""
:mod:`coda.flower`

This module implements flower glyphs. Not really glyphs, but a single plot
which shows a flower glyph. The flower petals are either wedges (fast
and simple) or parametrized by a curve like the rose curve or tear-drop
curve, which both are more beautiful.
"""

import functools
import itertools
from typing import Dict, List, Any, Literal, Tuple

import bokeh
import bokeh.plotting
import bokeh.models
import bokeh.palettes

import pandas as pd
import numpy as np

from coda.application import Application
from coda.view.base import ViewBase
import coda.utils


__all__ = [
    "FlowerPlot",
    "FlowerWedge",
    "FlowerCurve",
    "FlowerRose",
    "FlowerDrop",
    "FlowerView"
]


class FlowerPlot(object):
    """Base class for all Flower plots. This class aggregates the data columns
    and computes information used in the flower plots.     

    This class draw the flower on an existing figure.

    :param source:
        The column data source with the non-aggregated data.
    :param field:
        The fields in the :attr:`source` for which a petal is drawn.
    :param figure:
        The Bokeh figure the flower is drawn onto.
    :param center:
        The center of the flower. The default is the origin ``(0.0, 0.0)``.
    :param radius:
        The maximal radius of the flower. The default is ``1``.
    """

    def __init__(
            self,
            *,
            source: bokeh.models.ColumnDataSource,
            fields: List[str],
            figure: bokeh.models.Model,
            center: Tuple[float, float] = (0.0, 0.0),
            radius: float = 1.0
        ):
        """ """
        super().__init__()

        #: The dataframe containing all samples. The data here is used to determine
        #: the overall scale of the petals.
        self.source = source
        self.source.selected.on_change("indices", self.on_source_selected_change)

        #: The fields for which a petal is drawn.
        self.fields = fields

        #: The figure onto which the petal is drawn.
        self.figure = figure

        #: The flower is centered at this point.
        self.center = center

        #: The maximal radius of the flower, i.e. distance from the :attr:`center`.
        self.radius = radius


        #: A description (mean, variance, skew, ...) of the whole dataset.
        self.desc: pd.DataFrame = None

        #: A description (mean, variance, skew, ...) of the selection.
        self.desc_selection: pd.DataFrame = None


        #: The data dictionary for the :attr:`flower_source` column data source.
        #: Changes are written to this dictionary first and then pushed at once
        #: to the actual column data source.
        self.data_flower: Dict[str, Any] = dict()

        #: The actual column data source the flower plot is based on.
        self.source_flower = bokeh.models.ColumnDataSource()

        #: The renderer for the petals. Must be set by subclasses. 
        #: The hover and tap tool will work on this renderer.
        self.petals: bokeh.models.Model = None

        self.init_data_flower()
        self.update()
        self.draw()
        return None
       

    def init_data_flower(self):
        """Initialises the :attr:`data_flower` dictionary so that
        empty draw calls will not result in a Bokeh warning. 
        This happens if the no field is given in :attr:`fields`.

        This method must be extended in subclasses if they add custom
        render data to the column data source.
        """
        self.data_flower.update({
            "start_angle": [],
            "end_angle": [],
            "radius": [],
            "fill_color": [],
            "column": [],
            "mean": [],
            "color": [],
            "label_xs": [],
            "label_ys": [],
            "label_angle": [],
            "label_align": []
        })
        return None
    
    
    def draw_petals(self):
        """Draws the petals.
        
        This method must be implemented in subclasses and is called
        only once when the flower is drawn for the first time. All
        other updates must happen inside the column data sources.
        """
        return None
    
    def draw(self):
        """Draws the flower onto the figure."""
        p = self.figure
        x0, y0 = self.center
        radius = self.radius

        # Draw a bounding circle as additional visual hint.
        # For some reason ``circle()`` was not really circular when used
        # with bounded ranges.
        p.ellipse(
            x=x0, 
            y=y0,
            width=2.0*radius, 
            height=2.0*radius,
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
            x=x0, 
            y=y0, 
            width=0.08*radius, 
            height=0.08*radius, 
            color="grey", 
            line_color="grey"
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
            source=self.source_flower
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
    

    def update_description(self):
        """Aggreagates the data for the currently selected fields 
        and selection in :attr:`desc` and :attr:`desc_selection`.
        """
        columns = [np.array(self.source.data[field]) for field in self.fields]

        self.desc = {
            "max": np.array([np.max(column) for column in columns]),
            "min": np.array([np.min(column) for column in columns]),
            "quantile05": np.array([np.quantile(column, 0.05) for column in columns]),
            "quantile95": np.array([np.quantile(column, 0.95) for column in columns])
        }
        return None
    
    def update_description_selection(self):
        """Updates the description of the current selection."""        
        columns = [np.array(self.source.data[field]) for field in self.fields]

        selection = self.source.selected.indices
        if selection:
            columns = [column[selection] for column in columns]

        self.desc_selection = {
            "max": np.array([np.max(column) for column in columns]),
            "min": np.array([np.min(column) for column in columns]),
            "mean": np.array([np.mean(column) for column in columns]),
            "median": np.array([np.median(column) for column in columns])
        }
        return None
    

    def update_flower_data(self):
        """Recomputes the data :attr:`flower_data` dictionary."""
        ncolumns = len(self.fields)

        # Extract the attributes relevant for the pedal/wedge size
        # and shape.
        mean_selection = self.desc_selection["mean"]
        min_total = self.desc["min"]
        max_total = self.desc["max"]

        # Divide the circle into segments of the same size.
        # Each column has its own segment. The petals are scaled
        # within 
        delta = 2.0*np.pi/ncolumns if ncolumns else 2.0*np.pi
        angles = np.linspace(0.0, 2.0*np.pi, ncolumns, endpoint=False)
        radius = ((mean_selection - min_total)/(max_total - min_total))*self.radius
        start_angle = angles - delta/2.0
        end_angle = angles + delta/2.0

        palette = bokeh.palettes.Spectral10
        color = [color for _, color in zip(range(ncolumns), itertools.cycle(palette))]

        # Update the column data source.
        self.data_flower.update({
            "start_angle": start_angle,
            "end_angle": end_angle,
            "radius": radius,
            "fill_color": color,
            "column": self.fields,
            "mean": mean_selection,
            "color": color
        })

        # Also update the label positions.
        self.update_flower_label_data()
        return None    

    def update_flower_label_data(self):
        """Updates the column data for the peta labels in :attr:`source_flower`.
        The labels are drawn outside each petal and are oriented to the center 
        of the flower.
        """
        ncolumns = len(self.fields)
        radii = self.data_flower["radius"]

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
    
        self.data_flower.update({
            "label_xs": xs,
            "label_ys": ys,
            "label_angle": angles,
            "label_align": alignments
        })
        return None
    
    def push_flower_data_to_source(self):
        """Replaces the current Bokeh ColumnDataSource data with the
        data in :attr:`cds_data`, effectively replacing all render data
        at once.
        """
        self.source_flower.data = self.data_flower
        return None
    
    def update(self):
        """Updates the entire flower plot."""
        self.update_description()
        self.update_description_selection()
        self.update_flower_data()
        self.push_flower_data_to_source()
        return None
    
    def on_source_selected_change(self, attr, old, new):
        """The current selection changed."""
        self.update_description_selection()
        self.update_flower_data()
        self.push_flower_data_to_source()
        return None
    

class FlowerWedge(FlowerPlot):
    """The petals are simple wedges. This visualization is fast,
    easy to compute and looks sciency (i.e. boring).
    """

    def __init__(self, *args, **kargs):
        """ """
        super().__init__(*args, **kargs)
        return None
    
    def draw_petals(self):
        """Draws a wedge for each petal."""
        p = self.figure
        x0, y0 = self.center

        # Draw the wedge. Usually, only the cds is updated as long as 
        # the columns of the data frame don't change.
        #
        # All the attributes are already available in the ColumnDataSource
        # so we don't have to compute anything new.
        self.petals = p.wedge(
            x=x0, 
            y=y0,
            radius="radius",
            start_angle="start_angle",
            end_angle="end_angle",
            fill_color="fill_color",
            line_color="grey",
            line_width=1.0,
            direction="anticlock",
            source=self.source_flower
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
    """Creates a flower visualization of the current selection. The petals
    curves are parametrized and given as a a point set / polygon.
    """

    def __init__(
            self, *,
            curve: Literal["rose", "drop"] = "rose",
            **kargs
        ):
        """ """
        #: The curve for a single peta.
        self.curve = curve

        # The base class will call the :meth:`draw` and :meth:`update`
        # method. So we have to initialize it after setting the curve
        # attribute.
        super().__init__(**kargs)
        return None

    def init_data_flower(self):
        super().init_data_flower()
        self.data_flower.update({
            "xs": [],
            "ys": []
        })
        return None
    
    def draw_petals(self):
        """Creates the glyph renderer for the petal polygons."""
        self.petals = self.figure.multi_polygons(
            xs="xs",
            ys="ys",
            color="color",
            line_color="grey",
            source=self.source_flower
        )
        return None
    
    def update_flower_data(self):
        """Adds additional render data for the petal polygons to the flower
        data dictionary.
        """
        # Recompute the basic information first.
        super().update_flower_data()

        # Recompute the petals.
        ncolumns = len(self.fields)
        if ncolumns == 0:
            x, y = [], []
        elif self.curve == "drop":
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
            radius = self.data_flower["radius"][icolumn]
            xi = xi*radius
            yi = yi*radius
            
            # We use the MultiPolygon renderer. So we need
            # to use these nested lists here.
            xs.append([[xi]])
            ys.append([[yi]])

        self.data_flower["xs"] = xs
        self.data_flower["ys"] = ys
        return None
    

class FlowerRose(FlowerCurve):
    """Dedicated subclass for flower plots with rose petals."""

    def __init__(self, **kargs):
        super().__init__(**kargs, curve="rose")
        return None
    

class FlowerDrop(FlowerCurve):
    """Dedicated subclass for flower plots with drop-shaped petals."""

    def __init__(self, **kargs):
        super().__init__(**kargs, curve="drop")
        return None
    

class FlowerView(ViewBase):
    """Shows a single flower plot in a view panel."""

    def __init__(self, app: Application):
        super().__init__(app)

        #: UI for switching between the different flower types.
        self.ui_select_flower = bokeh.models.Select(
            title="Flower",
            options=["wedge", "rose", "drop"],
            value="rose",
            sizing_mode="stretch_width"
        )
        self.ui_select_flower.on_change(
            "value", self.on_ui_select_flower_change
        )

        #: UI for selecting the columns to display in the flower.
        self.ui_multichoice_columns = bokeh.models.MultiChoice(
            title="Columns",
            sizing_mode="stretch_width"
        )
        self.ui_multichoice_columns.on_change(
            "value", self.on_ui_multichoice_columns_change
        )

        #: The figure showing the flower plot.
        self.figure: bokeh.models.Model = None
        
        #: The actual flower plot drawn onto the figure :attr:`figure`.
        self.flower: FlowerPlot = None

        # Sidebar layout.
        self.layout_sidebar.children = [
            self.ui_select_flower,
            self.ui_multichoice_columns
        ]
        return None
    

    def reload_df(self):
        """Update the UI to match the available columns in the dataset."""
        columns = coda.utils.scalar_columns(self.app.df)

        selection = self.ui_multichoice_columns.value
        selection = [column for column in selection if column in columns]

        self.ui_multichoice_columns.options = columns
        self.ui_multichoice_columns.value = selection
        return None

    def reload_cds(self):
        """Update the flower plot."""
        # Just replace the old figure with a new one.
        self.create_figure()
        return None
    

    def on_ui_select_flower_change(self, attr, old, new):
        """The user changed the flower type."""
        self.create_figure()
        return None
    
    def on_ui_multichoice_columns_change(self, attr, old, new):
        """The user changed the petal columns."""
        if self.is_reloading:
            return None
                
        self.flower.fields = new
        self.flower.update()
        return None
    

    def create_figure(self):
        """Create the Bokeh figure showing the flower plot and replace
        the current figure.
        """
        # Create the figure.
        figure = bokeh.plotting.figure(
            tools="reset,save,pan,wheel_zoom",
            match_aspect=True,
            sizing_mode="scale_both",
            toolbar_location="above",
            title="Flower"
        )
        figure.xaxis.visible = False
        figure.yaxis.visible = False
        figure.xgrid.visible = False
        figure.ygrid.visible = False

        # Create the flower.
        flower_classes = {
            "wedge": FlowerWedge,
            "rose": FlowerRose,
            "drop": FlowerDrop
        }
        flower_class = flower_classes[self.ui_select_flower.value]

        flower = flower_class(
            source=self.app.cds,
            fields=self.ui_multichoice_columns.value,
            figure=figure,
            center=(0.0, 0.0),
            radius=1.0
        )

        # Done.
        self.flower = flower
        self.figure = figure
        self.layout_panel.children = [figure]
        return None