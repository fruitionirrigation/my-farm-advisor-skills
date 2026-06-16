# Grower Web Map Subskill

## Assignment 1 – Interactive Grower-Level Web Map

This subskill generates a lightweight, self-contained interactive HTML map for each grower in the My Farm Advisor data pipeline.

### What It Does

- Scans all farms under `growers/<grower>/farms/`
- Reads the actual downloaded field polygon boundaries (`boundary/field_boundaries.geojson`)
- Enriches each field with metadata from `field.json` (grower, farm, field name)
- Produces a single HTML file per grower with embedded GeoJSON and Leaflet.js

### Map Features

- **OpenStreetMap basemap** (loaded from CDN)
- **All fields** displayed as green polygons with hover highlight
- **Click a field** to see a popup with: Grower, Farm, Field Name, Field ID, Area (acres), County, State FIPS
- **Sidebar field list** – click any field to zoom directly to it and open its popup
- **Zoom and pan** enabled
- **Canvas rendering** for performance
- **Small file size** (~5–15 KB for typical growers, no embedded imagery or rasters)

### Usage

```bash
export DATA_PIPELINE_DATA_ROOT=/home/coder/my-farm-advisor-runtime
cd ~/my-farm-advisor-runtime/data-pipeline/src
~/my-farm-advisor-runtime/data-pipeline/.venv/bin/python \
  scripts/reporting/generate_grower_web_map.py \
  --grower-slug <grower-slug>
```

### Output

The HTML file is written to:
```
${DATA_PIPELINE_DATA_ROOT}/data-pipeline/growers/<grower-slug>/maps/grower_web_map.html
```

### Example

```bash
# Generate map for Illinois grower
~/my-farm-advisor-runtime/data-pipeline/.venv/bin/python \
  scripts/reporting/generate_grower_web_map.py \
  --grower-slug northern-il-grower

# Generate map for Iowa grower
~/my-farm-advisor-runtime/data-pipeline/.venv/bin/python \
  scripts/reporting/generate_grower_web_map.py \
  --grower-slug northern-iowa-grower
```

### Files

- **Source script:** `data-pipeline/src/scripts/reporting/generate_grower_web_map.py`
- **Runtime copy:** Synced via `scripts/install.sh --force-refresh`
