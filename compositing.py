"""
Image compositing module.
Creates temporal composites from image collections to fill gaps and reduce noise.
"""

import ee
from typing import List, Optional

import config


def create_median_composite(
    collection: ee.ImageCollection,
    bands: List[str] = None
) -> ee.Image:
    """
    Create a median composite from image collection.
    
    Median compositing is effective for removing clouds and noise
    because outliers (clouds are bright, shadows are dark) get filtered out.
    
    Args:
        collection: Image collection to composite.
        bands: Optional list of bands to include. If None, includes all.
    
    Returns:
        ee.Image: Median composite image.
    """
    if bands:
        collection = collection.select(bands)
    
    composite = collection.median()
    
    print("✓ Created median composite")
    return composite


def create_mean_composite(
    collection: ee.ImageCollection,
    bands: List[str] = None
) -> ee.Image:
    """
    Create a mean composite from image collection.
    
    Mean compositing averages all values. Less robust to outliers than median
    but preserves more spectral information.
    
    Args:
        collection: Image collection to composite.
        bands: Optional list of bands to include.
    
    Returns:
        ee.Image: Mean composite image.
    """
    if bands:
        collection = collection.select(bands)
    
    composite = collection.mean()
    
    print("✓ Created mean composite")
    return composite


def create_percentile_composite(
    collection: ee.ImageCollection,
    percentile: int = 50,
    bands: List[str] = None
) -> ee.Image:
    """
    Create a percentile composite from image collection.
    
    Percentile compositing allows tuning between median (50) and
    other values. Lower percentiles favor darker values, higher favor brighter.
    
    For soil analysis:
    - Lower percentiles (20-40) can help reveal bare soil under sparse vegetation
    - Higher percentiles (60-80) can reduce shadow effects
    
    Args:
        collection: Image collection to composite.
        percentile: Percentile value (0-100). 50 = median.
        bands: Optional list of bands to include.
    
    Returns:
        ee.Image: Percentile composite image.
    """
    if bands:
        collection = collection.select(bands)
    
    composite = collection.reduce(ee.Reducer.percentile([percentile]))
    
    # Rename bands to remove '_pXX' suffix
    band_names = composite.bandNames()
    new_names = band_names.map(lambda name: ee.String(name).replace(f"_p{percentile}", ""))
    composite = composite.rename(new_names)
    
    print(f"✓ Created {percentile}th percentile composite")
    return composite


def create_min_composite(
    collection: ee.ImageCollection,
    bands: List[str] = None
) -> ee.Image:
    """
    Create a minimum value composite.
    
    Useful for:
    - Finding darkest (least cloudy in visible bands)
    - Identifying water bodies
    - Shadow analysis
    
    Args:
        collection: Image collection to composite.
        bands: Optional list of bands to include.
    
    Returns:
        ee.Image: Minimum value composite.
    """
    if bands:
        collection = collection.select(bands)
    
    composite = collection.min()
    
    print("✓ Created minimum composite")
    return composite


def create_max_composite(
    collection: ee.ImageCollection,
    bands: List[str] = None
) -> ee.Image:
    """
    Create a maximum value composite.
    
    Useful for:
    - Finding brightest pixels
    - Maximum vegetation greenness
    - Peak NDVI analysis
    
    Args:
        collection: Image collection to composite.
        bands: Optional list of bands to include.
    
    Returns:
        ee.Image: Maximum value composite.
    """
    if bands:
        collection = collection.select(bands)
    
    composite = collection.max()
    
    print("✓ Created maximum composite")
    return composite


def create_greenest_pixel_composite(
    collection: ee.ImageCollection
) -> ee.Image:
    """
    Create composite using pixels with maximum NDVI.
    
    This selects the pixel from the date with highest vegetation greenness,
    which often corresponds to clearest conditions and healthiest vegetation.
    
    Args:
        collection: Sentinel-2 image collection.
    
    Returns:
        ee.Image: Greenest pixel composite.
    """
    def add_ndvi(image):
        ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        return image.addBands(ndvi)
    
    collection_with_ndvi = collection.map(add_ndvi)
    
    # Select pixels with maximum NDVI
    composite = collection_with_ndvi.qualityMosaic("NDVI")
    
    print("✓ Created greenest pixel composite")
    return composite


def create_driest_pixel_composite(
    collection: ee.ImageCollection
) -> ee.Image:
    """
    Create composite using pixels with minimum moisture.
    
    Useful for soil analysis as it favors dates when soil is more exposed
    (less vegetation, drier conditions).
    
    Args:
        collection: Sentinel-2 image collection.
    
    Returns:
        ee.Image: Driest pixel composite.
    """
    def add_ndmi(image):
        # NDMI: lower = drier
        ndmi = image.normalizedDifference(["B8", "B11"]).rename("NDMI")
        # Invert so that drier = higher quality score
        ndmi_inv = ndmi.multiply(-1).rename("NDMI_inv")
        return image.addBands(ndmi_inv)
    
    collection_with_ndmi = collection.map(add_ndmi)
    
    # Select pixels with minimum moisture (maximum inverted NDMI)
    composite = collection_with_ndmi.qualityMosaic("NDMI_inv")
    
    print("✓ Created driest pixel composite")
    return composite


def create_monthly_composites(
    collection: ee.ImageCollection,
    start_date: str,
    end_date: str,
    method: str = "median"
) -> ee.ImageCollection:
    """
    Create monthly composites from a collection.
    
    Args:
        collection: Image collection to composite.
        start_date: Start date (YYYY-MM-DD).
        end_date: End date (YYYY-MM-DD).
        method: Compositing method ("median", "mean", "max", "min").
    
    Returns:
        ee.ImageCollection: Collection of monthly composites.
    """
    start = ee.Date(start_date)
    end = ee.Date(end_date)
    
    # Calculate number of months
    n_months = end.difference(start, "month").round()
    
    def make_monthly_composite(month_offset):
        month_offset = ee.Number(month_offset)
        month_start = start.advance(month_offset, "month")
        month_end = month_start.advance(1, "month")
        
        monthly_collection = collection.filterDate(month_start, month_end)
        
        if method == "median":
            composite = monthly_collection.median()
        elif method == "mean":
            composite = monthly_collection.mean()
        elif method == "max":
            composite = monthly_collection.max()
        elif method == "min":
            composite = monthly_collection.min()
        else:
            composite = monthly_collection.median()
        
        return composite.set({
            "system:time_start": month_start.millis(),
            "month": month_start.format("YYYY-MM")
        })
    
    months = ee.List.sequence(0, n_months.subtract(1))
    monthly_composites = ee.ImageCollection(months.map(make_monthly_composite))
    
    print(f"✓ Created {n_months.getInfo()} monthly composites using {method}")
    return monthly_composites


def create_composite(
    collection: ee.ImageCollection,
    method: str = None,
    percentile: int = None,
    bands: List[str] = None
) -> ee.Image:
    """
    Create composite using specified method from config.
    
    This is the main compositing function that reads from config
    and dispatches to the appropriate method.
    
    Args:
        collection: Image collection to composite.
        method: Compositing method. Defaults to config.COMPOSITE_METHOD.
        percentile: Percentile value. Defaults to config.COMPOSITE_PERCENTILE.
        bands: Optional list of bands to include.
    
    Returns:
        ee.Image: Composite image.
    """
    method = method or config.COMPOSITE_METHOD
    percentile = percentile or config.COMPOSITE_PERCENTILE
    
    if method == "median":
        return create_median_composite(collection, bands)
    elif method == "mean":
        return create_mean_composite(collection, bands)
    elif method == "percentile":
        return create_percentile_composite(collection, percentile, bands)
    elif method == "min":
        return create_min_composite(collection, bands)
    elif method == "max":
        return create_max_composite(collection, bands)
    elif method == "greenest":
        return create_greenest_pixel_composite(collection)
    elif method == "driest":
        return create_driest_pixel_composite(collection)
    else:
        print(f"Unknown method '{method}', defaulting to median")
        return create_median_composite(collection, bands)


def create_multi_composite(
    collection: ee.ImageCollection,
    bands: List[str] = None
) -> dict:
    """
    Create multiple composites for comparison.
    
    Useful for understanding which compositing method works best
    for your specific area.
    
    Args:
        collection: Image collection to composite.
        bands: Optional list of bands to include.
    
    Returns:
        dict: Dictionary of composites by method name.
    """
    composites = {
        "median": create_median_composite(collection, bands),
        "mean": create_mean_composite(collection, bands),
        "p25": create_percentile_composite(collection, 25, bands),
        "p75": create_percentile_composite(collection, 75, bands),
        "greenest": create_greenest_pixel_composite(collection),
        "driest": create_driest_pixel_composite(collection),
    }
    
    print(f"✓ Created {len(composites)} composite variants")
    return composites