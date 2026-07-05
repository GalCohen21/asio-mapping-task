from pathlib import Path

import rasterio
from rasterio.warp import transform
from rasterio.windows import Window

dtm_path = Path("data_original") / "dtm.tif"

# Same point as before
lon = 35.3359
lat = 32.86325

with rasterio.open(dtm_path) as src:
    # Convert from lon/lat to the DTM coordinate system
    xs, ys = transform(
        "EPSG:4326",
        src.crs,
        [lon],
        [lat],
    )

    x = xs[0]
    y = ys[0]

    # Convert projected coordinate to raster row/column
    row, col = src.index(x, y)

    # Read only one pixel from the DTM
    value = src.read(1, window=Window(col, row, 1, 1))[0, 0]

    print("Input coordinate:")
    print("lon:", lon)
    print("lat:", lat)

    print("\nConverted to DTM CRS:")
    print("x:", x)
    print("y:", y)

    print("\nDTM pixel:")
    print("row:", row)
    print("col:", col)

    print("\nElevation:")
    print("value:", value)

    if value == src.nodata:
        print("This is a NoData pixel")
    else:
        print("Valid elevation value")