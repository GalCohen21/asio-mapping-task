import math

# From gpkg_tile_matrix_set
matrix_min_x = 35.28
matrix_min_y = 32.71101722095672
matrix_max_x = 35.45578150760521
matrix_max_y = 32.8868

tile_size = 256

# Zoom 9 metadata
zoom_level = 9
matrix_width = 512
matrix_height = 512

# A point roughly in the middle of the actual orthophoto bounds
lon = (35.28 + 35.3918) / 2
lat = (32.8397 + 32.8868) / 2

total_pixel_width = matrix_width * tile_size
total_pixel_height = matrix_height * tile_size

# Global pixel position inside the entire tile matrix
global_pixel_x = (
    (lon - matrix_min_x)
    / (matrix_max_x - matrix_min_x)
    * total_pixel_width
)

global_pixel_y = (
    (matrix_max_y - lat)
    / (matrix_max_y - matrix_min_y)
    * total_pixel_height
)

tile_col = math.floor(global_pixel_x / tile_size)
tile_row = math.floor(global_pixel_y / tile_size)

pixel_x_inside_tile = math.floor(global_pixel_x - tile_col * tile_size)
pixel_y_inside_tile = math.floor(global_pixel_y - tile_row * tile_size)

print("Input coordinate:")
print("lon:", lon)
print("lat:", lat)

print("\nGlobal pixel position in tile matrix:")
print("global_pixel_x:", global_pixel_x)
print("global_pixel_y:", global_pixel_y)

print("\nTile:")
print("zoom:", zoom_level)
print("tile_col:", tile_col)
print("tile_row:", tile_row)

print("\nPixel inside tile:")
print("pixel_x_inside_tile:", pixel_x_inside_tile)
print("pixel_y_inside_tile:", pixel_y_inside_tile)