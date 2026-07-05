from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ELEVATION_BIN_PATH = PROJECT_ROOT / "data_processed" / "elevation_window_int16.bin"

OUTPUT_IMAGE_PATH = PROJECT_ROOT / "data_processed" / "elevation_heatmap_overlay.png"
OUTPUT_SUMMARY_PATH = PROJECT_ROOT / "data_processed" / "elevation_heatmap_summary.json"

ANDROID_ASSET_IMAGE_PATH = (
    PROJECT_ROOT / "android_app" / "app" / "src" / "main" / "assets" / "elevation_heatmap_overlay.png"
)

ANDROID_ASSET_SUMMARY_PATH = (
    PROJECT_ROOT / "android_app" / "app" / "src" / "main" / "assets" / "elevation_heatmap_summary.json"
)

ELEVATION_WIDTH = 1058
ELEVATION_HEIGHT = 545
NO_DATA_VALUE = -32768

COLORMAP_NAME = "terrain_like"

CUSTOM_COLORS = [
    "#1f5d2f",  # dark green
    "#6fae4a",  # light green
    "#d7c08a",  # light brown / beige
    "#a87b4f",  # medium brown
    "#6b4a2f",  # dark brown
]

# Alpha controls how strongly the heatmap covers the orthophoto.
# 0 = fully transparent, 255 = fully opaque.
ALPHA = 120

# Percentile clipping improves visual contrast without changing exact tap values.
LOW_PERCENTILE = 2
HIGH_PERCENTILE = 98


def main():
    if not ELEVATION_BIN_PATH.exists():
        raise FileNotFoundError(f"Missing input file: {ELEVATION_BIN_PATH}")

    elevation = np.fromfile(ELEVATION_BIN_PATH, dtype="<i2")

    expected_size = ELEVATION_WIDTH * ELEVATION_HEIGHT
    if elevation.size != expected_size:
        raise ValueError(
            f"Expected {expected_size} elevation values, got {elevation.size}"
        )

    elevation = elevation.reshape((ELEVATION_HEIGHT, ELEVATION_WIDTH)).astype(np.float32)

    valid_mask = elevation != NO_DATA_VALUE
    valid_values = elevation[valid_mask]

    min_elevation = float(valid_values.min())
    max_elevation = float(valid_values.max())

    visual_min = float(np.percentile(valid_values, LOW_PERCENTILE))
    visual_max = float(np.percentile(valid_values, HIGH_PERCENTILE))

    print(f"Elevation range: {min_elevation:.1f}m - {max_elevation:.1f}m")
    print(f"Visual range: {visual_min:.1f}m - {visual_max:.1f}m")
    print(f"Colormap: {COLORMAP_NAME}")
    print(f"Alpha: {ALPHA}")

    normalized = np.zeros_like(elevation, dtype=np.float32)

    normalized[valid_mask] = (
        (elevation[valid_mask] - visual_min) /
        (visual_max - visual_min)
    )

    normalized = np.clip(normalized, 0.0, 1.0)

    cmap = LinearSegmentedColormap.from_list(
    COLORMAP_NAME,
    CUSTOM_COLORS,
    N=256
    )
    
    rgba = cmap(normalized)

    rgba_image = (rgba * 255).astype(np.uint8)

    # Make NoData transparent.
    rgba_image[:, :, 3] = np.where(valid_mask, ALPHA, 0).astype(np.uint8)

    image = Image.fromarray(rgba_image, mode="RGBA")

    OUTPUT_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT_IMAGE_PATH)

    summary = {
        "min_elevation": round(min_elevation, 2),
        "max_elevation": round(max_elevation, 2),
        "visual_min_percentile": LOW_PERCENTILE,
        "visual_max_percentile": HIGH_PERCENTILE,
        "visual_min_elevation": round(visual_min, 2),
        "visual_max_elevation": round(visual_max, 2),
        "colormap": COLORMAP_NAME,
        "alpha": ALPHA,
        "important_note": (
            "This PNG is only a visual elevation overlay. "
            "Exact elevation values are still read from elevation_window_int16.bin."
        ),
    }

    with open(OUTPUT_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    ANDROID_ASSET_IMAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(ANDROID_ASSET_IMAGE_PATH)

    with open(ANDROID_ASSET_SUMMARY_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"Saved heatmap overlay: {OUTPUT_IMAGE_PATH}")
    print(f"Saved summary: {OUTPUT_SUMMARY_PATH}")
    print(f"Copied heatmap overlay to Android assets: {ANDROID_ASSET_IMAGE_PATH}")
    print(f"Copied summary to Android assets: {ANDROID_ASSET_SUMMARY_PATH}")


if __name__ == "__main__":
    main()