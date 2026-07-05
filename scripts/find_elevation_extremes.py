from pathlib import Path
import math
import json
import warnings

import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, transform

warnings.filterwarnings("ignore", category=DeprecationWarning)


dtm_path = Path("data_original") / "dtm.tif"
output_path = Path("data_processed") / "elevation_extremes.json"

# Exact orthophoto bounds from gpkg_contents, in EPSG:4326
min_lon = 35.28
min_lat = 32.8397
max_lon = 35.3918
max_lat = 32.8868

gpkg_bounds_4326 = (min_lon, min_lat, max_lon, max_lat)

# Minimum distance between representative points, in meters.
# The DTM CRS is EPSG:32636, so distances are measured in meters.
min_distance_meters = 300


def distance_meters(p1, p2):
    x1, y1 = p1
    x2, y2 = p2

    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def make_point(idx, values, rows, cols, xs, ys, lons, lats):
    return {
        "elevation": int(values[idx]),
        "dtm_row": int(rows[idx]),
        "dtm_col": int(cols[idx]),
        "x": float(xs[idx]),
        "y": float(ys[idx]),
        "lon": float(lons[idx]),
        "lat": float(lats[idx]),
    }


def select_raw_points(indices, values, rows, cols, xs, ys, lons, lats):
    """
    Select the exact first 5 points from the sorted indices.
    No distance filtering is applied here.
    """
    selected = []

    for idx in indices[:5]:
        selected.append(
            make_point(idx, values, rows, cols, xs, ys, lons, lats)
        )

    return selected


def select_representative_points(indices, values, rows, cols, xs, ys, lons, lats):
    """
    Select 5 representative points from the sorted indices.

    A candidate point is accepted only if it is at least
    min_distance_meters away from all previously selected points.
    """
    selected = []

    for idx in indices:
        candidate_xy = (xs[idx], ys[idx])

        too_close = False

        for point in selected:
            existing_xy = (point["x"], point["y"])

            if distance_meters(candidate_xy, existing_xy) < min_distance_meters:
                too_close = True
                break

        if too_close:
            continue

        selected.append(
            make_point(idx, values, rows, cols, xs, ys, lons, lats)
        )

        if len(selected) == 5:
            break

    return selected


def print_points(title, points):
    print(title)
    print("-" * len(title))

    for i, point in enumerate(points, start=1):
        print(
            f"{i}. elevation={point['elevation']}, "
            f"dtm_row={point['dtm_row']}, "
            f"dtm_col={point['dtm_col']}, "
            f"lon={point['lon']:.8f}, "
            f"lat={point['lat']:.8f}"
        )

    print()


with rasterio.open(dtm_path) as src:
    # Convert orthophoto bounds from EPSG:4326 to the DTM CRS
    gpkg_bounds_dtm_crs = transform_bounds(
        "EPSG:4326",
        src.crs,
        *gpkg_bounds_4326,
        densify_pts=21,
    )

    # Read only the DTM window that overlaps the orthophoto
    window = from_bounds(*gpkg_bounds_dtm_crs, transform=src.transform)
    window = window.round_offsets().round_lengths()

    data = src.read(1, window=window)

    nodata = src.nodata
    valid_mask = data != nodata

    local_rows, local_cols = np.where(valid_mask)
    values = data[local_rows, local_cols]

    absolute_rows = (window.row_off + local_rows).astype(int)
    absolute_cols = (window.col_off + local_cols).astype(int)

    # Convert DTM pixel positions to DTM coordinates, in EPSG:32636
    xs, ys = rasterio.transform.xy(
        src.transform,
        absolute_rows,
        absolute_cols,
        offset="center",
    )

    # Convert DTM coordinates back to lon/lat, in EPSG:4326
    lon_list, lat_list = transform(
        src.crs,
        "EPSG:4326",
        xs,
        ys,
    )

    xs = np.array(xs)
    ys = np.array(ys)
    lons = np.array(lon_list)
    lats = np.array(lat_list)

    # Keep only pixels inside the exact orthophoto bounds
    inside_mask = (
        (lons >= min_lon)
        & (lons <= max_lon)
        & (lats >= min_lat)
        & (lats <= max_lat)
    )

    values = values[inside_mask]
    rows = absolute_rows[inside_mask]
    cols = absolute_cols[inside_mask]
    xs = xs[inside_mask]
    ys = ys[inside_mask]
    lons = lons[inside_mask]
    lats = lats[inside_mask]

    # Sort all valid pixels by elevation
    ascending_indices = np.argsort(values)
    descending_indices = ascending_indices[::-1]

    # Raw extrema: exact 5 lowest / highest pixels
    raw_min = select_raw_points(
        ascending_indices,
        values,
        rows,
        cols,
        xs,
        ys,
        lons,
        lats,
    )

    raw_max = select_raw_points(
        descending_indices,
        values,
        rows,
        cols,
        xs,
        ys,
        lons,
        lats,
    )

    # Representative extrema: still sorted by elevation,
    # but with minimum distance between selected points
    representative_min = select_representative_points(
        ascending_indices,
        values,
        rows,
        cols,
        xs,
        ys,
        lons,
        lats,
    )

    representative_max = select_representative_points(
        descending_indices,
        values,
        rows,
        cols,
        xs,
        ys,
        lons,
        lats,
    )

    result = {
    "metadata": {
        "orthophoto_bounds_epsg_4326": {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        },
        "dtm_crs": str(src.crs),
        "minimum_distance_meters_for_representative_points": min_distance_meters,
        "valid_pixels_inside_orthophoto_bounds": int(values.size),
        "note": (
            "Raw points are the exact 5 lowest/highest pixels. "
            "Representative points use a minimum-distance filter "
            "to improve visual readability."
        ),
    },
    "raw": {
        "min": raw_min,
        "max": raw_max,
    },
    "representative": {
        "min": representative_min,
        "max": representative_max,
    },
}

output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w", encoding="utf-8") as f:
    json.dump(result, f, indent=2)

    print("Window:", window)
    print("Window shape:", data.shape)
    print("Valid pixels inside exact orthophoto bounds:", values.size)
    print("Minimum distance for representative points:", min_distance_meters, "meters")
    print()
    print(f"Saved JSON to: {output_path}")
    print()

    print_points("Raw 5 lowest points", raw_min)
    print_points("Raw 5 highest points", raw_max)
    print_points("Representative 5 lowest points", representative_min)
    print_points("Representative 5 highest points", representative_max)