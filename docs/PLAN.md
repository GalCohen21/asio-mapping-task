# ASIO Mapping Task - Development Plan

## 1. Initial Understanding

The goal of this task is to build an Android application in Kotlin that displays an orthophoto map, overlays elevation data, and allows the user to inspect terrain height values interactively.

The main required features are:

* Display an orthophoto image/map from a GeoPackage (`.gpkg`) file.
* Display an elevation layer on top of the selected image.
* Mark the 5 highest and 5 lowest elevation points.
* Show the relevant elevation value when the user taps on the image.
* Provide a short demo video.
* Document the implementation approach, main decisions, challenges, and personal experience.

## 2. Provided Data

The provided files are:

* `Orthophoto.gpkg` - GeoPackage file containing the orthophoto map.
* `dtm.tif` - Digital Terrain Model raster file containing elevation data.
* `dtm.tfw` - world file describing the spatial mapping of the DTM raster.
* `task.pdf` / `task.docx` - task instructions.

## 3. Main Technical Challenge

The main technical challenge is expected to be coordinate mapping:

screen tap → image pixel → geographic coordinate → DTM pixel → elevation value

This mapping is important because the displayed image and the elevation raster may have different dimensions, resolutions, and coordinate systems. Therefore, the app should not assume that the same pixel indices can be used directly for both files.

## 4. Guiding Principles

* First understand the provided data before implementing the Android UI.
* Keep the application simple, stable, and easy to explain.
* Prioritize the required features before optional bonuses.
* Use preprocessing if the original GIS files are too large for efficient Android rendering.
* Keep the code modular and readable.
* Document assumptions, limitations, and tradeoffs clearly.

## 5. Initial Work Plan

1. Inspect the provided GIS files.
2. Understand the structure of the GeoPackage.
3. Inspect the DTM raster and its spatial metadata.
4. Decide whether preprocessing is needed.
5. Generate Android-friendly assets if necessary.
6. Build a minimal Android viewer.
7. Add the elevation overlay.
8. Mark the 5 highest and 5 lowest elevation points.
9. Implement tap-to-elevation lookup.
10. Prepare README, summary, and demo video.

## 6. Open Questions

* What exactly is stored inside `Orthophoto.gpkg`?
* Do the orthophoto and DTM cover the same geographic area?
* Are both files using the same coordinate reference system?
* What is the best way to handle the large file sizes efficiently on Android?
* Which optional bonuses are realistic after the required features are complete?
