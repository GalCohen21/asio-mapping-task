# ASIO Mapping Task

Android GIS mapping application written in Kotlin.

The app displays an orthophoto map from a GeoPackage file and overlays DTM-based elevation information.

## App Features

- Displays orthophoto tiles from `Orthophoto.gpkg`
- Displays a DTM-based elevation heatmap over the orthophoto
- Displays 5 minimum and 5 maximum elevation points
- Supports extrema marker modes: Off, Representative, Raw
- Shows elevation from the DTM when tapping on the map
- Shows local built-up density estimate when tapping on the map
- Bonus: topographic contour line overlay
- Bonus: built-up density percentage estimate

## Project Structure

- `android_app/` - Android Studio project
- `scripts/` - Python preprocessing scripts
- `android_app/app/src/main/assets/` - processed files used by the Android app
- `docs/WORK_LOG.md` - development work log
- `Summary.pdf` - short reflection summary for the assignment
- `Demo_Video.mp4` - demo video showing the app features

## Data Files

The original GIS files are large and are not included in the GitHub repository:

- `Orthophoto.gpkg`
- `dtm.tif`
- `dtm.tfw`

The Android app expects `Orthophoto.gpkg` to be located on the emulator/device at:

```text
/sdcard/Android/data/com.galcohen.asiomapping/files/Orthophoto.gpkg
```

Example ADB command:

```powershell
& "C:\Users\cohen\AppData\Local\Android\Sdk\platform-tools\adb.exe" push "data_original\Orthophoto.gpkg" "/sdcard/Android/data/com.galcohen.asiomapping/files/Orthophoto.gpkg"
```

## Preprocessing

Heavy GIS/raster processing is done in Python before running the Android app, so the app can stay lighter and more stable.

The preprocessing creates files such as:

- `elevation_window_int16.bin`
- `elevation_window_metadata.json`
- `elevation_extremes.json`
- `elevation_heatmap_overlay.png`
- `contour_overlay.png`
- `building_density_overlay.png`
- `building_density_summary.json`

These processed files are included in the Android assets folder.

Main preprocessing scripts:

- `scripts/inspect_dtm.py`
- `scripts/find_elevation_extremes.py`
- `scripts/export_elevation_window.py`
- `scripts/create_elevation_heatmap_overlay.py`
- `scripts/create_contour_overlay.py`
- `scripts/create_building_density_overlay.py`

Run preprocessing scripts from the project root.

Install Python dependencies with:

```bash
python -m pip install -r requirements.txt
```

Exact package versions are listed in `requirements.txt`.

## How to Run

1. Open `android_app/` in Android Studio.
2. Start an Android emulator.
3. Push `Orthophoto.gpkg` to the emulator using the ADB command above.
4. Run the app from Android Studio.

## Versions and Libraries

Android:

- Language: Kotlin
- Minimum SDK: 26
- Target SDK: 36
- Compile SDK: Android API 37.1
- Package name: `com.galcohen.asiomapping`

Android APIs used:

- SQLite API for reading GeoPackage tiles
- Canvas API for drawing the map, overlays, markers, labels, and tap indicator
- Bitmap / BitmapFactory for decoding JPEG tiles and PNG overlays
- Assets API for reading processed DTM and overlay files

Python preprocessing:

- `numpy`
- `rasterio`
- `Pillow`
- `matplotlib`

## Notes

- The elevation heatmap is used for visual display. Exact elevation values are read from `elevation_window_int16.bin`.
- The Android app reads DTM window configuration from `elevation_window_metadata.json`.
- Built-up density is an approximate raster-based estimate from the orthophoto, not an exact GIS building-footprint calculation.
- The app currently displays a stable overview map rather than a full pan/zoom GIS viewer.
