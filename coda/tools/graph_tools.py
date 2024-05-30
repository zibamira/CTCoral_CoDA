"""
:mod:`coda.tools.graph_tools`

This module implements special selection tools for graphs that haven't been
implemented in Bokeh yet. 

There's a tool that selects all ancestors of a vertex and a tool that selects
all descendents of a vertex.
"""

import pathlib
from typing import List

import bokeh
import bokeh.layouts
import bokeh.models
import bokeh.plotting
import bokeh.util.compiler

import pandas as pd
import numpy as np
import networkx as nx

from coda.application import Application


__all__ = [
    "make_ancestor_tool",
    "make_descendant_tool",
    "make_component_tool",
    "AncestorToolTS"
]


this_dir = pathlib.Path(__file__).parent


def make_ancestor_tool(
        colname_source: str,
        colname_target: str,
        cds_vertices: bokeh.models.ColumnDataSource, 
        cds_edges: bokeh.models.ColumnDataSource,
        *args, **kargs
    ):
    """A special tap tool that selects ancestors.
    
    TODO: Allow to synchonize the *colname_source* and *colname_target* after creation.
    """
    tool = bokeh.models.TapTool(*args, **kargs, behavior="inspect")
    tool.name = "ancestor-tool"
    tool.icon = this_dir / "caret-down-solid.png"
    tool.callback = bokeh.models.CustomJS(
        args={
            "cds_vertices": cds_vertices, 
            "cds_edges": cds_edges,
            "colname_source": colname_source,
            "colname_target": colname_target
        },
        code="""
            // Get the current tap selection.
            const tap_selection = cb_data.source.inspected.indices;
            if(tap_selection.length == 0) {
                return;
            }
                        
            const col_source = cds_edges.data[colname_source];
            const col_target = cds_edges.data[colname_target];
            const nedges = cds_edges.length;
            const nvertices = cds_vertices.length;

            // Build a linked list for faster lookups.
            let graph = Array.from({length: nvertices}, () => {
                return [];
            });
            for(let iedge = 0; iedge < nedges; ++iedge) {
                let isource = col_source[iedge];
                let itarget = col_target[iedge];
                graph[isource].push(itarget);
            }

            // Find all ancestors.
            let queue = tap_selection;
            let seen = [];
            while(queue.length > 0) {
                const isource = queue.shift();
                if(seen.includes(isource))
                {
                    continue;
                }
                seen.push(isource);
                
                graph[isource].forEach((itarget, _) => {
                    if(!queue.includes(itarget)) {
                        queue.push(itarget);
                    }
                });
            }

            // Mark the ancestors as selected.
            seen.sort();
            cds_vertices.selected.indices = seen;
    """)
    return tool


def make_descendant_tool(
        colname_source: str,
        colname_target: str,
        cds_vertices: bokeh.models.ColumnDataSource, 
        cds_edges: bokeh.models.ColumnDataSource,
        *args, **kargs
    ):
    """A special tap tool that selects descendants.
    
    TODO: Allow to synchonize the *colname_source* and *colname_target* after creation.
    """
    tool = bokeh.models.TapTool(*args, **kargs, behavior="inspect")
    tool.name = "descendant-tool"
    tool.icon = this_dir / "caret-up-solid.png"
    tool.callback = bokeh.models.CustomJS(
        args={
            "cds_vertices": cds_vertices, 
            "cds_edges": cds_edges,
            "colname_source": colname_source,
            "colname_target": colname_target
        },
        code="""
            // Get the current tap selection.
            const tap_selection = cb_data.source.inspected.indices;
            if(tap_selection.length == 0) {
                return;
            }
            
            const col_source = cds_edges.data[colname_source];
            const col_target = cds_edges.data[colname_target];
            const nedges = cds_edges.length;
            const nvertices = cds_vertices.length;

            // Build a linked list for faster lookups.
            let graph = Array.from({length: nvertices}, () => {
                return [];
            });
            for(let iedge = 0; iedge < nedges; ++iedge) {
                let isource = col_source[iedge];
                let itarget = col_target[iedge];

                // NOTE: We flip all edges at this point.
                graph[itarget].push(isource);
            }

            // Find all ancestors.
            let queue = tap_selection;
            let seen = [];
            while(queue.length > 0) {
                const isource = queue.shift();
                if(seen.includes(isource)) {
                    continue;
                }
                seen.push(isource);                
                graph[isource].forEach((itarget, _) => {
                    if(!queue.includes(itarget))
                    {
                        queue.push(itarget);
                    }
                });
            }

            // Mark the descendants as selected.
            seen.sort();
            cds_vertices.selected.indices = seen;
    """)
    return tool


def make_component_tool(
        colname_source: str,
        colname_target: str,
        cds_vertices: bokeh.models.ColumnDataSource, 
        cds_edges: bokeh.models.ColumnDataSource,
        *args, **kargs
    ):
    """A special tap tool that selects the whole, weakly connected component
    of the tapped vertices.
    
    TODO: Allow to synchonize the *colname_source* and *colname_target* after creation.
    """
    tool = bokeh.models.TapTool(*args, **kargs, behavior="inspect")
    tool.name = "component-tool"
    tool.icon = this_dir / "asterisk-solid.png"
    tool.callback = bokeh.models.CustomJS(
        args={
            "cds_vertices": cds_vertices, 
            "cds_edges": cds_edges,
            "colname_source": colname_source,
            "colname_target": colname_target
        },
        code="""
            // Get the current tap selection.
            const tap_selection = cb_data.source.inspected.indices;
            if(tap_selection.length == 0) {
                return;
            }
            
            const col_source = cds_edges.data[colname_source];
            const col_target = cds_edges.data[colname_target];
            const nedges = cds_edges.length;
            const nvertices = cds_vertices.length;

            // Build a linked list for faster lookups.
            let graph = Array.from({length: nvertices}, () => {
                return [];
            });
            for(let iedge = 0; iedge < nedges; ++iedge) {
                let isource = col_source[iedge];
                let itarget = col_target[iedge];

                // Create two edges, one from the source, one from the target.
                // I.e. we consider the graph to be undirected.
                graph[itarget].push(isource);
                graph[isource].push(itarget);
            }

            // Find all vertices in the connected component.
            let queue = tap_selection;
            let seen = [];
            while(queue.length > 0) {
                const isource = queue.shift();
                if(seen.includes(isource)) {
                    continue;
                }
                seen.push(isource);       
                graph[isource].forEach((itarget, _) => {
                    if(!queue.includes(itarget))
                    {
                        queue.push(itarget);
                    }
                });
            }

            // Mark the descendants as selected.
            seen.sort();
            cds_vertices.selected.indices = seen;
    """)
    return tool


class AncestorToolTS(bokeh.models.Tool):
    """Tapping on a vertex selects the vertex and all its ancestors.
    
    This tool does the same as :class:`AncestorToolPy` but is implemented in TypeScript
    as all BokehJS tools.

    .. todo::

        After implementing the ancestor tool in TypeScript, I realized that it can
        be easier implemented in Python using Bokeh's TapTool callback. Since I spend
        a lot of time doing so, I did not want to throw it away right away.

        Here's the todo: Remove this module and the TypeScript eventually.
    """

    def __init__(self, *args, **kargs) -> None:
        super().__init__(*args, **kargs)
        return None

    CODE = (this_dir / "ancestor_tool.ts").read_text()
    __implementation__ = bokeh.util.compiler.TypeScript(CODE)

    source_edges = bokeh.core.properties.Instance(bokeh.models.ColumnDataSource)
    source_vertices = bokeh.core.properties.Instance(bokeh.models.ColumnDataSource)
    selection_mode = bokeh.core.properties.Enum("ancestors", "descendants", default="ancestors")
