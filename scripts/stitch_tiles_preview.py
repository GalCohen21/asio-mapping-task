import sqlite3
from io import BytesIO
from pathlib import Path

from PIL import Image

gpkg_path = Path("data_original") / "Orthophoto.gpkg"
output_path = Path("data_processed") / "tiles_preview_3x3.jpg"

zoom_level = 9

# A center-ish location inside the available tile range
start_col = 161
start_row = 67

tile_size = 256
grid_size = 3

preview = Image.new(
    "RGB",
    (tile_size * grid_size, tile_size * grid_size)
)

con = sqlite3.connect(gpkg_path)
cur = con.cursor()

for dy in range(grid_size):
    for dx in range(grid_size):
        col = start_col + dx
        row = start_row + dy

        result = cur.execute(
            """
            SELECT tile_data
            FROM SAKHNIN
            WHERE zoom_level = ?
              AND tile_column = ?
              AND tile_row = ?;
            """,
            (zoom_level, col, row),
        ).fetchone()

        if result is None:
            raise ValueError(f"Tile not found: zoom={zoom_level}, col={col}, row={row}")

        tile_data = result[0]
        tile_image = Image.open(BytesIO(tile_data)).convert("RGB")

        x = dx * tile_size
        y = dy * tile_size

        preview.paste(tile_image, (x, y))

con.close()

preview.save(output_path, quality=95)

print(f"Saved preview image to: {output_path}")
print(f"Preview size: {preview.size}")