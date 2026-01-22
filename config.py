"""
Configuration settings for plantation soil analysis system.
Modify these parameters to analyze different locations or time periods.
"""

# =============================================================================
# LOCATION SETTINGS
# =============================================================================

# Target coordinates (latitude, longitude)
LATITUDE = -1.841927
LONGITUDE = -80.741419

# Buffer radius around coordinates in meters
BUFFER_RADIUS_M = 5000  # 1km radius

# =============================================================================
# DATE RANGE
# =============================================================================

# Analysis period (YYYY-MM-DD format)
START_DATE = "2025-10-22"
END_DATE = "2026-01-22"

# =============================================================================
# SENTINEL-2 SETTINGS
# =============================================================================

# Sentinel-2 collection ID (Surface Reflectance)
S2_COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"

# s2cloudless collection ID
S2_CLOUDLESS = "COPERNICUS/S2_CLOUD_PROBABILITY"

# Cloud probability threshold (0-100)
# Pixels with cloud probability above this are masked
CLOUD_PROBABILITY_THRESHOLD = 40

# Maximum scene cloud percentage to include in collection
MAX_SCENE_CLOUD_PERCENT = 70

# =============================================================================
# SENTINEL-1 SETTINGS (SAR backup)
# =============================================================================

# Sentinel-1 collection ID
S1_COLLECTION = "COPERNICUS/S1_GRD"

# Polarization bands to use
S1_POLARIZATION = ["VV", "VH"]

# =============================================================================
# COMPOSITE SETTINGS
# =============================================================================

# Composite method: "median", "mean", "min", "max", "percentile"
COMPOSITE_METHOD = "median"

# Percentile value (only used if COMPOSITE_METHOD is "percentile")
COMPOSITE_PERCENTILE = 50

# =============================================================================
# SOIL INDICES TO CALCULATE
# =============================================================================

# Available indices:
# - NDSI: Normalized Difference Soil Index
# - BI: Bare Soil Index
# - CI: Color Index
# - NDMI: Normalized Difference Moisture Index
# - BSI: Bare Soil Index (alternative formula)

SOIL_INDICES = ["NDSI", "BI", "CI", "NDMI", "BSI"]

# =============================================================================
# EXPORT SETTINGS
# =============================================================================

# Export destination: "drive", "cloud", "asset"
EXPORT_DESTINATION = "drive"

# Google Drive folder name (created if doesn't exist)
DRIVE_FOLDER = "plantation_prueba"

# Export file prefix
FILE_PREFIX = "manabi_coastal"

# Export scale in meters (resolution)
EXPORT_SCALE = 10  # Sentinel-2 native resolution

# Export format: "GeoTIFF"
EXPORT_FORMAT = "GeoTIFF"

# GeoTIFF compression: "LZW", "DEFLATE", "JPEG", or None
GEOTIFF_COMPRESSION = "LZW"

# Maximum pixels for export (GEE limit is 1e13)
MAX_PIXELS = 1e9

# =============================================================================
# VISUALIZATION SETTINGS
# =============================================================================

# RGB visualization bands for Sentinel-2
VIS_BANDS_RGB = ["B4", "B3", "B2"]  # True color
VIS_BANDS_AGRICULTURE = ["B8", "B4", "B3"]  # False color (vegetation)
VIS_BANDS_SOIL = ["B11", "B8", "B4"]  # SWIR composite (soil/geology)

# Visualization min/max values
VIS_MIN = 0
VIS_MAX = 3000

# =============================================================================
# BAND MAPPINGS
# =============================================================================

# Sentinel-2 band names for calculations
S2_BANDS = {
    "blue": "B2",
    "green": "B3",
    "red": "B4",
    "red_edge_1": "B5",
    "red_edge_2": "B6",
    "red_edge_3": "B7",
    "nir": "B8",
    "nir_narrow": "B8A",
    "swir_1": "B11",
    "swir_2": "B12",
}

# =============================================================================
# OPTIMIZED BAND SELECTIONS
# =============================================================================

# Core bands for soil analysis (best balance of resolution and information)
SOIL_ANALYSIS_BANDS = ["B2", "B3", "B4", "B8", "B11", "B12"]

# Full spectral export (all useful bands)
FULL_SPECTRAL_BANDS = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]

# High resolution only (10m bands)
HIGH_RES_BANDS = ["B2", "B3", "B4", "B8"]

# Band descriptions for reference
BAND_INFO = {
    "B2": {"name": "Blue", "resolution": 10, "use": "Soil discrimination, organic matter"},
    "B3": {"name": "Green", "resolution": 10, "use": "Color index, turbidity"},
    "B4": {"name": "Red", "resolution": 10, "use": "Soil/iron oxide, dead vegetation"},
    "B5": {"name": "Red Edge 1", "resolution": 20, "use": "Vegetation classification"},
    "B6": {"name": "Red Edge 2", "resolution": 20, "use": "Vegetation classification"},
    "B7": {"name": "Red Edge 3", "resolution": 20, "use": "Vegetation classification"},
    "B8": {"name": "NIR", "resolution": 10, "use": "Biomass, moisture, vegetation"},
    "B8A": {"name": "NIR Narrow", "resolution": 20, "use": "Vegetation classification"},
    "B11": {"name": "SWIR 1", "resolution": 20, "use": "Soil moisture, clay minerals"},
    "B12": {"name": "SWIR 2", "resolution": 20, "use": "Soil moisture, mineral content"},
}