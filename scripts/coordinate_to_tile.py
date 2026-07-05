import math

# From gpkg_tile_matrix_set:
# table_name='SAKHNIN', srs_id=4326,
# min_x, min_y, max_x, max_y
matrix_min_x = 35.28
matrix_min_y = 32.71101722095672
matrix_max_x = 35.45578150760521
matrix_max_y = 32.8868

tile_size = 256

# We start with zoom 9 because it is the highest-resolution level.
zoom_level = 9
matrix_width = 512
matrix_height = 512

# A point roughly in the middle of the actual orthophoto bounds:
# gpkg_contents bounds:
# lon: 35.28 to 35.3918
# lat: 32.8397 to 32.8868
lon = (35.28 + 35.3918) / 2
lat = (32.8397 + 32.8868) / 2

tile_col = math.floor(
    (lon - matrix_min_x) / (matrix_max_x - matrix_min_x) * matrix_width
)

tile_row = math.floor(
    (matrix_max_y - lat) / (matrix_max_y - matrix_min_y) * matrix_height
)

print("Input coordinate:")
print("lon:", lon)
print("lat:", lat)

print("\nCalculated tile:")
print("zoom:", zoom_level)
print("tile_col:", tile_col)
print("tile_row:", tile_row)

print("\nExpected to be around the center of the existing zoom 9 range:")
print("cols: 0-325")
print("rows: 0-137")