/**
 * This module implements a custom Bokeh tool for selecting special subgraphs,
 * e.g. all ancestors or all descendants. 
 * 
 * The documentation of BokehJS was kinda non-exsistent when I tried to 
 * implement this tool. It is based on the source code of the *TapTool*,
 * the *SelectionManager* and the documentation for a custom drawing tool.
 * 
 * The most important insight is that Bokeh keeps a list of *inspected*
 * and *selected* indices. Both can be changed by user interaction and are similarly
 * implemented, but only the *selected* index list is shown as actually selected,
 * while the *inspected* list is used to implement tooltips e.g. when hovering
 * a glyph.
 */
import {SelectTool, SelectToolView} from "models/tools/gestures/select_tool"
import {ColumnDataSource} from "models/sources/column_data_source"
import {TapEvent} from "core/ui_events"
import * as p from "core/properties"
import type {PointGeometry} from "core/geometry"


export class AncestorToolView extends SelectToolView {
  declare model: AncestorTool

  /**
   * React to tap (mouse click) events.
   */
  _tap(ev: TapEvent): void {
    const {sx, sy} = ev
    const {frame} = this.plot_view
    if (!frame.bbox.contains(sx, sy))
      return

    this._clear_other_overlays()
    const geometry: PointGeometry = {type: "point", sx, sy}
    this._select(geometry)
  }

  _select(geometry: PointGeometry)
  {
    const source_vertices = this.model.source_vertices;

    for (const r of this.computed_renderers) {
      const rv = this.plot_view.renderer_view(r)
      if (rv == null)
        continue

      const sm = r.get_selection_manager()
      if(!Object.is(sm.source, source_vertices))
      {
        continue;
      }

      const did_hit = sm.inspect(rv, geometry)
      if (did_hit) {
        let roots = Array<number>();
        for(let ind of sm.source.inspected.indices) {
          roots.push(ind);
        }        
        this._select_ancestors(roots);
      }
    }
  }

  _select_ancestors(roots: Array<number>)
  {
    console.log("Do subgraph selection.");

    const cds_edges = this.model.source_edges;
    const cds_vertices = this.model.source_vertices;

    const nedges = cds_edges.length;
    const nvertices = cds_vertices.length;

    const colname_source = "input:source";
    const colname_target = "input:target";

    const col_source = cds_edges.data[colname_source];
    const col_target = cds_edges.data[colname_target];
    
    // Build a linked list for faster lookups.
    let graph = Array.from({length: nvertices}, () => {
      return Array<number>();
    });
    for(let iedge = 0; iedge < nedges; ++iedge)
    {
        let isource = col_source[iedge];
        let itarget = col_target[iedge];
        graph[isource].push(itarget);
    }

    // Find all ancestors.
    let queue = Array.from(roots);
    let seen = Array<number>();

    while(queue.length > 0)
    {
        const isource = queue.shift()!;
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
  }
}


export namespace AncestorTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = SelectTool.Props & {
    source_vertices: p.Property<ColumnDataSource>
    source_edges: p.Property<ColumnDataSource>
    mode: p.Property<
  }
}


export interface AncestorTool extends AncestorTool.Attrs {}


export class AncestorTool extends SelectTool {
  declare properties: AncestorTool.Props
  declare __view_type__: AncestorToolView

  constructor(attrs?: Partial<AncestorTool.Attrs>) {
    super(attrs)
  }

  tool_name = "Ancestor Tool"
  tool_icon = "bk-tool-icon-caret-down"
  event_type = "tap" as "tap"
  default_order = 12

  static {
    this.prototype.default_view = AncestorToolView

    this.define<AncestorTool.Props>(({Ref}) => ({
      source_vertices: [Ref(ColumnDataSource)],
      source_edges: [Ref(ColumnDataSource)],
    }))
  }
}