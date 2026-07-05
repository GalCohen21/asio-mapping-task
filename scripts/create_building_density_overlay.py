from pathlib import Path
import json
import sqlite3

import numpy as np
from PIL import Image, ImageFilter


PROJECT_ROOT = Path(__file__).resolve().parents[1]

GPKG_PATH = PROJECT_ROOT / "data_original" / "Orthophoto.gpkg"

OUTPUT_OVERLAY_PATH = PROJECT_ROOT / "data_processed" / "building_density_overlay.png"
OUTPUT_SUMMARY_PATH = PROJECT_ROOT / "data_processed" / "building_density_summary.json"

ANDROID_ASSET_OVERLAY_PATH = (
    PROJECT_ROOT / "android_app" / "app" / "src" / "main" / "assets" / "building_density_overlay.png"
)
ANDROID_ASSET_SUMMARY_PATH = (
    PROJECT_ROOT / "android_app" / "app" / "src" / "main" / "assets" / "building_density_summary.json"
)

TILE_SIZE = 256

# We use zoom 6 because it is detailed enough for a visual approximation,
# but still small enough to process quickly.
ZOOM_LEVEL = 6
START_COL = 0
START_ROW = 0
GRID_COLS = 41
GRID_ROWS = 18

# Zoom 6 matrix size from the GeoPackage tile matrix.
MATRIX_WIDTH = 64
MATRIX_HEIGHT = 64

# GeoPackage matrix bounds
MATRIX_MIN_LON = 35.28
MATRIX_MIN_LAT = 32.71101722095672
MATRIX_MAX_LON = 35.45578150760521
MATRIX_MAX_LAT = 32.8868

# Actual orthophoto content bounds
CONTENT_MIN_LON = 35.28
CONTENT_MIN_LAT = 32.8397
CONTENT_MAX_LON = 35.3918
CONTENT_MAX_LAT = 32.8868

# Same size as the elevation window, so Android can draw it using the same destination rect.
OUTPUT_WIDTH = 1058
OUTPUT_HEIGHT = 545


def lon_lat_to_local_pixel(lon: float, lat: float) -> tuple[int, int]:
    total_matrix_pixel_width = MATRIX_WIDTH * TILE_SIZE
    total_matrix_pixel_height = MATRIX_HEIGHT * TILE_SIZE

    global_x = (
        (lon - MATRIX_MIN_LON)
        / (MATRIX_MAX_LON - MATRIX_MIN_LON)
        * total_matrix_pixel_width
    )

    global_y = (
        (MATRIX_MAX_LAT - lat)
        / (MATRIX_MAX_LAT - MATRIX_MIN_LAT)
        * total_matrix_pixel_height
    )

    local_x = global_x - START_COL * TILE_SIZE
    local_y = global_y - START_ROW * TILE_SIZE

    return int(round(local_x)), int(round(local_y))


def load_zoom_mosaic() -> Image.Image:
    if not GPKG_PATH.exists():
        raise FileNotFoundError(f"Missing GeoPackage file: {GPKG_PATH}")

    mosaic_width = GRID_COLS * TILE_SIZE
    mosaic_height = GRID_ROWS * TILE_SIZE

    mosaic = Image.new("RGB", (mosaic_width, mosaic_height), color=(255, 255, 255))

    conn = sqlite3.connect(GPKG_PATH)
    cursor = conn.cursor()

    loaded_tiles = 0

    for dy in range(GRID_ROWS):
        for dx in range(GRID_COLS):
            tile_col = START_COL + dx
            tile_row = START_ROW + dy

            cursor.execute(
                """
                SELECT tile_data
                FROM SAKHNIN
                WHERE zoom_level = ?
                  AND tile_column = ?
                  AND tile_row = ?
                """,
                (ZOOM_LEVEL, tile_col, tile_row),
            )

            row = cursor.fetchone()

            if row is None:
                continue

            tile_bytes = row[0]
            tile = Image.open(__import__("io").BytesIO(tile_bytes)).convert("RGB")

            mosaic.paste(tile, (dx * TILE_SIZE, dy * TILE_SIZE))
            loaded_tiles += 1

    conn.close()

    print(f"Loaded {loaded_tiles} tiles at zoom {ZOOM_LEVEL}")

    return mosaic


def create_built_up_mask(image: Image.Image) -> np.ndarray:
    arr = np.asarray(image).astype(np.float32) / 255.0

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    max_channel = np.maximum(np.maximum(r, g), b)
    min_channel = np.minimum(np.minimum(r, g), b)

    brightness = max_channel
    saturation = (max_channel - min_channel) / (max_channel + 1e-6)

    # Approximate vegetation removal:
    # green pixels are unlikely to be buildings.
    green_like = (
        (g > r * 1.08)
        & (g > b * 1.08)
        & (saturation > 0.18)
        & (brightness > 0.20)
    )

    very_dark = brightness < 0.18

    # Concrete / roofs / paved built-up surfaces are often grey-ish or bright.
    grey_or_concrete = (
        (saturation < 0.28)
        & (brightness > 0.32)
        & (~green_like)
        & (~very_dark)
    )

    # Some roofs are reddish / brown-ish.
    red_roof_like = (
        (r > g * 1.10)
        & (r > b * 1.10)
        & (brightness > 0.25)
        & (saturation > 0.18)
        & (~green_like)
        & (~very_dark)
    )

    # Combine the simple visual rules.
    candidate_mask = grey_or_concrete | red_roof_like

    # Light cleanup to reduce single-pixel noise.
    mask_image = Image.fromarray((candidate_mask.astype(np.uint8)) * 255)
    mask_image = mask_image.filter(ImageFilter.MedianFilter(size=3))
    mask_image = mask_image.filter(ImageFilter.MaxFilter(size=3))
    mask_image = mask_image.filter(ImageFilter.MinFilter(size=3))

    return np.asarray(mask_image) > 0


def main():
    mosaic = load_zoom_mosaic()

    left, top = lon_lat_to_local_pixel(CONTENT_MIN_LON, CONTENT_MAX_LAT)
    right, bottom = lon_lat_to_local_pixel(CONTENT_MAX_LON, CONTENT_MIN_LAT)

    print(f"Cropping content area: left={left}, top={top}, right={right}, bottom={bottom}")

    content_crop = mosaic.crop((left, top, right, bottom))
    content_resized = content_crop.resize(
        (OUTPUT_WIDTH, OUTPUT_HEIGHT),
        Image.Resampling.BILINEAR,
    )

    built_up_mask = create_built_up_mask(content_resized)

    density_percentage = built_up_mask.mean() * 100.0

    overlay = np.zeros((OUTPUT_HEIGHT, OUTPUT_WIDTH, 4), dtype=np.uint8)

    # Orange transparent overlay for estimated built-up areas.
    overlay[built_up_mask] = [255, 140, 0, 120]

    overlay_image = Image.fromarray(overlay, mode="RGBA")

    OUTPUT_OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    overlay_image.save(OUTPUT_OVERLAY_PATH)

    summary = {
        "density_percentage": round(float(density_percentage), 2),
        "method": "Approximate raster-based built-up density estimation from RGB orthophoto.",
        "important_note": (
            "This is not an exact GIS building-footprint calculation. "
            "It is a visual heuristic based on color and brightness patterns in the orthophoto."
        ),
        "zoom_level_used": ZOOM_LEVEL,
        "output_width": OUTPUT_WIDTH,
        "output_height": OUTPUT_HEIGHT,
    }

    with open(OUTPUT_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    ANDROID_ASSET_OVERLAY_PATH.parent.mkdir(parents=True, exist_ok=True)
    overlay_image.save(ANDROID_ASSET_OVERLAY_PATH)

    with open(ANDROID_ASSET_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Built-up density estimate: {density_percentage:.2f}%")
    print(f"Saved overlay: {OUTPUT_OVERLAY_PATH}")
    print(f"Saved summary: {OUTPUT_SUMMARY_PATH}")
    print(f"Copied overlay to Android assets: {ANDROID_ASSET_OVERLAY_PATH}")
    print(f"Copied summary to Android assets: {ANDROID_ASSET_SUMMARY_PATH}")


if __name__ == "__main__":
    main()