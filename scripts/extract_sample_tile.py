import sqlite3
from pathlib import Path

gpkg_path = Path("data_original") / "Orthophoto.gpkg"
output_path = Path("data_processed") / "sample_tile_z9_center.jpg"

zoom_level = 9
tile_column = 162
tile_row = 68

con = sqlite3.connect(gpkg_path)
cur = con.cursor()

row = cur.execute(
    """
    SELECT tile_data
    FROM SAKHNIN
    WHERE zoom_level = ?
      AND tile_column = ?
      AND tile_row = ?;
    """,
    (zoom_level, tile_column, tile_row),
).fetchone()

con.close()

if row is None:
    raise ValueError("Tile not found")

tile_data = row[0]

output_path.write_bytes(tile_data)

print(f"Saved tile to: {output_path}")
print(f"Tile size in bytes: {len(tile_data)}")