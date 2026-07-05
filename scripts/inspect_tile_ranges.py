import sqlite3
from pathlib import Path

gpkg_path = Path("data_original") / "Orthophoto.gpkg"

con = sqlite3.connect(gpkg_path)
cur = con.cursor()

rows = cur.execute(
    """
    SELECT
        zoom_level,
        COUNT(*) AS tile_count,
        MIN(tile_column) AS min_col,
        MAX(tile_column) AS max_col,
        MIN(tile_row) AS min_row,
        MAX(tile_row) AS max_row
    FROM SAKHNIN
    GROUP BY zoom_level
    ORDER BY zoom_level;
    """
).fetchall()

print("Tile ranges by zoom level:")
for row in rows:
    zoom, count, min_col, max_col, min_row, max_row = row
    print(
        f"zoom={zoom}, "
        f"count={count}, "
        f"cols={min_col}-{max_col}, "
        f"rows={min_row}-{max_row}"
    )

con.close()