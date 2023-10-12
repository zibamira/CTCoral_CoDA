"""
:mod:`cora.tools.ancestor_tool`

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

from cora.application import Application


__all__ = [
    "AncestorTool"
]


this_dir = pathlib.Path(__file__).parent


class AncestorTool(bokeh.models.Tool):
    """Select all ancestors when clicked on a vertex glyph."""

    def __init__(self, *args, **kargs) -> None:
        super().__init__(*args, **kargs)
        return None

    CODE = (this_dir / "ancestor_tool.ts").read_text()
    __implementation__ = bokeh.util.compiler.TypeScript(CODE)

    source_edges = bokeh.core.properties.Instance(bokeh.models.ColumnDataSource)
    source_vertices = bokeh.core.properties.Instance(bokeh.models.ColumnDataSource)


def OldAncestorTool(
        colname_source,
        colname_target,
        cds_vertices, 
        cds_edges, 
        *args, **kargs
    ):
    """A special tap tool that selects ancestors."""
    tool = bokeh.models.TapTool(*args, **kargs)

    tool.callback = bokeh.models.CustomJS(
        args={
            "cds_vertices": cds_vertices, 
            "cds_edges": cds_edges,
            "colname_source": colname_source,
            "colname_target": colname_target
        },
        code="""
            // Get the current tap selection.
            const tap_selection = cb_data.source.selected.indices;
            if(tap_selection.length == 0)
            {
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
            for(let iedge = 0; iedge < nedges; ++iedge)
            {
                let isource = col_source[iedge];
                let itarget = col_target[iedge];
                graph[isource].push(itarget);
            }

            // Find all ancestors.
            let istart = tap_selection[0];
            let queue = [istart];
            let seen = [];

            while(queue.length > 0)
            {
                const isource = queue.shift();
                if(seen.includes(isource))
                {
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

            seen.sort();
            console.log(seen);

            // Markt the descendants as selected.
            cds_vertices.selected.indices = seen;
/*

            console.log(col_source);
            console.log(col_target);
            console.log(nvertices);
            console.log(graph);
            */
    """)
    return tool

