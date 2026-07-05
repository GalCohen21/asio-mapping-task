# ASIO Mapping Task - Work Log

## 1. Project Setup

Created a clean project structure and placed the original provided files under `data_original/`.

Original files:

- `Orthophoto.gpkg`
- `dtm.tif`
- `dtm.tfw`
- `task.pdf`
- `task.docx`

The original GIS files are kept separate from the source code because they are large and should not be modified directly.

## 2. GeoPackage Inspection

The `Orthophoto.gpkg` file was inspected as a SQLite-based GeoPackage.

Main tables found:

- `gpkg_spatial_ref_sys`
- `gpkg_contents`
- `gpkg_tile_matrix_set`
- `gpkg_tile_matrix`
- `SAKHNIN`

The main orthophoto layer is stored in the `SAKHNIN` table.

From `gpkg_contents`, the layer information is:

- Table name: `SAKHNIN`
- Data type: `tiles`
- CRS/SRS ID: `4326`
- Bounds:
  - min longitude: `35.28`
  - min latitude: `32.8397`
  - max longitude: `35.3918`
  - max latitude: `32.8868`

This means the orthophoto is stored as map tiles in WGS84 longitude/latitude coordinates.

## 3. Tile Structure

The GeoPackage contains tiles in zoom levels 3 to 9.

Each tile is `256 x 256` pixels.

Tile counts by zoom level:

- zoom 3: 18 tiles
- zoom 4: 55 tiles
- zoom 5: 189 tiles
- zoom 6: 738 tiles
- zoom 7: 2,870 tiles
- zoom 8: 11,247 tiles
- zoom 9: 44,988 tiles

At zoom 9, the tile range is:

- columns: `0-325`
- rows: `0-137`

This means that reconstructing the full zoom 9 orthophoto as a single image would create a very large image:

- width: `326 * 256 = 83,456` pixels
- height: `138 * 256 = 35,328` pixels

Conclusion: the Android application should avoid loading the entire orthophoto into memory. A tile-based loading approach is more appropriate.

## 4. Tile Format

A sample tile was extracted from the `SAKHNIN` table.

The tile data starts with JPEG bytes:

- first bytes: `FF D8 FF E0`
- detected format: `JPEG`

Conclusion: each tile can be decoded as a standard JPEG image.

This makes it feasible for the Android application to load tile data from SQLite/GeoPackage and decode it into bitmaps.

## 5. DTM Inspection

The `dtm.tfw` file shows that each DTM pixel represents approximately `10 x 10` meters.

The `dtm.tif` file was inspected using `rasterio`.

Main DTM metadata:

- Driver: `GTiff`
- Width: `40828`
- Height: `60009`
- Number of bands: `1`
- Data type: `int16`
- CRS: `EPSG:32636`
- NoData value: `-32768`

The DTM is much larger than the orthophoto area and uses a projected metric coordinate system.

## 6. Coordinate Systems

The orthophoto GeoPackage uses:

- `EPSG:4326` - longitude/latitude

The DTM uses:

- `EPSG:32636` - projected metric coordinates

Therefore, the application logic must handle coordinate transformation:

map tap → longitude/latitude → EPSG:32636 → DTM pixel → elevation value

## 7. DTM Coverage Check

The orthophoto bounds were transformed from `EPSG:4326` to `EPSG:32636`.

Transformed orthophoto bounds:

- x: `713282.95` to `723862.14`
- y: `3635819.54` to `3641274.35`

DTM bounds:

- x: `474035.42` to `882315.42`
- y: `3230611.59` to `3830701.59`

Conclusion: the orthophoto area is fully inside the DTM coverage.

## 8. Elevation Values in Orthophoto Area

Only the DTM window corresponding to the orthophoto area was read.

Relevant DTM window:

- shape: `545 x 1058`

Elevation values in this area:

- minimum elevation: `69`
- maximum elevation: `545`
- mean elevation: `254.35`

Conclusion: the DTM contains valid elevation values for the orthophoto area.

## 9. Tile Extraction and Stitching Test

A sample JPEG tile was extracted directly from the `SAKHNIN` table inside the GeoPackage and saved as an image.

Then, a `3 x 3` tile preview was generated from neighboring tiles at zoom level 9.

The resulting image was continuous and visually correct.

Conclusion: tile coordinates are ordered as expected:

- increasing `tile_column` moves right
- increasing `tile_row` moves down

This confirms that the Android application can load and render orthophoto tiles directly from the GeoPackage instead of converting the full orthophoto into a single image.

## 10. Coordinate to Tile and Elevation Tests

A test coordinate inside the orthophoto area was selected:

- longitude: `35.3359`
- latitude: `32.86325`

Using the GeoPackage tile matrix, the coordinate was mapped to zoom level 9:

- tile column: `162`
- tile row: `68`
- pixel inside tile: `(209, 152)`

This confirmed the coordinate-to-tile calculation.

The same coordinate was then transformed from `EPSG:4326` to the DTM CRS, `EPSG:32636`:

- x: `718571.13`
- y: `3638545.51`

The projected coordinate was mapped to a DTM raster pixel:

- row: `19215`
- column: `24453`

Reading this single pixel from `dtm.tif` returned:

- elevation: `200`

Conclusion: the full coordinate-to-elevation pipeline works:

longitude/latitude → EPSG:32636 → DTM row/column → elevation value

## 11. Raw and Representative Elevation Extremes

The elevation extrema were computed in two ways:

1. Raw extrema:
   - the exact 5 lowest elevation pixels
   - the exact 5 highest elevation pixels

2. Representative extrema:
   - still selected by elevation order
   - but with a minimum distance of 300 meters between selected points

The reason for keeping both versions is that raw extrema often fall on adjacent pixels from the same terrain peak or valley. This is mathematically correct, but visually less useful.

The representative version improves map readability by showing distinct high and low terrain areas, while the raw version preserves the exact answer to the task requirement.

Current results:

Raw lowest elevations:
- 70, 70, 70, 70, 70

Raw highest elevations:
- 545, 545, 544, 544, 544

Representative lowest elevations:
- 70, 75, 78, 82, 85

Representative highest elevations:
- 545, 532, 526, 523, 519

## 12. Exported Elevation Window for Android

To avoid loading the full `dtm.tif` file on Android, only the DTM window that overlaps the orthophoto area was exported.

Exported files:

- `data_processed/elevation_window_int16.bin`
- `data_processed/elevation_window_metadata.json`

Original DTM size:

- approximately 680MB

Exported elevation window size:

- approximately 1.15MB

The exported window shape is:

- height: `545`
- width: `1058`

A validation test was performed using the coordinate:

- longitude: `35.3359`
- latitude: `32.86325`

The original `dtm.tif` lookup returned:

- elevation: `200`

The exported elevation window lookup also returned:

- elevation: `200`

Conclusion: the exported elevation window can be used by the Android app for efficient tap-to-elevation lookup.

## 13. Android Project Setup

Created a Kotlin Android project and verified that the basic app runs successfully on an Android emulator.

During setup, the project was moved to a path without non-ASCII characters because Gradle/Android Studio on Windows may fail when the project path contains Hebrew characters.

The empty Android app was successfully launched on a Pixel emulator.

## 14. Android Asset Loading Tests

The processed elevation files were copied into:

`app/src/main/assets/`

Files added:

- `elevation_extremes.json`
- `elevation_window_metadata.json`
- `elevation_window_int16.bin`

The Android app successfully loaded `elevation_extremes.json` and confirmed that each extrema list contains 5 points.

The app also loaded the binary elevation window and validated a known test pixel:

- local row: `273`
- local col: `529`
- expected elevation: `200`
- Android-read elevation: `200`

Conclusion: the Android app can read the processed DTM assets and retrieve elevation values correctly.

## 15. Android GeoPackage Tile Loading

The original `Orthophoto.gpkg` file was copied to the emulator app-specific storage during development.

The Android app successfully opened the GeoPackage as a SQLite database and queried the `SAKHNIN` tile table.

A single tile was loaded using:

- zoom level: `9`
- tile column: `162`
- tile row: `68`

The tile data was decoded from JPEG bytes into an Android bitmap and displayed on screen.

Conclusion: the Android app can directly read and render orthophoto tiles from the original GeoPackage file.

## 16. Android 3x3 Tile Grid Rendering

The Android app was extended from displaying a single GeoPackage tile to displaying a `3 x 3` grid of neighboring tiles.

The app loads tiles directly from the `SAKHNIN` table in `Orthophoto.gpkg` using:

- zoom level: `9`
- columns: `161-163`
- rows: `67-69`

Each tile is decoded from JPEG bytes into an Android bitmap and drawn on a custom `Canvas` view.

The resulting image was visually continuous.

Conclusion: the app can render multiple neighboring orthophoto tiles directly from the GeoPackage, confirming that the tile ordering and rendering logic work correctly on Android.

## 17. Android Marker Placement Test

A known test coordinate was mapped to a tile and pixel position:

- longitude: `35.3359`
- latitude: `32.86325`
- tile column: `162`
- tile row: `68`
- pixel inside tile: `(209, 152)`

Since the displayed `3 x 3` tile grid starts at:

- start column: `161`
- start row: `67`

the marker position inside the displayed grid is:

- x: `(162 - 161) * 256 + 209 = 465`
- y: `(68 - 67) * 256 + 152 = 408`

The Android app successfully drew a marker at this position on top of the rendered tiles.

Conclusion: the app can place geographic points correctly on the tile canvas once their tile and pixel position are known.

## 18. Raw / Representative Marker Toggle

The Android app now supports toggling between two marker display modes:

1. `Representative`
   - displays spatially separated elevation extrema
   - uses the 300-meter minimum-distance filtering computed during preprocessing
   - improves visual readability on the map

2. `Raw`
   - displays the exact 5 lowest and 5 highest elevation pixels
   - directly represents the strict mathematical extrema
   - points may appear close together because adjacent DTM pixels can have the same or very similar elevation

The toggle does not recompute the points on Android. Instead, both versions are precomputed and stored in `elevation_extremes.json`, and the app switches between the `representative` and `raw` sections of the JSON.

Conclusion: the app can show both the strict task result and a display-friendly interpretation.

## 19. Tap to Elevation

The Android app now supports tapping on the displayed orthophoto overview.

The tap flow is:

screen x/y
-> local map pixel
-> global tile-matrix pixel
-> lon/lat
-> EPSG:32636 / UTM coordinates
-> DTM row/col
-> elevation value

The DTM values are loaded from `elevation_window_int16.bin`, which was exported during preprocessing from the original DTM GeoTIFF.

Conclusion: the app can display the relevant elevation value for a user-selected point on the orthophoto.

## 20. Elevation Layer Overlay

The Android app now supports displaying a semi-transparent elevation layer on top of the orthophoto.

The elevation layer is generated from the exported DTM window:
- each DTM value is normalized between the minimum and maximum elevation in the selected area
- lower elevations are rendered with colder colors
- higher elevations are rendered with warmer colors
- the layer is drawn on top of the GPKG orthophoto tiles and below the elevation markers

The layer can be turned on and off using a UI button.

Conclusion: the app can visually display terrain height variation over the selected orthophoto image.

## 21. Topographic Contour Overlay Bonus

A topographic contour overlay was generated from the exported DTM elevation window.

The contour lines were created during Python preprocessing and saved as `contour_overlay.png`.
The Android app loads this PNG from assets and can toggle it on and off over the orthophoto.

The contour layer is drawn above the orthophoto and elevation heatmap, but below the min/max elevation markers.

Conclusion: the app now supports a topographic map-style overlay using contour lines derived from the DTM.

## 22. Last Tap Marker

The Android app now draws a marker at the last tapped location on the map.

When the user taps the orthophoto:
- the screen position is converted to lon/lat
- the lon/lat is converted to a DTM elevation value
- the tapped point is drawn on the map
- the elevation value is displayed next to the marker

Conclusion: the touch-to-elevation feature is now visually clear in the app and easier to demonstrate.

## 23. Interactive Building Density and UI Improvements

The app now reports both global and local built-up density.

Global built-up density is calculated during preprocessing from the normalized RGB orthophoto pixels.
Local built-up density is calculated around the last tapped point using the building-density mask.

The last tapped point is now drawn on the map with a readable label showing:
- elevation
- local built-up density

The extrema marker display now supports three modes:
- representative
- raw
- off

This improves the demo experience by allowing the user to inspect the map without visual clutter.

## 24. Map Cropping and UI Polish

The Android map view was improved to display the actual orthophoto content bounds instead of the full tile-grid rectangle.

This removed unused white margins around the map and made the display cleaner.

The UI was also polished:
- the top status text was shortened and made user-facing
- extrema markers can now be shown as representative, raw, or turned off
- labels for extrema and tapped points are drawn with readable background boxes
- labels are constrained to remain

## 25. Improved Elevation Heatmap

The elevation layer visualization was improved by moving the heatmap rendering to Python preprocessing.

Instead of generating a basic red/blue heatmap inside Android, the app now loads a precomputed `elevation_heatmap_overlay.png` from assets.

The new heatmap uses a terrain-like color scale:
- dark green for lower elevations
- light green for low-to-mid elevations
- beige/light brown for mid elevations
- darker brown for higher elevations

Exact elevation values are still read from `elevation_window_int16.bin`, so the visual heatmap does not affect the tap-to-elevation calculation.

Conclusion: the app now provides a more natural and map-like elevation visualization while preserving accurate DTM-based elevation lookup.

### 26. Elevation Metadata Loading

Updated the Android app to read DTM window metadata from `elevation_window_metadata.json` instead of relying only on hardcoded constants. The app still keeps matching default values as fallback, but the runtime configuration now comes from the generated metadata file.