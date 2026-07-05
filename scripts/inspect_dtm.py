from rasterio.warp import transform_bounds

# Bounds from gpkg_contents:
# min_x, min_y, max_x, max_y in EPSG:4326
gpkg_bounds_4326 = (35.28, 32.8397, 35.3918, 32.8868)

gpkg_bounds_32636 = transform_bounds(
    "EPSG:4326",
    "EPSG:32636",
    *gpkg_bounds_4326,
    densify_pts=21,
)

print("GPKG bounds in EPSG:4326:")
print(gpkg_bounds_4326)

print("\nGPKG bounds transformed to EPSG:32636:")
print(gpkg_bounds_32636)

print("\nDTM bounds in EPSG:32636:")
print((
    474035.41821334185,
    3230611.5944371745,
    882315.4182133419,
    3830701.5944371745,
))