from pathlib import Path
import json
import warnings

import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds

warnings.filterwarnings("ignore", category=DeprecationWarning)


dtm_path = Path("data_original") / "dtm.tif"

output_bin_path = Path("data_processed") / "elevation_window_int16.bin"
output_metadata_path = Path("data_processed") / "elevation_window_metadata.json"

# Exact orthophoto bounds from gpkg_contents, in EPSG:4326
min_lon = 35.28
min_lat = 32.8397
max_lon = 35.3918
max_lat = 32.8868

gpkg_bounds_4326 = (min_lon, min_lat, max_lon, max_lat)


with rasterio.open(dtm_path) as src:
    # Convert orthophoto bounds to the DTM CRS
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

    output_bin_path.parent.mkdir(parents=True, exist_ok=True)

    # Save the elevation values as raw int16 binary
    data.astype("int16").tofile(output_bin_path)

    metadata = {
        "description": "DTM window covering the orthophoto area. Values are stored as row-major int16.",
        "source_dtm": "dtm.tif",
        "orthophoto_bounds_epsg_4326": {
            "min_lon": min_lon,
            "min_lat": min_lat,
            "max_lon": max_lon,
            "max_lat": max_lat,
        },
        "dtm_crs": str(src.crs),
        "nodata": src.nodata,
        "window": {
            "col_off": int(window.col_off),
            "row_off": int(window.row_off),
            "width": int(window.width),
            "height": int(window.height),
        },
        "dtm_transform": {
            "a_pixel_width": src.transform.a,
            "b_rotation": src.transform.b,
            "c_top_left_x": src.transform.c,
            "d_rotation": src.transform.d,
            "e_pixel_height": src.transform.e,
            "f_top_left_y": src.transform.f,
        },
        "binary_file": output_bin_path.name,
        "binary_format": {
            "dtype": "int16",
            "byte_order": "native",
            "layout": "row-major",
            "index_formula": "index = row * width + col"
        }
    }

    with output_metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print("Exported elevation window")
    print("-------------------------")
    print("Window:", window)
    print("Shape:", data.shape)
    print("Binary file:", output_bin_path)
    print("Metadata file:", output_metadata_path)
    print("Binary size bytes:", output_bin_path.stat().st_size)