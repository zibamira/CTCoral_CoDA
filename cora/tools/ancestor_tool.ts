import {SelectTool, SelectToolView} from "models/tools/gestures/select_tool"
import {ColumnDataSource} from "models/sources/column_data_source"
import {TapEvent} from "core/ui_events"
import * as p from "core/properties"
import type {PointGeometry} from "core/geometry"
import type {DataRendererView} from "models/renderers/data_renderer"


export class AncestorToolView extends SelectToolView {
  declare model: AncestorTool

  counter = 0;


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
        console.log("SELECTED INDICES");
        console.log(sm.source.inspected.indices);
        // this._emit_callback(rv, geometry, sm.source, modifiers)
      }
    }
  }

  _do_subgraph_selection(
    rv: DataRendererView, 
    geometry:PointGeometry,
    source: ColumnDataSource
  ) : void 
  {
    const x = rv.coordinates.x_scale.invert(geometry.sx)
    const y = rv.coordinates.y_scale.invert(geometry.sy)
    const data = {
      geometries: {...geometry, x, y},
      source,
    }
    console.log(data);
  }
}


export namespace AncestorTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = SelectTool.Props & {
    source_vertices: p.Property<ColumnDataSource>
    source_edges: p.Property<ColumnDataSource>
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