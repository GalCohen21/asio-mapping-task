from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds

dtm_path = Path("data_original") / "dtm.tif"

# Bounds from gpkg_contents in EPSG:4326
gpkg_bounds_4326 = (35.28, 32.8397, 35.3918, 32.8868)

with rasterio.open(dtm_path) as src:
    gpkg_bounds_dtm_crs = transform_bounds(
        "EPSG:4326",
        src.crs,
        *gpkg_bounds_4326,
        densify_pts=21,
    )

    window = from_bounds(*gpkg_bounds_dtm_crs, transform=src.transform)
    window = window.round_offsets().round_lengths()

    data = src.read(1, window=window)

    nodata = src.nodata
    valid = data[data != nodata]

    print("DTM CRS:", src.crs)
    print("GPKG bounds in DTM CRS:", gpkg_bounds_dtm_crs)
    print("Window:", window)
    print("Window shape:", data.shape)
    print("NoData value:", nodata)
    print("Valid pixels:", valid.size)
    print("Min elevation:", valid.min())
    print("Max elevation:", valid.max())
    print("Mean elevation:", round(float(valid.mean()), 2))