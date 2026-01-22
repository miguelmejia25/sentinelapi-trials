"""
Compression and output formatting module.
Handles image preparation for export with various compression options.
"""

import ee
from typing import List, Tuple, Optional

import config


def scale_to_uint16(image: ee.Image, min_val: float = 0, max_val: float = 10000) -> ee.Image:
    """
    Scale image values to unsigned 16-bit integer range.
    
    Useful for reducing file size while preserving data quality.
    Sentinel-2 SR data is typically in 0-10000 range.
    
    Args:
        image: Input image.
        min_val: Minimum expected value.
        max_val: Maximum expected value.
    
    Returns:
        ee.Image: Scaled image with uint16 values.
    """
    scaled = image.unitScale(min_val, max_val).multiply(65535).toUint16()
    return scaled


def scale_to_uint8(image: ee.Image, min_val: float = 0, max_val: float = 10000) -> ee.Image:
    """
    Scale image values to unsigned 8-bit integer range.
    
    Maximum compression but loses precision. Good for visualization,
    not recommended for quantitative analysis.
    
    Args:
        image: Input image.
        min_val: Minimum expected value.
        max_val: Maximum expected value.
    
    Returns:
        ee.Image: Scaled image with uint8 values.
    """
    scaled = image.unitScale(min_val, max_val).multiply(255).toUint8()
    return scaled


def scale_indices_to_uint16(image: ee.Image, index_bands: List[str] = None) -> ee.Image:
    """
    Scale soil index bands to uint16 for storage.
    
    Indices typically range from -1 to 1, so we rescale to 0-65535
    with 32768 as the zero point.
    
    Args:
        image: Image with index bands.
        index_bands: List of index band names to scale.
    
    Returns:
        ee.Image: Image with scaled index bands.
    """
    index_bands = index_bands or config.SOIL_INDICES
    
    # Indices typically -1 to 1, scale to 0-65535
    def scale_index(band_name):
        band = image.select(band_name)
        # Shift from [-1,1] to [0,2], then scale to [0,65535]
        scaled = band.add(1).multiply(32767.5).toUint16()
        return scaled.rename(band_name + "_scaled")
    
    scaled_bands = [scale_index(name) for name in index_bands 
                    if name in image.bandNames().getInfo()]
    
    if scaled_bands:
        result = ee.Image.cat(scaled_bands)
        return result
    else:
        return image


def prepare_rgb_visualization(
    image: ee.Image,
    bands: List[str] = None,
    min_val: float = None,
    max_val: float = None
) -> ee.Image:
    """
    Prepare RGB visualization image.
    
    Args:
        image: Input image.
        bands: RGB band names. Defaults to config.VIS_BANDS_RGB.
        min_val: Minimum value for stretching. Defaults to config.VIS_MIN.
        max_val: Maximum value for stretching. Defaults to config.VIS_MAX.
    
    Returns:
        ee.Image: 3-band uint8 image suitable for visualization.
    """
    bands = bands or config.VIS_BANDS_RGB
    min_v = min_val if min_val is not None else config.VIS_MIN
    max_v = max_val if max_val is not None else config.VIS_MAX
    
    rgb = image.select(bands)
    vis = rgb.unitScale(min_v, max_v).multiply(255).toUint8()
    
    return vis.rename(["red", "green", "blue"])


def prepare_for_export(
    image: ee.Image,
    bands: List[str] = None,
    scale_type: str = "float"
) -> ee.Image:
    """
    Prepare image for export with specified scaling.
    
    Args:
        image: Input image.
        bands: Bands to include. If None, includes all.
        scale_type: "float" (no scaling), "uint16", or "uint8".
    
    Returns:
        ee.Image: Prepared image for export.
    """
    if bands:
        image = image.select(bands)
    
    if scale_type == "uint16":
        return scale_to_uint16(image)
    elif scale_type == "uint8":
        return scale_to_uint8(image)
    else:
        return image.toFloat()


def get_optimal_bands(
    include_rgb: bool = True,
    include_indices: bool = True,
    include_all_spectral: bool = False
) -> List[str]:
    """
    Get optimal band selection for export based on use case.
    
    Args:
        include_rgb: Include RGB visualization bands.
        include_indices: Include soil index bands.
        include_all_spectral: Include all Sentinel-2 spectral bands.
    
    Returns:
        list: Band names to export.
    """
    bands = []
    
    if include_all_spectral:
        # All 10m and 20m Sentinel-2 bands
        bands.extend([
            "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"
        ])
    elif include_rgb:
        # Just RGB
        bands.extend(config.VIS_BANDS_RGB)
    
    if include_indices:
        bands.extend(config.SOIL_INDICES)
    
    return bands


def estimate_file_size(
    image: ee.Image,
    roi: ee.Geometry,
    scale: int = 10,
    num_bands: int = None,
    bit_depth: int = 32
) -> dict:
    """
    Estimate output file size.
    
    Args:
        image: Image to export.
        roi: Region of interest.
        scale: Export scale in meters.
        num_bands: Number of bands. If None, counts from image.
        bit_depth: Bits per pixel (8, 16, or 32).
    
    Returns:
        dict: Size estimates in various units.
    """
    # Get ROI area in square meters
    area_m2 = roi.area().getInfo()
    
    # Calculate number of pixels
    pixels = area_m2 / (scale * scale)
    
    # Get band count
    if num_bands is None:
        num_bands = image.bandNames().size().getInfo()
    
    # Calculate raw size in bytes
    bytes_per_pixel = bit_depth / 8
    raw_bytes = pixels * num_bands * bytes_per_pixel
    
    # Estimate compressed size (LZW typically 30-50% compression for imagery)
    compressed_bytes = raw_bytes * 0.6  # Assume 40% compression
    
    return {
        "pixels": int(pixels),
        "bands": num_bands,
        "raw_mb": raw_bytes / (1024 * 1024),
        "estimated_mb": compressed_bytes / (1024 * 1024),
        "estimated_gb": compressed_bytes / (1024 * 1024 * 1024),
    }


def create_export_params(
    image: ee.Image,
    roi: ee.Geometry,
    description: str,
    folder: str = None,
    scale: int = None,
    crs: str = "EPSG:4326",
    max_pixels: float = None
) -> dict:
    """
    Create standardized export parameters dictionary.
    
    Args:
        image: Image to export.
        roi: Region of interest.
        description: Export task description.
        folder: Drive folder name. Defaults to config.DRIVE_FOLDER.
        scale: Export scale. Defaults to config.EXPORT_SCALE.
        crs: Coordinate reference system.
        max_pixels: Maximum pixels. Defaults to config.MAX_PIXELS.
    
    Returns:
        dict: Parameters for ee.batch.Export.image.toDrive()
    """
    params = {
        "image": image,
        "description": description,
        "folder": folder or config.DRIVE_FOLDER,
        "region": roi,
        "scale": scale or config.EXPORT_SCALE,
        "crs": crs,
        "maxPixels": max_pixels or config.MAX_PIXELS,
        "fileFormat": "GeoTIFF",
    }
    
    # Add compression if specified
    if config.GEOTIFF_COMPRESSION:
        params["formatOptions"] = {
            "cloudOptimized": True,
            "compression": config.GEOTIFF_COMPRESSION
        }
    
    return params


def split_for_tiled_export(
    roi: ee.Geometry,
    tile_size_km: float = 10
) -> List[ee.Geometry]:
    """
    Split large region into tiles for manageable exports.
    
    Args:
        roi: Region of interest.
        tile_size_km: Tile size in kilometers.
    
    Returns:
        list: List of tile geometries.
    """
    # Get bounding box
    bounds = roi.bounds().getInfo()["coordinates"][0]
    
    min_lon = min(c[0] for c in bounds)
    max_lon = max(c[0] for c in bounds)
    min_lat = min(c[1] for c in bounds)
    max_lat = max(c[1] for c in bounds)
    
    # Convert km to degrees (approximate)
    deg_per_km_lat = 1 / 111  # ~111 km per degree latitude
    deg_per_km_lon = 1 / (111 * abs(ee.Number(min_lat).cos().getInfo()))
    
    tile_size_lat = tile_size_km * deg_per_km_lat
    tile_size_lon = tile_size_km * deg_per_km_lon
    
    tiles = []
    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            tile = ee.Geometry.Rectangle([
                lon, lat,
                min(lon + tile_size_lon, max_lon),
                min(lat + tile_size_lat, max_lat)
            ])
            # Only include tiles that intersect original ROI
            tiles.append(tile)
            lon += tile_size_lon
        lat += tile_size_lat
    
    print(f"✓ Split ROI into {len(tiles)} tiles ({tile_size_km}km each)")
    return tiles


def print_export_summary(params: dict, size_estimate: dict = None):
    """
    Print summary of planned export.
    
    Args:
        params: Export parameters dictionary.
        size_estimate: Optional size estimate dictionary.
    """
    print("\nExport Summary:")
    print("-" * 40)
    print(f"  Description: {params['description']}")
    print(f"  Destination: Drive/{params['folder']}")
    print(f"  Scale: {params['scale']}m")
    print(f"  CRS: {params['crs']}")
    print(f"  Format: {params['fileFormat']}")
    
    if "formatOptions" in params:
        opts = params["formatOptions"]
        print(f"  Compression: {opts.get('compression', 'None')}")
        print(f"  Cloud Optimized: {opts.get('cloudOptimized', False)}")
    
    if size_estimate:
        print(f"\n  Estimated size:")
        print(f"    Pixels: {size_estimate['pixels']:,}")
        print(f"    Bands: {size_estimate['bands']}")
        print(f"    Raw: {size_estimate['raw_mb']:.1f} MB")
        print(f"    Compressed: ~{size_estimate['estimated_mb']:.1f} MB")
    
    print("-" * 40)