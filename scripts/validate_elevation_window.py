from pathlib import Path
import json
import math

import numpy as np
from rasterio.warp import transform


bin_path = Path("data_processed") / "elevation_window_int16.bin"
metadata_path = Path("data_processed") / "elevation_window_metadata.json"

# Same test coordinate we used before
lon = 35.3359
lat = 32.86325

with metadata_path.open("r", encoding="utf-8") as f:
    metadata = json.load(f)

width = metadata["window"]["width"]
height = metadata["window"]["height"]
window_col_off = metadata["window"]["col_off"]
window_row_off = metadata["window"]["row_off"]

t = metadata["dtm_transform"]

pixel_width = t["a_pixel_width"]
pixel_height = t["e_pixel_height"]
top_left_x = t["c_top_left_x"]
top_left_y = t["f_top_left_y"]

# Load the exported DTM window
data = np.fromfile(bin_path, dtype=np.int16).reshape((height, width))

# Convert lon/lat to the DTM coordinate system
xs, ys = transform(
    "EPSG:4326",
    metadata["dtm_crs"],
    [lon],
    [lat],
)

x = xs[0]
y = ys[0]

# Convert DTM CRS coordinate to absolute DTM row/col
absolute_col = math.floor((x - top_left_x) / pixel_width)
absolute_row = math.floor((y - top_left_y) / pixel_height)

# Convert absolute DTM row/col to local row/col inside the exported window
local_col = absolute_col - window_col_off
local_row = absolute_row - window_row_off

elevation = data[local_row, local_col]

print("Input coordinate:")
print("lon:", lon)
print("lat:", lat)

print("\nConverted to DTM CRS:")
print("x:", x)
print("y:", y)

print("\nAbsolute DTM pixel:")
print("row:", absolute_row)
print("col:", absolute_col)

print("\nLocal window pixel:")
print("row:", local_row)
print("col:", local_col)

print("\nElevation from exported window:")
print("value:", int(elevation))