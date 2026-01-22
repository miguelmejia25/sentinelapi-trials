"""
Satellite imagery retrieval module.
Handles fetching Sentinel-2 and Sentinel-1 collections from GEE.
"""

import ee
from typing import Tuple, Optional

import config


def create_region_of_interest(
    latitude: float = None,
    longitude: float = None,
    buffer_m: int = None
) -> ee.Geometry:
    """
    Create a circular region of interest around given coordinates.
    
    Args:
        latitude: Center latitude. Defaults to config.LATITUDE.
        longitude: Center longitude. Defaults to config.LONGITUDE.
        buffer_m: Buffer radius in meters. Defaults to config.BUFFER_RADIUS_M.
    
    Returns:
        ee.Geometry: Circular geometry for the ROI.
    """
    lat = latitude or config.LATITUDE
    lon = longitude or config.LONGITUDE
    buffer = buffer_m or config.BUFFER_RADIUS_M
    
    point = ee.Geometry.Point([lon, lat])
    roi = point.buffer(buffer)
    
    print(f"✓ Created ROI: center ({lat}, {lon}), radius {buffer}m")
    return roi


def create_bbox_roi(
    min_lon: float,
    min_lat: float,
    max_lon: float,
    max_lat: float
) -> ee.Geometry:
    """
    Create a rectangular region of interest from bounding box.
    
    Args:
        min_lon: Western boundary longitude.
        min_lat: Southern boundary latitude.
        max_lon: Eastern boundary longitude.
        max_lat: Northern boundary latitude.
    
    Returns:
        ee.Geometry: Rectangle geometry for the ROI.
    """
    roi = ee.Geometry.Rectangle([min_lon, min_lat, max_lon, max_lat])
    print(f"✓ Created bbox ROI: [{min_lon}, {min_lat}, {max_lon}, {max_lat}]")
    return roi


def get_sentinel2_collection(
    roi: ee.Geometry,
    start_date: str = None,
    end_date: str = None,
    max_cloud_percent: int = None
) -> Tuple[ee.ImageCollection, int]:
    """
    Retrieve Sentinel-2 Surface Reflectance collection.
    
    Args:
        roi: Region of interest geometry.
        start_date: Start date (YYYY-MM-DD). Defaults to config.START_DATE.
        end_date: End date (YYYY-MM-DD). Defaults to config.END_DATE.
        max_cloud_percent: Maximum cloud cover percentage. 
                          Defaults to config.MAX_SCENE_CLOUD_PERCENT.
    
    Returns:
        Tuple of (ee.ImageCollection, image_count)
    """
    start = start_date or config.START_DATE
    end = end_date or config.END_DATE
    max_cloud = max_cloud_percent or config.MAX_SCENE_CLOUD_PERCENT
    
    collection = (
        ee.ImageCollection(config.S2_COLLECTION)
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
    )
    
    # Get image count
    count = collection.size().getInfo()
    
    print(f"✓ Retrieved Sentinel-2 collection")
    print(f"  Date range: {start} to {end}")
    print(f"  Max cloud cover: {max_cloud}%")
    print(f"  Images found: {count}")
    
    return collection, count


def get_s2_cloudless_collection(
    roi: ee.Geometry,
    start_date: str = None,
    end_date: str = None
) -> ee.ImageCollection:
    """
    Retrieve s2cloudless cloud probability collection.
    
    This collection provides cloud probability masks that align with
    Sentinel-2 imagery for improved cloud masking.
    
    Args:
        roi: Region of interest geometry.
        start_date: Start date (YYYY-MM-DD). Defaults to config.START_DATE.
        end_date: End date (YYYY-MM-DD). Defaults to config.END_DATE.
    
    Returns:
        ee.ImageCollection: Cloud probability collection.
    """
    start = start_date or config.START_DATE
    end = end_date or config.END_DATE
    
    collection = (
        ee.ImageCollection(config.S2_CLOUDLESS)
        .filterBounds(roi)
        .filterDate(start, end)
    )
    
    count = collection.size().getInfo()
    print(f"✓ Retrieved s2cloudless collection: {count} images")
    
    return collection


def get_sentinel1_collection(
    roi: ee.Geometry,
    start_date: str = None,
    end_date: str = None,
    orbit_pass: str = "DESCENDING"
) -> Tuple[ee.ImageCollection, int]:
    """
    Retrieve Sentinel-1 SAR GRD collection.
    
    Sentinel-1 provides radar imagery that penetrates clouds,
    useful as a backup when optical imagery is unavailable.
    
    Args:
        roi: Region of interest geometry.
        start_date: Start date (YYYY-MM-DD). Defaults to config.START_DATE.
        end_date: End date (YYYY-MM-DD). Defaults to config.END_DATE.
        orbit_pass: "ASCENDING" or "DESCENDING". Affects viewing geometry.
    
    Returns:
        Tuple of (ee.ImageCollection, image_count)
    """
    start = start_date or config.START_DATE
    end = end_date or config.END_DATE
    
    collection = (
        ee.ImageCollection(config.S1_COLLECTION)
        .filterBounds(roi)
        .filterDate(start, end)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("orbitProperties_pass", orbit_pass))
        .select(config.S1_POLARIZATION)
    )
    
    count = collection.size().getInfo()
    
    print(f"✓ Retrieved Sentinel-1 collection")
    print(f"  Date range: {start} to {end}")
    print(f"  Orbit: {orbit_pass}")
    print(f"  Images found: {count}")
    
    return collection, count


def get_collection_dates(collection: ee.ImageCollection) -> list:
    """
    Get list of acquisition dates in a collection.
    
    Args:
        collection: An ee.ImageCollection.
    
    Returns:
        list: Sorted list of date strings.
    """
    dates = (
        collection
        .aggregate_array("system:time_start")
        .map(lambda d: ee.Date(d).format("YYYY-MM-dd"))
        .distinct()
        .sort()
        .getInfo()
    )
    return dates


def get_collection_metadata(collection: ee.ImageCollection) -> dict:
    """
    Get summary metadata for a collection.
    
    Args:
        collection: An ee.ImageCollection.
    
    Returns:
        dict: Metadata including count, date range, and cloud stats.
    """
    count = collection.size().getInfo()
    
    if count == 0:
        return {"count": 0, "dates": [], "cloud_stats": None}
    
    dates = get_collection_dates(collection)
    
    # Try to get cloud statistics (Sentinel-2 only)
    try:
        cloud_stats = {
            "mean": collection.aggregate_mean("CLOUDY_PIXEL_PERCENTAGE").getInfo(),
            "min": collection.aggregate_min("CLOUDY_PIXEL_PERCENTAGE").getInfo(),
            "max": collection.aggregate_max("CLOUDY_PIXEL_PERCENTAGE").getInfo(),
        }
    except:
        cloud_stats = None
    
    return {
        "count": count,
        "dates": dates,
        "date_range": f"{dates[0]} to {dates[-1]}" if dates else None,
        "cloud_stats": cloud_stats
    }


def print_collection_info(collection: ee.ImageCollection, name: str = "Collection"):
    """
    Print detailed information about a collection.
    
    Args:
        collection: An ee.ImageCollection.
        name: Display name for the collection.
    """
    metadata = get_collection_metadata(collection)
    
    print(f"\n{name} Info:")
    print("-" * 40)
    print(f"  Image count: {metadata['count']}")
    
    if metadata['count'] > 0:
        print(f"  Date range: {metadata['date_range']}")
        
        if metadata['cloud_stats']:
            cs = metadata['cloud_stats']
            print(f"  Cloud cover: {cs['min']:.1f}% - {cs['max']:.1f}% (mean: {cs['mean']:.1f}%)")
        
        print(f"  Acquisition dates:")
        for date in metadata['dates'][:10]:  # Show first 10 dates
            print(f"    - {date}")
        if len(metadata['dates']) > 10:
            print(f"    ... and {len(metadata['dates']) - 10} more")
    
    print("-" * 40)