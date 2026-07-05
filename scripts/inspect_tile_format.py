import sqlite3
from pathlib import Path

gpkg_path = Path("data_original") / "Orthophoto.gpkg"

con = sqlite3.connect(gpkg_path)
cur = con.cursor()

row = cur.execute(
    """
    SELECT zoom_level, tile_column, tile_row, tile_data
    FROM SAKHNIN
    LIMIT 1;
    """
).fetchone()

zoom_level, tile_column, tile_row, tile_data = row

print("Sample tile:")
print("zoom_level:", zoom_level)
print("tile_column:", tile_column)
print("tile_row:", tile_row)
print("tile_data length:", len(tile_data))
print("first bytes:", tile_data[:20])

if tile_data.startswith(b"\x89PNG"):
    print("Detected format: PNG")
elif tile_data.startswith(b"\xff\xd8"):
    print("Detected format: JPEG")
else:
    print("Detected format: unknown")

con.close()