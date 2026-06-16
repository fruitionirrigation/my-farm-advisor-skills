#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false, reportGeneralTypeIssues=false
"""Generate a lightweight, self-contained interactive HTML web map for a grower.

Scans all farms under growers/<grower>/farms/, reads their field boundary
GeoJSON files, enriches features with metadata from each field's field.json,
and produces a single HTML file with embedded GeoJSON and Leaflet.js.

Usage:
    python generate_grower_web_map.py --grower-slug northern-il-grower
    python generate_grower_web_map.py --grower-slug northern-iowa-grower
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

_LOCAL_LIB = Path(__file__).resolve().parents[1] / "lib"
sys.path.insert(0, str(_LOCAL_LIB))

from runtime_paths import resolve_runtime_paths  # noqa: E402
from paths import grower_dir, farm_boundary_path  # noqa: E402

_RUNTIME_PATHS = resolve_runtime_paths()


def _load_field_metadata(grower_slug: str, farm_slug: str, field_slug: str) -> dict[str, Any]:
    """Load field.json metadata if it exists."""
    meta_path = grower_dir(grower_slug) / "farms" / farm_slug / "fields" / field_slug / "field.json"
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _collect_grower_fields(grower_slug: str) -> tuple[gpd.GeoDataFrame, list[dict[str, Any]]]:
    """Collect all field boundaries across all farms for a grower."""
    gdf_parts: list[gpd.GeoDataFrame] = []
    sidebar_records: list[dict[str, Any]] = []

    farms_dir = grower_dir(grower_slug) / "farms"
    if not farms_dir.exists():
        raise FileNotFoundError(f"No farms directory found for grower: {grower_slug}")

    for farm_path in sorted(farms_dir.iterdir()):
        if not farm_path.is_dir():
            continue
        farm_slug = farm_path.name
        boundary_file = farm_boundary_path(grower_slug, farm_slug)
        if not boundary_file.exists():
            continue

        gdf = gpd.read_file(boundary_file)
        if gdf.empty:
            continue

        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)

        for idx, row in gdf.iterrows():
            field_id = row.get("field_id", "")
            field_slug = str(field_id).replace("OSM_", "osm-") if field_id else ""
            meta = _load_field_metadata(grower_slug, farm_slug, field_slug)

            display_name = meta.get("display_name", field_slug) or field_slug
            farm_display = meta.get("farm_slug", farm_slug).replace("-", " ").title()
            grower_display = meta.get("grower_slug", grower_slug).replace("-", " ").title()

            gdf.at[idx, "grower_name"] = grower_display
            gdf.at[idx, "farm_name"] = farm_display
            gdf.at[idx, "field_name"] = display_name
            gdf.at[idx, "field_slug"] = field_slug
            gdf.at[idx, "farm_slug"] = farm_slug

            bounds = row.geometry.bounds
            center = ((bounds[1] + bounds[3]) / 2.0, (bounds[0] + bounds[2]) / 2.0)

            sidebar_records.append(
                {
                    "field_name": display_name,
                    "farm_name": farm_display,
                    "field_slug": field_slug,
                    "farm_slug": farm_slug,
                    "area_acres": float(row.get("area_acres", 0.0)),
                    "county_name": str(row.get("county_name", "")),
                    "state_fips": str(row.get("state_fips", "")),
                    "center": center,
                    "bounds": bounds,
                }
            )

        gdf_parts.append(gdf)

    if not gdf_parts:
        raise ValueError(f"No field boundaries found for grower: {grower_slug}")

    combined = gpd.GeoDataFrame(pd.concat(gdf_parts, ignore_index=True))
    if combined.crs is None:
        combined.set_crs(epsg=4326, inplace=True)

    return combined, sidebar_records


def _compute_map_view(gdf: gpd.GeoDataFrame) -> tuple[float, float, int]:
    """Compute center lat/lon and zoom from a GeoDataFrame."""
    bounds = gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2.0
    center_lon = (bounds[0] + bounds[2]) / 2.0

    lat_span = abs(bounds[3] - bounds[1])
    if lat_span < 0.01:
        zoom = 15
    elif lat_span < 0.05:
        zoom = 13
    elif lat_span < 0.2:
        zoom = 11
    elif lat_span < 0.5:
        zoom = 10
    elif lat_span < 1.0:
        zoom = 9
    elif lat_span < 2.0:
        zoom = 8
    elif lat_span < 5.0:
        zoom = 7
    else:
        zoom = 6

    return center_lat, center_lon, zoom


def _build_html(gdf: gpd.GeoDataFrame, sidebar_records: list[dict[str, Any]], grower_slug: str) -> str:
    """Build a self-contained HTML string with embedded GeoJSON and Leaflet."""
    geojson_data = json.loads(gdf.to_json())
    geojson_str = json.dumps(geojson_data, separators=(",", ":"))

    center_lat, center_lon, zoom = _compute_map_view(gdf)

    sidebar_items = []
    for rec in sidebar_records:
        lat, lon = rec["center"]
        label = f"{rec['field_name']} ({rec['farm_name']})"
        sidebar_items.append(
            f"""<div class="field-item" onclick="zoomToField({lat:.6f}, {lon:.6f}, '{rec['field_slug']}', '{rec['farm_slug']}')">{label}</div>"""
        )
    sidebar_html = "\n".join(sidebar_items)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Grower Map – {grower_slug.replace("-", " ").title()}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body, html {{ height:100%; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
  #container {{ display:flex; height:100%; }}
  #sidebar {{
    width: 320px;
    background: #ffffff;
    border-right: 1px solid #ddd;
    padding: 16px;
    overflow-y: auto;
    flex-shrink: 0;
  }}
  #sidebar h2 {{
    font-size: 1.1em;
    margin-bottom: 10px;
    color: #1B5E20;
  }}
  #sidebar p {{
    font-size: 0.85em;
    color: #555;
    margin-bottom: 12px;
  }}
  .field-item {{
    padding: 8px 10px;
    border-radius: 6px;
    margin-bottom: 6px;
    cursor: pointer;
    background: #f4f6f8;
    font-size: 0.9em;
    transition: background 0.15s;
  }}
  .field-item:hover {{ background: #e8f5e9; }}
  #map {{ flex:1; height:100%; }}
  .legend {{
    background: white;
    padding: 8px 12px;
    border-radius: 5px;
    box-shadow: 0 0 10px rgba(0,0,0,0.15);
    font-size: 0.85em;
    line-height: 1.4;
  }}
</style>
</head>
<body>
<div id="container">
  <div id="sidebar">
    <h2>Field List</h2>
    <p>Click a field to zoom to it.</p>
    <div id="field-list">
      {sidebar_html}
    </div>
  </div>
  <div id="map"></div>
</div>
<script>
  var map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], {zoom});

  // Basemap layers
  var satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}', {{
    attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
    maxZoom: 19
  }});

  var streets = L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }});

  satellite.addTo(map);

  L.control.layers({{
    "Satellite": satellite,
    "Street Map": streets
  }}, null, {{ collapsed: false }}).addTo(map);

  var geojsonData = {geojson_str};
  var layerMap = {{}};

  var fieldsLayer = L.geoJSON(geojsonData, {{
    renderer: L.canvas(),
    style: function(feature) {{
      return {{
        color: '#FFFFFF',
        weight: 2.5,
        fillColor: '#FFFFFF',
        fillOpacity: 0.10
      }};
    }},
    onEachFeature: function(feature, layer) {{
      var props = feature.properties;
      var popup = '<div style="font-size:0.95em;line-height:1.5;">' +
        '<b>Grower:</b> ' + (props.grower_name || 'N/A') + '<br>' +
        '<b>Farm:</b> ' + (props.farm_name || 'N/A') + '<br>' +
        '<b>Field:</b> ' + (props.field_name || 'N/A') + '<br>' +
        '<b>Field ID:</b> ' + (props.field_id || 'N/A') + '<br>' +
        '<b>Area:</b> ' + (props.area_acres ? props.area_acres.toFixed(2) : 'N/A') + ' acres<br>' +
        '<b>County:</b> ' + (props.county_name || 'N/A') + '<br>' +
        '<b>State FIPS:</b> ' + (props.state_fips || 'N/A') +
        '</div>';
      layer.bindPopup(popup);

      layer.on('mouseover', function(e) {{
        e.target.setStyle({{ color: '#FF8C00', weight: 4, fillColor: '#FF8C00', fillOpacity: 0.35 }});
      }});
      layer.on('mouseout', function(e) {{
        e.target.setStyle({{ color: '#FFFFFF', weight: 2.5, fillColor: '#FFFFFF', fillOpacity: 0.10 }});
      }});

      if (props.field_slug && props.farm_slug) {{
        var key = props.farm_slug + '::' + props.field_slug;
        layerMap[key] = layer;
      }}
    }}
  }}).addTo(map);

  map.fitBounds(fieldsLayer.getBounds(), {{ padding: [20, 20] }});

  function zoomToField(lat, lon, fieldSlug, farmSlug) {{
    var key = farmSlug + '::' + fieldSlug;
    var layer = layerMap[key];
    if (layer) {{
      map.fitBounds(layer.getBounds(), {{ padding: [60, 60] }});
      layer.openPopup();
    }} else {{
      map.setView([lat, lon], 15);
    }}
  }}

  var legend = L.control({{position: 'bottomright'}});
  legend.onAdd = function(map) {{
    var div = L.DomUtil.create('div', 'legend');
    div.innerHTML = '<b>Legend</b><br><span style="display:inline-block;width:12px;height:12px;background:#FFFFFF;border:1px solid #FF8C00;margin-right:6px;"></span>Field Boundary<br><span style="font-size:0.8em;color:#666;">Switch basemap via top-right control</span>';
    return div;
  }};
  legend.addTo(map);
</script>
</body>
</html>
"""
    return html


def generate_grower_web_map(grower_slug: str, output_dir: Path | None = None) -> Path:
    """Main entrypoint: generate the HTML map and return the output path."""
    gdf, sidebar_records = _collect_grower_fields(grower_slug)
    html = _build_html(gdf, sidebar_records, grower_slug)

    if output_dir is None:
        output_dir = grower_dir(grower_slug) / "maps"
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / "grower_web_map.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a lightweight interactive web map for a grower.")
    parser.add_argument("--grower-slug", required=True, help="Grower slug (e.g., northern-il-grower)")
    parser.add_argument("--output-dir", default=None, help="Optional output directory override")
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else None
    out_path = generate_grower_web_map(args.grower_slug, out_dir)
    size_kb = out_path.stat().st_size / 1024.0
    print(f"Generated grower web map: {out_path}")
    print(f"File size: {size_kb:.1f} KB")


if __name__ == "__main__":
    main()
