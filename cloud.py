"""
Cloud masking module.
Implements various cloud masking strategies for Sentinel-2 imagery.
"""

import ee
from typing import Tuple

import config


def mask_s2_clouds_qa(image: ee.Image) -> ee.Image:
    """
    Mask clouds using Sentinel-2 QA60 band.
    
    This is the basic built-in cloud mask. Less accurate than s2cloudless
    but doesn't require joining collections.
    
    Args:
        image: Sentinel-2 image with QA60 band.
    
    Returns:
        ee.Image: Image with clouds masked.
    """
    qa = image.select("QA60")
    
    # Bits 10 and 11 are clouds and cirrus
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    
    # Both flags should be zero for clear conditions
    mask = (
        qa.bitwiseAnd(cloud_bit_mask).eq(0)
        .And(qa.bitwiseAnd(cirrus_bit_mask).eq(0))
    )
    
    return image.updateMask(mask)


def mask_s2_clouds_scl(image: ee.Image) -> ee.Image:
    """
    Mask clouds using Sentinel-2 Scene Classification Layer (SCL).
    
    SCL provides more detailed classification including cloud shadows.
    Available in Sentinel-2 Level-2A products.
    
    Args:
        image: Sentinel-2 image with SCL band.
    
    Returns:
        ee.Image: Image with clouds and shadows masked.
    """
    scl = image.select("SCL")
    
    # SCL classes to mask:
    # 3 = Cloud Shadow
    # 8 = Cloud Medium Probability
    # 9 = Cloud High Probability
    # 10 = Thin Cirrus
    # 11 = Snow/Ice (optional, may want to keep)
    
    mask = (
        scl.neq(3)   # Not cloud shadow
        .And(scl.neq(8))   # Not cloud medium
        .And(scl.neq(9))   # Not cloud high
        .And(scl.neq(10))  # Not cirrus
    )
    
    return image.updateMask(mask)


def add_cloud_probability(
    s2_collection: ee.ImageCollection,
    cloudless_collection: ee.ImageCollection
) -> ee.ImageCollection:
    """
    Join s2cloudless probability band to Sentinel-2 collection.
    
    This adds a 'probability' band to each S2 image from the
    corresponding s2cloudless image.
    
    Args:
        s2_collection: Sentinel-2 image collection.
        cloudless_collection: s2cloudless probability collection.
    
    Returns:
        ee.ImageCollection: S2 collection with probability band added.
    """
    # Define join condition: same system:index
    join_filter = ee.Filter.equals(
        leftField="system:index",
        rightField="system:index"
    )
    
    # Join the collections
    joined = ee.ImageCollection(
        ee.Join.saveFirst("cloud_prob").apply(
            primary=s2_collection,
            secondary=cloudless_collection,
            condition=join_filter
        )
    )
    
    # Add probability band to each image
    def add_prob_band(image):
        cloud_prob = ee.Image(image.get("cloud_prob")).select("probability")
        return image.addBands(cloud_prob)
    
    return joined.map(add_prob_band)


def mask_s2_clouds_probability(
    image: ee.Image,
    threshold: int = None
) -> ee.Image:
    """
    Mask clouds using s2cloudless probability.
    
    Requires the image to have a 'probability' band added via
    add_cloud_probability().
    
    Args:
        image: Sentinel-2 image with probability band.
        threshold: Cloud probability threshold (0-100). 
                  Pixels above this are masked.
                  Defaults to config.CLOUD_PROBABILITY_THRESHOLD.
    
    Returns:
        ee.Image: Image with clouds masked.
    """
    thresh = threshold or config.CLOUD_PROBABILITY_THRESHOLD
    
    cloud_prob = image.select("probability")
    mask = cloud_prob.lt(thresh)
    
    return image.updateMask(mask)


def mask_cloud_shadows(
    image: ee.Image,
    cloud_prob_threshold: int = 40,
    nir_dark_threshold: float = 0.15,
    shadow_search_distance: int = 1000
) -> ee.Image:
    """
    Mask cloud shadows using projection from clouds.
    
    This estimates shadow positions based on sun angle and cloud height,
    then masks dark pixels in those areas.
    
    Args:
        image: Sentinel-2 image with probability band.
        cloud_prob_threshold: Threshold for identifying cloud pixels.
        nir_dark_threshold: NIR reflectance threshold for dark pixels.
        shadow_search_distance: Max distance to search for shadows (meters).
    
    Returns:
        ee.Image: Image with cloud shadows masked.
    """
    # Identify clouds
    cloud_prob = image.select("probability")
    is_cloud = cloud_prob.gt(cloud_prob_threshold)
    
    # Identify dark pixels (potential shadows)
    nir = image.select("B8")
    dark_pixels = nir.lt(nir_dark_threshold * 10000)  # Scale factor
    
    # Get sun position for shadow projection
    mean_azimuth = image.get("MEAN_SOLAR_AZIMUTH_ANGLE")
    mean_zenith = image.get("MEAN_SOLAR_ZENITH_ANGLE")
    
    # Project shadows from clouds
    shadow_azimuth = ee.Number(90).subtract(ee.Number(mean_azimuth))
    
    # Assume cloud height of ~1km for shadow projection
    cloud_height = 1000
    shadow_distance = ee.Number(mean_zenith).tan().multiply(cloud_height)
    
    # Limit shadow distance
    shadow_distance = shadow_distance.min(shadow_search_distance)
    
    # Project cloud shadows
    projected_shadows = (
        is_cloud
        .directionalDistanceTransform(shadow_azimuth, shadow_search_distance)
        .select("distance")
        .mask()
    )
    
    # Shadow mask: dark pixels within projected shadow zone
    is_shadow = dark_pixels.And(projected_shadows)
    
    # Combined mask: not cloud and not shadow
    clear_mask = is_cloud.Not().And(is_shadow.Not())
    
    return image.updateMask(clear_mask)


def apply_comprehensive_cloud_mask(
    s2_collection: ee.ImageCollection,
    cloudless_collection: ee.ImageCollection,
    cloud_threshold: int = None,
    mask_shadows: bool = True
) -> ee.ImageCollection:
    """
    Apply comprehensive cloud and shadow masking to collection.
    
    This is the recommended function for production use. It:
    1. Joins s2cloudless probability
    2. Masks clouds using probability threshold
    3. Optionally masks cloud shadows
    4. Also applies SCL mask for extra coverage
    
    Args:
        s2_collection: Sentinel-2 image collection.
        cloudless_collection: s2cloudless probability collection.
        cloud_threshold: Cloud probability threshold.
                        Defaults to config.CLOUD_PROBABILITY_THRESHOLD.
        mask_shadows: Whether to also mask cloud shadows.
    
    Returns:
        ee.ImageCollection: Collection with clouds masked.
    """
    thresh = cloud_threshold or config.CLOUD_PROBABILITY_THRESHOLD
    
    # Add cloud probability band
    collection_with_prob = add_cloud_probability(s2_collection, cloudless_collection)
    
    def apply_masks(image):
        # Apply probability-based cloud mask
        masked = mask_s2_clouds_probability(image, thresh)
        
        # Apply SCL mask for additional coverage
        masked = mask_s2_clouds_scl(masked)
        
        return masked
    
    masked_collection = collection_with_prob.map(apply_masks)
    
    print(f"✓ Applied cloud masking (threshold: {thresh}%)")
    
    return masked_collection


def get_cloud_free_pixel_percentage(
    image: ee.Image,
    roi: ee.Geometry,
    scale: int = 100
) -> float:
    """
    Calculate percentage of cloud-free pixels in an image.
    
    Args:
        image: Masked image (clouds should be masked out).
        roi: Region of interest.
        scale: Scale for calculation in meters.
    
    Returns:
        float: Percentage of cloud-free pixels (0-100).
    """
    # Count valid (unmasked) pixels
    valid_pixels = (
        image.select(0)
        .reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=scale,
            maxPixels=1e9
        )
        .values()
        .get(0)
    )
    
    # Count total pixels in region
    total_pixels = (
        ee.Image.constant(1)
        .reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=scale,
            maxPixels=1e9
        )
        .values()
        .get(0)
    )
    
    percentage = (
        ee.Number(valid_pixels)
        .divide(ee.Number(total_pixels))
        .multiply(100)
        .getInfo()
    )
    
    return percentage


def filter_by_clear_pixels(
    collection: ee.ImageCollection,
    roi: ee.Geometry,
    min_clear_percent: float = 50,
    scale: int = 100
) -> ee.ImageCollection:
    """
    Filter collection to only include images with sufficient clear pixels.
    
    Args:
        collection: Masked image collection.
        roi: Region of interest.
        min_clear_percent: Minimum percentage of clear pixels required.
        scale: Scale for calculation in meters.
    
    Returns:
        ee.ImageCollection: Filtered collection.
    """
    def add_clear_percent(image):
        valid = image.select(0).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=scale,
            maxPixels=1e9
        ).values().get(0)
        
        total = ee.Image.constant(1).reduceRegion(
            reducer=ee.Reducer.count(),
            geometry=roi,
            scale=scale,
            maxPixels=1e9
        ).values().get(0)
        
        clear_pct = ee.Number(valid).divide(ee.Number(total)).multiply(100)
        
        return image.set("clear_pixel_percent", clear_pct)
    
    collection_with_stats = collection.map(add_clear_percent)
    
    filtered = collection_with_stats.filter(
        ee.Filter.gte("clear_pixel_percent", min_clear_percent)
    )
    
    return filtered