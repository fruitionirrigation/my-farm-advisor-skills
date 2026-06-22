# DEM Terrain Contract

This package defines the foundational runtime contract for field-level DEM terrain products in My Farm Advisor. It intentionally contains only deterministic constants, dataclasses, product names, output schema fields, and manifest schema fields; it does not download DEM tiles, process rasters, create runtime directories, or write generated assets.

## Runtime path contract

Generated and downloaded DEM assets are runtime-only and must stay out of Git. Downstream tasks should write under the external data-pipeline root, never inside this checkout:

| Purpose | Template |
| --- | --- |
| Field DEM root | `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/<grower>/farms/<farm>/fields/<field_slug>/terrain/dem/` |
| Derived rasters | `fields/<field_slug>/derived/terrain/` |
| CSV summary | `fields/<field_slug>/derived/tables/dem_terrain_summary.csv` |
| JSON summary | `fields/<field_slug>/derived/tables/dem_terrain_summary.json` |
| Manifest | `fields/<field_slug>/manifests/dem_terrain_manifest.json` |
| Source cache | `${DATA_PIPELINE_DATA_ROOT}/data-pipeline/shared/dem/<adapter>/` |

The contract module exposes these as string templates only. Importing `dem_terrain` is safe in a clean checkout and does not require `DATA_PIPELINE_DATA_ROOT` to exist.

## Product filenames

The required runtime products are:

- `dem_source_reference.json`
- `dem_clipped.tif`
- `dem_conditioned.tif`
- `slope_degrees.tif`
- `slope_percent.tif`
- `aspect_degrees.tif`
- `hillshade.tif`
- `profile_curvature.tif`
- `planform_curvature.tif`
- `tpi.tif`
- `tri.tif`
- `flow_direction.tif`
- `flow_accumulation.tif`
- `topographic_wetness_index.tif`
- `depression_depth.tif`
- `relative_elevation.tif`
- `erosion_proxy.tif`

Summary outputs are `dem_terrain_summary.csv` and `dem_terrain_summary.json`. The manifest filename is `dem_terrain_manifest.json`.

## Manifest schema

The manifest must include these top-level fields exactly:

`run_id`, `field_id`, `field_slug`, `buffer_meters`, `analysis_crs`, `selected_source`, `candidate_sources`, `fallback_reason`, `surface_type`, `source_resolution_m`, `source_horizontal_crs`, `source_vertical_datum`, `source_urls`, `license`, `citation`, `acquisition_date`, `publication_date`, `processing_parameters`, `warnings`, `outputs`, `checksums`, `generated_at`.

The `outputs` records should be STAC-like where useful. Each asset should include an `href`, media `type`, `roles`, projection metadata such as `proj:epsg` or `proj:wkt2`, raster metadata such as nodata, data type, unit, and resolution, file size and checksum, and source/provenance links. DSM or mixed-surface fallbacks must set warning fields so farm-terrain analysis is not misrepresented as bare-earth DTM when vegetation or structures may affect elevations.

## Git and asset boundary

Do not commit generated DEM `.tif`, preview `.png`, downloaded DEM source tiles, cache folders, runtime manifests, or runtime summaries. This package is the schema and naming contract that later source resolvers, adapters, raster processors, and validators will consume.
