from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ELEVATION_BIN_PATH = PROJECT_ROOT / "data_processed" / "elevation_window_int16.bin"
OUTPUT_PATH = PROJECT_ROOT / "data_processed" / "contour_overlay.png"
ANDROID_ASSET_PATH = PROJECT_ROOT / "android_app" / "app" / "src" / "main" / "assets" / "contour_overlay.png"

ELEVATION_WIDTH = 1058
ELEVATION_HEIGHT = 545
NO_DATA_VALUE = -32768

CONTOUR_INTERVAL_METERS = 50


def main():
    elevation = np.fromfile(ELEVATION_BIN_PATH, dtype="<i2")

    expected_size = ELEVATION_WIDTH * ELEVATION_HEIGHT
    if elevation.size != expected_size:
        raise ValueError(
            f"Expected {expected_size} elevation values, got {elevation.size}"
        )

    elevation = elevation.reshape((ELEVATION_HEIGHT, ELEVATION_WIDTH)).astype(float)
    elevation[elevation == NO_DATA_VALUE] = np.nan

    min_elevation = int(np.nanmin(elevation))
    max_elevation = int(np.nanmax(elevation))

    first_level = (
        (min_elevation + CONTOUR_INTERVAL_METERS - 1)
        // CONTOUR_INTERVAL_METERS
        * CONTOUR_INTERVAL_METERS
    )

    last_level = (
        max_elevation
        // CONTOUR_INTERVAL_METERS
        * CONTOUR_INTERVAL_METERS
    )

    levels = np.arange(
        first_level,
        last_level + CONTOUR_INTERVAL_METERS,
        CONTOUR_INTERVAL_METERS,
    )

    print(f"Elevation range: {min_elevation}m - {max_elevation}m")
    print(f"Contour interval: {CONTOUR_INTERVAL_METERS}m")
    print(f"Contour levels: {levels.tolist()}")

    dpi = 100

    fig = plt.figure(
        figsize=(ELEVATION_WIDTH / dpi, ELEVATION_HEIGHT / dpi),
        dpi=dpi,
    )

    fig.patch.set_alpha(0)

    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    ax.patch.set_alpha(0)

    x = np.arange(ELEVATION_WIDTH)
    y = np.arange(ELEVATION_HEIGHT)

    ax.set_xlim(0, ELEVATION_WIDTH - 1)
    ax.set_ylim(ELEVATION_HEIGHT - 1, 0)
    ax.set_aspect("auto")

    # Very subtle white halo, only for contrast on dark imagery
    ax.contour(
        x,
        y,
        elevation,
        levels=levels,
        colors="white",
        linewidths=1.2,
        alpha=0.25,
    )

    # Main contour line
    ax.contour(
        x,
        y,
        elevation,
        levels=levels,
        colors="black",
        linewidths=1.1,
        alpha=0.95,
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    fig.savefig(
        OUTPUT_PATH,
        transparent=True,
        dpi=dpi,
        pad_inches=0,
    )

    plt.close(fig)

    image = Image.open(OUTPUT_PATH)
    print(f"Saved contour overlay: {OUTPUT_PATH}")
    print(f"PNG size: {image.size}")

    ANDROID_ASSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    image.save(ANDROID_ASSET_PATH)

    print(f"Copied to Android assets: {ANDROID_ASSET_PATH}")


if __name__ == "__main__":
    main()