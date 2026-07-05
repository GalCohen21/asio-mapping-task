package com.galcohen.asiomapping

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.math.min
import android.widget.Button
import android.view.MotionEvent
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.tan
import kotlin.math.max
import kotlin.math.roundToInt

private fun Context.dp(value: Int): Int {
    return (value * resources.displayMetrics.density).roundToInt()
}

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val layout = LinearLayout(this)
        layout.orientation = LinearLayout.VERTICAL

        val statusText = TextView(this)
        statusText.textSize = 16f
        statusText.setLineSpacing(0f, 1.05f)
        statusText.setPadding(
            this.dp(16),
            this.dp(40),
            this.dp(16),
            this.dp(10)
        )

        val mapView = TileOverviewView(this, statusText)

        val toggleButton = Button(this)
        toggleButton.text = "Extrema: Off"

        toggleButton.setOnClickListener {
            val newMode = mapView.toggleMarkerMode()

            toggleButton.text = when (newMode) {
                "representative" -> "Extrema: Representative"
                "raw" -> "Extrema: Raw"
                else -> "Extrema: Off"
            }
        }

        val elevationLayerButton = Button(this)
        elevationLayerButton.text = "Elevation Layer: Off"

        elevationLayerButton.setOnClickListener {
            val isEnabled = mapView.toggleElevationLayer()

            elevationLayerButton.text = if (isEnabled) {
                "Elevation Layer: On"
            } else {
                "Elevation Layer: Off"
            }
        }

        val contoursButton = Button(this)
        contoursButton.text = "Contours: Off"

        contoursButton.setOnClickListener {
            val isEnabled = mapView.toggleContourLayer()

            contoursButton.text = if (isEnabled) {
                "Contours: On"
            } else {
                "Contours: Off"
            }
        }

        val buildingDensityButton = Button(this)
        buildingDensityButton.text = "Built-up Density: Off"

        buildingDensityButton.setOnClickListener {
            val isEnabled = mapView.toggleBuildingDensityLayer()

            buildingDensityButton.text = if (isEnabled) {
                "Built-up Density: On"
            } else {
                "Built-up Density: Off"
            }
        }

        layout.addView(
            statusText,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        layout.addView(
            toggleButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        layout.addView(
            elevationLayerButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        layout.addView(
            contoursButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        layout.addView(
            buildingDensityButton,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
        )

        layout.addView(
            mapView,
            LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                0,
                1f
            )
        )

        setContentView(layout)
    }
}

class TileOverviewView(
    context: Context,
    private val statusText: TextView
) : View(context) {

    private data class Tile(
        val dx: Int,
        val dy: Int,
        val bitmap: Bitmap
    )

    private data class ElevationMarker(
        val type: String, // "min" or "max"
        val rank: Int,
        val elevation: Int,
        val lon: Double,
        val lat: Double
    )

    private data class MapLayoutInfo(
        val contentLeftPixel: Double,
        val contentTopPixel: Double,
        val contentRightPixel: Double,
        val contentBottomPixel: Double,
        val contentPixelWidth: Double,
        val contentPixelHeight: Double,
        val scale: Float,
        val drawnMapWidth: Float,
        val drawnMapHeight: Float,
        val leftOffset: Float,
        val topOffset: Float
    )

    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val tiles = mutableListOf<Tile>()
    private val markers = mutableListOf<ElevationMarker>()

    private var markerMode = "off"

    private var lastTapText = "Tap on the map to inspect a coordinate"

    private var lastTapLon: Double? = null
    private var lastTapLat: Double? = null
    private var lastTapElevation: Int? = null
    private var lastTapLocalBuildingDensity: Double? = null

    private var showElevationLayer = false
    private var elevationOverlayBitmap: Bitmap? = null

    private var showContourLayer = false
    private var contourOverlayBitmap: Bitmap? = null

    private var showBuildingDensityLayer = false
    private var buildingDensityOverlayBitmap: Bitmap? = null
    private var buildingDensityPercentage: Double? = null

    private val tileSize = 256

    // Overview zoom level.
    // At zoom 3, the actual available tiles are cols 0-5 and rows 0-2.
    private val zoomLevel = 3
    private val startCol = 0
    private val startRow = 0
    private val gridCols = 6
    private val gridRows = 3

    // Tile matrix metadata for zoom 3.
    // From gpkg_tile_matrix: zoom 3 has matrix width/height = 8 x 8.
    private val matrixWidth = 8
    private val matrixHeight = 8

    // From gpkg_tile_matrix_set
    private val matrixMinLon = 35.28
    private val matrixMinLat = 32.71101722095672
    private val matrixMaxLon = 35.45578150760521
    private val matrixMaxLat = 32.8868

    private var elevationWidth = 1058
    private var elevationHeight = 545
    private var noDataValue = -32768

    private var dtmOriginX = 474035.41821334185
    private var dtmOriginY = 3830701.5944371745
    private var dtmPixelSize = 10.0

    private var dtmWindowColOffset = 23924
    private var dtmWindowRowOffset = 18942
    private val contentMinLon = 35.28
    private val contentMinLat = 32.8397
    private val contentMaxLon = 35.3918
    private val contentMaxLat = 32.8868
    private var elevationData = ShortArray(0)

    init {
        isClickable = true
        isFocusable = true

        loadTiles()

        if (markerMode != "off") {
            loadMarkers(markerMode)
        }

        loadElevationMetadata()
        loadElevationWindow()
        loadContourOverlay()
        loadBuildingDensityAssets()
        updateStatusText()
    }

    fun toggleMarkerMode(): String {
        markerMode = when (markerMode) {
            "representative" -> "raw"
            "raw" -> "off"
            else -> "representative"
        }

        markers.clear()

        if (markerMode != "off") {
            loadMarkers(markerMode)
        }

        updateStatusText()
        invalidate()

        return markerMode
    }

    private fun loadTiles() {
        val gpkgFile = File(context.getExternalFilesDir(null), "Orthophoto.gpkg")

        if (!gpkgFile.exists()) {
            statusText.text = """
                Orthophoto.gpkg was not found.
                
                Expected path:
                ${gpkgFile.absolutePath}
            """.trimIndent()
            return
        }

        try {
            val db = SQLiteDatabase.openDatabase(
                gpkgFile.absolutePath,
                null,
                SQLiteDatabase.OPEN_READONLY
            )

            for (dy in 0 until gridRows) {
                for (dx in 0 until gridCols) {
                    val col = startCol + dx
                    val row = startRow + dy

                    val cursor = db.rawQuery(
                        """
                        SELECT tile_data
                        FROM SAKHNIN
                        WHERE zoom_level = ?
                          AND tile_column = ?
                          AND tile_row = ?
                        """.trimIndent(),
                        arrayOf(
                            zoomLevel.toString(),
                            col.toString(),
                            row.toString()
                        )
                    )

                    if (cursor.moveToFirst()) {
                        val tileBytes = cursor.getBlob(0)

                        val bitmap = BitmapFactory.decodeByteArray(
                            tileBytes,
                            0,
                            tileBytes.size
                        )

                        if (bitmap != null) {
                            tiles.add(Tile(dx, dy, bitmap))
                        }
                    }

                    cursor.close()
                }
            }

            db.close()

        } catch (e: Exception) {
            statusText.text = """
                Failed to load overview tiles from GPKG.
                
                Error:
                ${e.message}
            """.trimIndent()
        }
    }

    private fun loadMarkers(mode: String) {
        markers.clear()

        try {
            val jsonText = context.assets.open("elevation_extremes.json")
                .bufferedReader()
                .use { it.readText() }

            val root = JSONObject(jsonText)
            val selectedGroup = root.getJSONObject(mode)

            val minArray = selectedGroup.getJSONArray("min")
            val maxArray = selectedGroup.getJSONArray("max")

            addMarkersFromArray(minArray, "min")
            addMarkersFromArray(maxArray, "max")

        } catch (e: Exception) {
            statusText.text = """
                Failed to load elevation_extremes.json.
                
                Error:
                ${e.message}
            """.trimIndent()
        }
    }

    private fun loadElevationMetadata() {
        try {
            val jsonText = context.assets.open("elevation_window_metadata.json")
                .bufferedReader()
                .use { it.readText() }

            val json = JSONObject(jsonText)

            noDataValue = json.getDouble("nodata").toInt()

            val window = json.getJSONObject("window")
            dtmWindowColOffset = window.getInt("col_off")
            dtmWindowRowOffset = window.getInt("row_off")
            elevationWidth = window.getInt("width")
            elevationHeight = window.getInt("height")

            val transform = json.getJSONObject("dtm_transform")
            dtmOriginX = transform.getDouble("c_top_left_x")
            dtmOriginY = transform.getDouble("f_top_left_y")
            dtmPixelSize = kotlin.math.abs(transform.getDouble("a_pixel_width"))

        } catch (e: Exception) {
            // Keep the default hardcoded values if metadata loading fails.
            e.printStackTrace()
        }
    }

    private fun loadElevationWindow() {
        try {
            val bytes = context.assets.open("elevation_window_int16.bin").readBytes()

            val buffer = ByteBuffer
                .wrap(bytes)
                .order(ByteOrder.LITTLE_ENDIAN)

            elevationData = ShortArray(bytes.size / 2)

            for (i in elevationData.indices) {
                elevationData[i] = buffer.short
            }

            val loadedPrecomputedHeatmap = loadPrecomputedElevationHeatmap()

            if (!loadedPrecomputedHeatmap) {
                createElevationOverlayBitmap()
            }

        } catch (e: Exception) {
            lastTapText = """
            Failed to load elevation_window_int16.bin
            
            Error:
            ${e.message}
        """.trimIndent()
        }
    }

    private fun addMarkersFromArray(array: JSONArray, type: String) {
        for (i in 0 until array.length()) {
            val point = array.getJSONObject(i)

            markers.add(
                ElevationMarker(
                    type = type,
                    rank = i + 1,
                    elevation = point.getInt("elevation"),
                    lon = point.getDouble("lon"),
                    lat = point.getDouble("lat")
                )
            )
        }
    }

    private fun lonLatToLocalMapPixel(lon: Double, lat: Double): Pair<Double, Double> {
        val totalMatrixPixelWidth = (matrixWidth * tileSize).toDouble()
        val totalMatrixPixelHeight = (matrixHeight * tileSize).toDouble()

        val globalPixelX =
            ((lon - matrixMinLon) / (matrixMaxLon - matrixMinLon)) * totalMatrixPixelWidth

        val globalPixelY =
            ((matrixMaxLat - lat) / (matrixMaxLat - matrixMinLat)) * totalMatrixPixelHeight

        val localMapPixelX = globalPixelX - (startCol * tileSize).toDouble()
        val localMapPixelY = globalPixelY - (startRow * tileSize).toDouble()

        return Pair(localMapPixelX, localMapPixelY)
    }

    private fun calculateMapLayout(): MapLayoutInfo {
        val topLeft = lonLatToLocalMapPixel(
            lon = contentMinLon,
            lat = contentMaxLat
        )

        val bottomRight = lonLatToLocalMapPixel(
            lon = contentMaxLon,
            lat = contentMinLat
        )

        val contentLeftPixel = topLeft.first
        val contentTopPixel = topLeft.second
        val contentRightPixel = bottomRight.first
        val contentBottomPixel = bottomRight.second

        val contentPixelWidth = contentRightPixel - contentLeftPixel
        val contentPixelHeight = contentBottomPixel - contentTopPixel

        val scale = min(
            width.toFloat() / contentPixelWidth.toFloat(),
            height.toFloat() / contentPixelHeight.toFloat()
        )

        val drawnMapWidth = contentPixelWidth.toFloat() * scale
        val drawnMapHeight = contentPixelHeight.toFloat() * scale

        val leftOffset = (width - drawnMapWidth) / 2f

        val verticalFreeSpace = height - drawnMapHeight
        val topOffset = min(
            20f * resources.displayMetrics.density,
            verticalFreeSpace / 2f
        )

        return MapLayoutInfo(
            contentLeftPixel = contentLeftPixel,
            contentTopPixel = contentTopPixel,
            contentRightPixel = contentRightPixel,
            contentBottomPixel = contentBottomPixel,
            contentPixelWidth = contentPixelWidth,
            contentPixelHeight = contentPixelHeight,
            scale = scale,
            drawnMapWidth = drawnMapWidth,
            drawnMapHeight = drawnMapHeight,
            leftOffset = leftOffset,
            topOffset = topOffset
        )
    }

    private fun lonLatToScreen(
        lon: Double,
        lat: Double,
        mapLayout: MapLayoutInfo
    ): Pair<Float, Float> {
        val localMapPixel = lonLatToLocalMapPixel(lon, lat)

        val screenX =
            mapLayout.leftOffset +
                    (localMapPixel.first - mapLayout.contentLeftPixel).toFloat() * mapLayout.scale

        val screenY =
            mapLayout.topOffset +
                    (localMapPixel.second - mapLayout.contentTopPixel).toFloat() * mapLayout.scale

        return Pair(screenX, screenY)
    }

    private fun handleMapTap(tapX: Float, tapY: Float) {
        val mapLayout = calculateMapLayout()

        val scale = mapLayout.scale
        val drawnMapWidth = mapLayout.drawnMapWidth
        val drawnMapHeight = mapLayout.drawnMapHeight
        val leftOffset = mapLayout.leftOffset
        val topOffset = mapLayout.topOffset

        // Check if the tap is inside the drawn map rectangle
        if (
            tapX < leftOffset ||
            tapX > leftOffset + drawnMapWidth ||
            tapY < topOffset ||
            tapY > topOffset + drawnMapHeight
        ) {
            lastTapText = "Tap is outside the map"
            lastTapLon = null
            lastTapLat = null
            lastTapElevation = null
            lastTapLocalBuildingDensity = null
            updateStatusText()
            return
        }

        // Screen coordinate -> local pixel inside the displayed content crop
        val localContentPixelX = (tapX - leftOffset) / scale
        val localContentPixelY = (tapY - topOffset) / scale

// Add the crop offset to get the local pixel inside the original tile grid
        val localMapPixelX = mapLayout.contentLeftPixel + localContentPixelX
        val localMapPixelY = mapLayout.contentTopPixel + localContentPixelY

// Local tile-grid pixel -> global tile-matrix pixel
        val globalPixelX = (startCol * tileSize).toDouble() + localMapPixelX
        val globalPixelY = (startRow * tileSize).toDouble() + localMapPixelY

        val totalMatrixPixelWidth = (matrixWidth * tileSize).toDouble()
        val totalMatrixPixelHeight = (matrixHeight * tileSize).toDouble()

        // Global tile-matrix pixel -> lon/lat
        val lon =
            matrixMinLon +
                    (globalPixelX / totalMatrixPixelWidth) *
                    (matrixMaxLon - matrixMinLon)

        val lat =
            matrixMaxLat -
                    (globalPixelY / totalMatrixPixelHeight) *
                    (matrixMaxLat - matrixMinLat)

        val elevation = getElevationForLonLat(lon, lat)
        val localBuildingDensity = getLocalBuildingDensityForLonLat(lon, lat)

        lastTapLon = lon
        lastTapLat = lat
        lastTapElevation = elevation
        lastTapLocalBuildingDensity = localBuildingDensity

        val elevationText = if (elevation != null) {
            "${elevation}m"
        } else {
            "not available"
        }

        val localDensityText = if (localBuildingDensity != null) {
            "${"%.2f".format(localBuildingDensity)}%"
        } else {
            "not available"
        }

        lastTapText = """
            Last tap:
            lon = ${"%.6f".format(lon)}
            lat = ${"%.6f".format(lat)}
            elevation = $elevationText
            local built-up density = $localDensityText
        """.trimIndent()

        updateStatusText()
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)

        canvas.drawColor(Color.WHITE)

        if (tiles.isEmpty()) {
            paint.color = Color.RED
            paint.textSize = 40f
            canvas.drawText("No tiles loaded", 40f, 80f, paint)
            return
        }

        val mapLayout = calculateMapLayout()

        val mapRect = RectF(
            mapLayout.leftOffset,
            mapLayout.topOffset,
            mapLayout.leftOffset + mapLayout.drawnMapWidth,
            mapLayout.topOffset + mapLayout.drawnMapHeight
        )

        canvas.save()
        canvas.clipRect(mapRect)

        // Draw tiles, cropped to the actual orthophoto content bounds
        for (tile in tiles) {
            val left =
                mapLayout.leftOffset +
                        (tile.dx * tileSize - mapLayout.contentLeftPixel).toFloat() * mapLayout.scale

            val top =
                mapLayout.topOffset +
                        (tile.dy * tileSize - mapLayout.contentTopPixel).toFloat() * mapLayout.scale

            val right = left + tileSize * mapLayout.scale
            val bottom = top + tileSize * mapLayout.scale

            val destination = RectF(left, top, right, bottom)

            canvas.drawBitmap(tile.bitmap, null, destination, paint)
        }

        canvas.restore()

        if (showElevationLayer && elevationOverlayBitmap != null) {
            canvas.drawBitmap(
                elevationOverlayBitmap!!,
                null,
                mapRect,
                paint
            )
        }

        if (showBuildingDensityLayer && buildingDensityOverlayBitmap != null) {
            canvas.drawBitmap(
                buildingDensityOverlayBitmap!!,
                null,
                mapRect,
                paint
            )
        }

        if (showContourLayer && contourOverlayBitmap != null) {
            canvas.drawBitmap(
                contourOverlayBitmap!!,
                null,
                mapRect,
                paint
            )
        }

        // Draw min/max markers
        for (marker in markers) {
            val color = if (marker.type == "max") {
                Color.RED
            } else {
                Color.BLUE
            }

            drawMarkerForLonLat(
                canvas = canvas,
                lon = marker.lon,
                lat = marker.lat,
                label = "${marker.elevation}m",
                color = color,
                mapLayout = mapLayout,
                mapRect = mapRect
            )
        }

        // Draw last tapped point
        if (lastTapLon != null && lastTapLat != null) {
            val tapScreenPoint = lonLatToScreen(
                lon = lastTapLon!!,
                lat = lastTapLat!!,
                mapLayout = mapLayout
            )

            val tapX = tapScreenPoint.first
            val tapY = tapScreenPoint.second

            paint.style = Paint.Style.FILL
            paint.color = Color.YELLOW
            canvas.drawCircle(tapX, tapY, 16f, paint)

            paint.style = Paint.Style.STROKE
            paint.strokeWidth = 4f
            paint.color = Color.BLACK
            canvas.drawCircle(tapX, tapY, 16f, paint)

            val elevationLabel = if (lastTapElevation != null) {
                "${lastTapElevation}m"
            } else {
                "N/A"
            }

            val densityLabel = if (lastTapLocalBuildingDensity != null) {
                "${"%.1f".format(lastTapLocalBuildingDensity)}%"
            } else {
                null
            }

            val label = if (densityLabel != null) {
                "$elevationLabel | $densityLabel"
            } else {
                elevationLabel
            }

            drawLabelBox(
                canvas = canvas,
                text = label,
                x = tapX + 20f,
                y = tapY - 16f,
                backgroundColor = Color.rgb(255, 232, 150),
                textColor = Color.BLACK,
                bounds = mapRect
            )
        }

        // Draw border around actual orthophoto content
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 3f
        paint.color = Color.BLACK
        canvas.drawRect(mapRect, paint)

        paint.style = Paint.Style.FILL
    }

    private fun drawMarkerForLonLat(
        canvas: Canvas,
        lon: Double,
        lat: Double,
        label: String,
        color: Int,
        mapLayout: MapLayoutInfo,
        mapRect: RectF
    ) {
        val screenPoint = lonLatToScreen(
            lon = lon,
            lat = lat,
            mapLayout = mapLayout
        )

        val screenX = screenPoint.first
        val screenY = screenPoint.second

        paint.style = Paint.Style.FILL
        paint.color = color
        canvas.drawCircle(screenX, screenY, 14f, paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 4f
        paint.color = Color.WHITE
        canvas.drawCircle(screenX, screenY, 14f, paint)

        val labelBackgroundColor = if (color == Color.RED) {
            Color.rgb(255, 220, 220)
        } else {
            Color.rgb(215, 225, 255)
        }

        drawLabelBox(
            canvas = canvas,
            text = label,
            x = screenX + 20f,
            y = screenY - 16f,
            backgroundColor = labelBackgroundColor,
            textColor = Color.BLACK,
            bounds = mapRect
        )
    }

    private fun updateStatusText() {
        val globalDensityText = if (buildingDensityPercentage != null) {
            "${"%.2f".format(buildingDensityPercentage)}%"
        } else {
            "not available"
        }

        val elevationLayerText = if (showElevationLayer) "On" else "Off"
        val contourLayerText = if (showContourLayer) "On" else "Off"
        val builtUpLayerText = if (showBuildingDensityLayer) "On" else "Off"

        val extremaText = when (markerMode) {
            "representative" -> "Representative"
            "raw" -> "Raw"
            else -> "Off"
        }

        val tapSummary = if (lastTapElevation != null || lastTapLocalBuildingDensity != null) {
            val elevationText = if (lastTapElevation != null) {
                "${lastTapElevation}m"
            } else {
                "N/A"
            }

            val localDensityText = if (lastTapLocalBuildingDensity != null) {
                "${"%.2f".format(lastTapLocalBuildingDensity)}%"
            } else {
                "N/A"
            }

            "Tap: elevation $elevationText | local built-up $localDensityText"
        } else {
            "Tap on the map to inspect elevation and local built-up density"
        }

        statusText.text = """
            Extrema: $extremaText | Elevation: $elevationLayerText | Contours: $contourLayerText | Built-up: $builtUpLayerText
            Global built-up density: $globalDensityText
            $tapSummary
        """.trimIndent()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.action == MotionEvent.ACTION_DOWN) {
            performClick()
            handleMapTap(event.x, event.y)
            return true
        }

        return true
    }

    override fun performClick(): Boolean {
        super.performClick()
        return true
    }

    private fun lonLatToUtm36N(lon: Double, lat: Double): Pair<Double, Double> {
        // WGS84 constants
        val a = 6378137.0
        val f = 1.0 / 298.257223563
        val k0 = 0.9996

        val eSq = f * (2.0 - f)
        val ePrimeSq = eSq / (1.0 - eSq)

        val latRad = Math.toRadians(lat)
        val lonRad = Math.toRadians(lon)

        // UTM zone 36 central meridian is 33 degrees east
        val lonOriginRad = Math.toRadians(33.0)

        val sinLat = sin(latRad)
        val cosLat = cos(latRad)
        val tanLat = tan(latRad)

        val n = a / sqrt(1.0 - eSq * sinLat * sinLat)
        val t = tanLat * tanLat
        val c = ePrimeSq * cosLat * cosLat
        val aTerm = cosLat * (lonRad - lonOriginRad)

        val eSq2 = eSq * eSq
        val eSq3 = eSq2 * eSq

        val m = a * (
                (1.0 - eSq / 4.0 - 3.0 * eSq2 / 64.0 - 5.0 * eSq3 / 256.0) * latRad
                        - (3.0 * eSq / 8.0 + 3.0 * eSq2 / 32.0 + 45.0 * eSq3 / 1024.0) * sin(2.0 * latRad)
                        + (15.0 * eSq2 / 256.0 + 45.0 * eSq3 / 1024.0) * sin(4.0 * latRad)
                        - (35.0 * eSq3 / 3072.0) * sin(6.0 * latRad)
                )

        val easting = 500000.0 + k0 * n * (
                aTerm
                        + (1.0 - t + c) * aTerm * aTerm * aTerm / 6.0
                        + (5.0 - 18.0 * t + t * t + 72.0 * c - 58.0 * ePrimeSq) *
                        aTerm * aTerm * aTerm * aTerm * aTerm / 120.0
                )

        val northing = k0 * (
                m + n * tanLat * (
                        aTerm * aTerm / 2.0
                                + (5.0 - t + 9.0 * c + 4.0 * c * c) *
                                aTerm * aTerm * aTerm * aTerm / 24.0
                                + (61.0 - 58.0 * t + t * t + 600.0 * c - 330.0 * ePrimeSq) *
                                aTerm * aTerm * aTerm * aTerm * aTerm * aTerm / 720.0
                        )
                )

        return Pair(easting, northing)
    }

    private fun getElevationForLonLat(lon: Double, lat: Double): Int? {
        if (elevationData.isEmpty()) {
            return null
        }

        val (x, y) = lonLatToUtm36N(lon, lat)

        val absoluteCol = floor((x - dtmOriginX) / dtmPixelSize).toInt()
        val absoluteRow = floor((dtmOriginY - y) / dtmPixelSize).toInt()

        val localCol = absoluteCol - dtmWindowColOffset
        val localRow = absoluteRow - dtmWindowRowOffset

        if (
            localCol < 0 ||
            localCol >= elevationWidth ||
            localRow < 0 ||
            localRow >= elevationHeight
        ) {
            return null
        }

        val index = localRow * elevationWidth + localCol
        val elevation = elevationData[index].toInt()

        if (elevation == noDataValue) {
            return null
        }

        return elevation
    }

    fun toggleElevationLayer(): Boolean {
        showElevationLayer = !showElevationLayer

        updateStatusText()
        invalidate()

        return showElevationLayer
    }

    private fun createElevationOverlayBitmap() {
        if (elevationData.isEmpty()) {
            return
        }

        var minElevation = Int.MAX_VALUE
        var maxElevation = Int.MIN_VALUE

        for (value in elevationData) {
            val elevation = value.toInt()

            if (elevation != noDataValue) {
                if (elevation < minElevation) {
                    minElevation = elevation
                }

                if (elevation > maxElevation) {
                    maxElevation = elevation
                }
            }
        }

        if (
            minElevation == Int.MAX_VALUE ||
            maxElevation == Int.MIN_VALUE ||
            minElevation == maxElevation
        ) {
            return
        }

        val pixels = IntArray(elevationWidth * elevationHeight)

        for (i in elevationData.indices) {
            val elevation = elevationData[i].toInt()

            if (elevation == noDataValue) {
                pixels[i] = Color.TRANSPARENT
            } else {
                val t =
                    ((elevation - minElevation).toDouble() /
                            (maxElevation - minElevation).toDouble())
                        .coerceIn(0.0, 1.0)

                val red = (255 * t).toInt()
                val green = 60
                val blue = (255 * (1.0 - t)).toInt()

                // Semi-transparent heatmap color
                pixels[i] = Color.argb(
                    120,
                    red,
                    green,
                    blue
                )
            }
        }

        elevationOverlayBitmap = Bitmap.createBitmap(
            pixels,
            elevationWidth,
            elevationHeight,
            Bitmap.Config.ARGB_8888
        )
    }

    private fun loadContourOverlay() {
        try {
            val inputStream = context.assets.open("contour_overlay.png")
            contourOverlayBitmap = BitmapFactory.decodeStream(inputStream)
            inputStream.close()

        } catch (e: Exception) {
            lastTapText = """
                Failed to load contour_overlay.png
                
                Error:
                ${e.message}
            """.trimIndent()
        }
    }

    fun toggleContourLayer(): Boolean {
        showContourLayer = !showContourLayer

        updateStatusText()
        invalidate()

        return showContourLayer
    }

    private fun loadBuildingDensityAssets() {
        try {
            val overlayInputStream = context.assets.open("building_density_overlay.png")
            buildingDensityOverlayBitmap = BitmapFactory.decodeStream(overlayInputStream)
            overlayInputStream.close()

            val summaryText = context.assets.open("building_density_summary.json")
                .bufferedReader()
                .use { it.readText() }

            val summaryJson = JSONObject(summaryText)
            buildingDensityPercentage = summaryJson.getDouble("density_percentage")

        } catch (e: Exception) {
            lastTapText = """
            Failed to load building density assets
            
            Error:
            ${e.message}
        """.trimIndent()
        }
    }

    fun toggleBuildingDensityLayer(): Boolean {
        showBuildingDensityLayer = !showBuildingDensityLayer

        updateStatusText()
        invalidate()

        return showBuildingDensityLayer
    }

    private fun getLocalBuildingDensityForLonLat(lon: Double, lat: Double): Double? {
        val bitmap = buildingDensityOverlayBitmap ?: return null

        if (
            lon < contentMinLon ||
            lon > contentMaxLon ||
            lat < contentMinLat ||
            lat > contentMaxLat
        ) {
            return null
        }

        val bitmapX =
            ((lon - contentMinLon) / (contentMaxLon - contentMinLon) * (bitmap.width - 1))
                .roundToInt()

        val bitmapY =
            ((contentMaxLat - lat) / (contentMaxLat - contentMinLat) * (bitmap.height - 1))
                .roundToInt()

        val radiusPixels = 35

        val startX = max(0, bitmapX - radiusPixels)
        val endX = min(bitmap.width - 1, bitmapX + radiusPixels)

        val startY = max(0, bitmapY - radiusPixels)
        val endY = min(bitmap.height - 1, bitmapY + radiusPixels)

        var totalPixels = 0
        var builtUpPixels = 0

        for (y in startY..endY) {
            for (x in startX..endX) {
                val pixel = bitmap.getPixel(x, y)
                val alpha = Color.alpha(pixel)

                totalPixels += 1

                if (alpha > 0) {
                    builtUpPixels += 1
                }
            }
        }

        if (totalPixels == 0) {
            return null
        }

        return builtUpPixels.toDouble() / totalPixels.toDouble() * 100.0
    }

    private fun drawLabelBox(
        canvas: Canvas,
        text: String,
        x: Float,
        y: Float,
        backgroundColor: Int,
        textColor: Int,
        bounds: RectF? = null
    ) {
        paint.style = Paint.Style.FILL
        paint.isAntiAlias = true
        paint.textSize = 26f
        paint.typeface = android.graphics.Typeface.create(
            android.graphics.Typeface.DEFAULT,
            android.graphics.Typeface.BOLD
        )

        val paddingX = 8f
        val paddingY = 5f
        val margin = 6f

        val textWidth = paint.measureText(text)
        val fontMetrics = paint.fontMetrics

        fun createRect(labelX: Float, labelY: Float): RectF {
            return RectF(
                labelX - paddingX,
                labelY + fontMetrics.ascent - paddingY,
                labelX + textWidth + paddingX,
                labelY + fontMetrics.descent + paddingY
            )
        }

        var finalX = x
        var finalY = y
        var rect = createRect(finalX, finalY)

        if (bounds != null) {
            // If the label goes beyond the right edge, move it left.
            if (rect.right > bounds.right - margin) {
                finalX -= rect.right - (bounds.right - margin)
                rect = createRect(finalX, finalY)
            }

            // If the label goes beyond the left edge, move it right.
            if (rect.left < bounds.left + margin) {
                finalX += (bounds.left + margin) - rect.left
                rect = createRect(finalX, finalY)
            }

            // If the label goes beyond the top edge, move it down.
            if (rect.top < bounds.top + margin) {
                finalY += (bounds.top + margin) - rect.top
                rect = createRect(finalX, finalY)
            }

            // If the label goes beyond the bottom edge, move it up.
            if (rect.bottom > bounds.bottom - margin) {
                finalY -= rect.bottom - (bounds.bottom - margin)
                rect = createRect(finalX, finalY)
            }
        }

        paint.color = backgroundColor
        canvas.drawRoundRect(rect, 6f, 6f, paint)

        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 1.5f
        paint.color = Color.rgb(80, 80, 80)
        canvas.drawRoundRect(rect, 6f, 6f, paint)

        paint.style = Paint.Style.FILL
        paint.color = textColor
        canvas.drawText(text, finalX, finalY, paint)

        paint.typeface = android.graphics.Typeface.DEFAULT
    }

    private fun loadPrecomputedElevationHeatmap(): Boolean {
        return try {
            val inputStream = context.assets.open("elevation_heatmap_overlay.png")
            elevationOverlayBitmap = BitmapFactory.decodeStream(inputStream)
            inputStream.close()

            elevationOverlayBitmap != null

        } catch (e: Exception) {
            false
        }
    }
}