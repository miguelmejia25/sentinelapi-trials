"""
Soil indices calculation module.
Implements various spectral indices for soil type and quality analysis.
"""

import ee
from typing import List, Dict

import config


def calculate_ndsi(image: ee.Image) -> ee.Image:
    """
    Calculate Normalized Difference Soil Index.
    
    NDSI = (SWIR - NIR) / (SWIR + NIR)
    
    Higher values indicate bare soil, lower values indicate vegetation.
    Useful for identifying exposed soil areas.
    
    Args:
        image: Sentinel-2 image with B8 and B11 bands.
    
    Returns:
        ee.Image: Single band image with NDSI values (-1 to 1).
    """
    ndsi = image.normalizedDifference([
        config.S2_BANDS["swir_1"],  # B11
        config.S2_BANDS["nir"]       # B8
    ]).rename("NDSI")
    
    return ndsi


def calculate_bare_soil_index(image: ee.Image) -> ee.Image:
    """
    Calculate Bare Soil Index (BI).
    
    BI = ((SWIR1 + Red) - (NIR + Blue)) / ((SWIR1 + Red) + (NIR + Blue))
    
    Highlights bare soil areas. Higher values indicate exposed soil.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with BI values.
    """
    swir1 = image.select(config.S2_BANDS["swir_1"])
    red = image.select(config.S2_BANDS["red"])
    nir = image.select(config.S2_BANDS["nir"])
    blue = image.select(config.S2_BANDS["blue"])
    
    numerator = swir1.add(red).subtract(nir).subtract(blue)
    denominator = swir1.add(red).add(nir).add(blue)
    
    bi = numerator.divide(denominator).rename("BI")
    
    return bi


def calculate_bsi(image: ee.Image) -> ee.Image:
    """
    Calculate Bare Soil Index (alternative formula - BSI).
    
    BSI = ((SWIR2 + Red) - (NIR + Blue)) / ((SWIR2 + Red) + (NIR + Blue)) * 100 + 100
    
    Scaled version that emphasizes bare soil. Range approximately 0-200.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with BSI values.
    """
    swir2 = image.select(config.S2_BANDS["swir_2"])
    red = image.select(config.S2_BANDS["red"])
    nir = image.select(config.S2_BANDS["nir"])
    blue = image.select(config.S2_BANDS["blue"])
    
    numerator = swir2.add(red).subtract(nir).subtract(blue)
    denominator = swir2.add(red).add(nir).add(blue)
    
    bsi = numerator.divide(denominator).multiply(100).add(100).rename("BSI")
    
    return bsi


def calculate_color_index(image: ee.Image) -> ee.Image:
    """
    Calculate Soil Color Index (CI).
    
    CI = (Red - Green) / (Red + Green)
    
    Related to soil iron oxide content. Higher values suggest
    more oxidized (redder) soils, often indicating well-drained conditions.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with CI values.
    """
    red = image.select(config.S2_BANDS["red"])
    green = image.select(config.S2_BANDS["green"])
    
    ci = red.subtract(green).divide(red.add(green)).rename("CI")
    
    return ci


def calculate_ndmi(image: ee.Image) -> ee.Image:
    """
    Calculate Normalized Difference Moisture Index.
    
    NDMI = (NIR - SWIR1) / (NIR + SWIR1)
    
    Indicates vegetation and soil moisture content.
    Higher values = more moisture, lower values = drier conditions.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with NDMI values (-1 to 1).
    """
    ndmi = image.normalizedDifference([
        config.S2_BANDS["nir"],      # B8
        config.S2_BANDS["swir_1"]    # B11
    ]).rename("NDMI")
    
    return ndmi


def calculate_ndvi(image: ee.Image) -> ee.Image:
    """
    Calculate Normalized Difference Vegetation Index.
    
    NDVI = (NIR - Red) / (NIR + Red)
    
    Standard vegetation index. Useful for identifying bare soil areas
    (low NDVI) vs vegetated areas (high NDVI).
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with NDVI values (-1 to 1).
    """
    ndvi = image.normalizedDifference([
        config.S2_BANDS["nir"],   # B8
        config.S2_BANDS["red"]    # B4
    ]).rename("NDVI")
    
    return ndvi


def calculate_saturation_index(image: ee.Image) -> ee.Image:
    """
    Calculate Soil Saturation Index (SSI).
    
    SSI = (Red - Green) / (Red + Green + Blue)
    
    Related to soil mineralogy and organic matter content.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with SSI values.
    """
    red = image.select(config.S2_BANDS["red"])
    green = image.select(config.S2_BANDS["green"])
    blue = image.select(config.S2_BANDS["blue"])
    
    ssi = red.subtract(green).divide(red.add(green).add(blue)).rename("SSI")
    
    return ssi


def calculate_brightness_index(image: ee.Image) -> ee.Image:
    """
    Calculate Soil Brightness Index.
    
    Brightness = sqrt(Red^2 + NIR^2)
    
    Indicates overall soil reflectance. Sandy soils tend to be brighter,
    organic-rich soils tend to be darker.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with brightness values.
    """
    red = image.select(config.S2_BANDS["red"])
    nir = image.select(config.S2_BANDS["nir"])
    
    brightness = red.pow(2).add(nir.pow(2)).sqrt().rename("Brightness")
    
    return brightness


def calculate_clay_index(image: ee.Image) -> ee.Image:
    """
    Calculate Clay Minerals Index.
    
    Clay Index = SWIR1 / SWIR2
    
    Clay minerals have characteristic absorption in SWIR2.
    Higher values may indicate higher clay content.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with clay index values.
    """
    swir1 = image.select(config.S2_BANDS["swir_1"])
    swir2 = image.select(config.S2_BANDS["swir_2"])
    
    clay = swir1.divide(swir2).rename("ClayIndex")
    
    return clay


def calculate_organic_matter_index(image: ee.Image) -> ee.Image:
    """
    Calculate Soil Organic Matter Index (SOM proxy).
    
    Based on the relationship between visible bands and organic content.
    Darker soils in visible wavelengths often indicate higher organic matter.
    
    SOM_proxy = 1 - (2.5 * Red - Green) / (Red + Green)
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Single band image with SOM index values.
    """
    red = image.select(config.S2_BANDS["red"])
    green = image.select(config.S2_BANDS["green"])
    
    # Normalize to 0-1 range (assuming 10000 scale factor)
    red_norm = red.divide(10000)
    green_norm = green.divide(10000)
    
    som = ee.Image.constant(1).subtract(
        red_norm.multiply(2.5).subtract(green_norm)
        .divide(red_norm.add(green_norm))
    ).rename("SOM_Index")
    
    return som


def calculate_all_indices(image: ee.Image) -> ee.Image:
    """
    Calculate all soil indices and add as bands.
    
    Args:
        image: Sentinel-2 image.
    
    Returns:
        ee.Image: Image with all soil index bands added.
    """
    indices = [
        calculate_ndsi(image),
        calculate_bare_soil_index(image),
        calculate_bsi(image),
        calculate_color_index(image),
        calculate_ndmi(image),
        calculate_ndvi(image),
        calculate_saturation_index(image),
        calculate_brightness_index(image),
        calculate_clay_index(image),
        calculate_organic_matter_index(image),
    ]
    
    result = image
    for index in indices:
        result = result.addBands(index)
    
    print("✓ Calculated all soil indices")
    return result


def calculate_selected_indices(
    image: ee.Image,
    indices: List[str] = None
) -> ee.Image:
    """
    Calculate selected soil indices based on config or input.
    
    Args:
        image: Sentinel-2 image.
        indices: List of index names to calculate. 
                Defaults to config.SOIL_INDICES.
    
    Returns:
        ee.Image: Image with selected soil index bands added.
    """
    indices_to_calc = indices or config.SOIL_INDICES
    
    index_functions = {
        "NDSI": calculate_ndsi,
        "BI": calculate_bare_soil_index,
        "BSI": calculate_bsi,
        "CI": calculate_color_index,
        "NDMI": calculate_ndmi,
        "NDVI": calculate_ndvi,
        "SSI": calculate_saturation_index,
        "Brightness": calculate_brightness_index,
        "ClayIndex": calculate_clay_index,
        "SOM_Index": calculate_organic_matter_index,
    }
    
    result = image
    calculated = []
    
    for index_name in indices_to_calc:
        if index_name in index_functions:
            index_image = index_functions[index_name](image)
            result = result.addBands(index_image)
            calculated.append(index_name)
        else:
            print(f"  Warning: Unknown index '{index_name}'")
    
    print(f"✓ Calculated indices: {', '.join(calculated)}")
    return result


def create_bare_soil_mask(
    image: ee.Image,
    ndvi_threshold: float = 0.3,
    bsi_threshold: float = 100
) -> ee.Image:
    """
    Create a mask identifying bare soil pixels.
    
    Combines NDVI (low vegetation) and BSI (high bare soil index)
    to identify pixels likely showing exposed soil.
    
    Args:
        image: Image with NDVI and BSI bands (or original bands).
        ndvi_threshold: Maximum NDVI for bare soil (default 0.3).
        bsi_threshold: Minimum BSI for bare soil (default 100).
    
    Returns:
        ee.Image: Binary mask (1 = bare soil, 0 = other).
    """
    # Calculate indices if not present
    try:
        ndvi = image.select("NDVI")
    except:
        ndvi = calculate_ndvi(image)
    
    try:
        bsi = image.select("BSI")
    except:
        bsi = calculate_bsi(image)
    
    # Bare soil: low vegetation AND high bare soil index
    bare_soil_mask = ndvi.lt(ndvi_threshold).And(bsi.gt(bsi_threshold))
    
    return bare_soil_mask.rename("bare_soil_mask")


def get_soil_statistics(
    image: ee.Image,
    roi: ee.Geometry,
    indices: List[str] = None,
    scale: int = 10
) -> Dict:
    """
    Calculate statistics for soil indices within region.
    
    Args:
        image: Image with soil index bands.
        roi: Region of interest.
        indices: List of index band names to analyze.
        scale: Scale for reduction in meters.
    
    Returns:
        dict: Statistics (mean, min, max, std) for each index.
    """
    indices = indices or config.SOIL_INDICES
    
    stats = {}
    
    for index_name in indices:
        try:
            index_band = image.select(index_name)
            
            reducers = ee.Reducer.mean() \
                .combine(ee.Reducer.minMax(), sharedInputs=True) \
                .combine(ee.Reducer.stdDev(), sharedInputs=True)
            
            result = index_band.reduceRegion(
                reducer=reducers,
                geometry=roi,
                scale=scale,
                maxPixels=1e9
            ).getInfo()
            
            stats[index_name] = {
                "mean": result.get(f"{index_name}_mean"),
                "min": result.get(f"{index_name}_min"),
                "max": result.get(f"{index_name}_max"),
                "stdDev": result.get(f"{index_name}_stdDev"),
            }
        except Exception as e:
            print(f"  Warning: Could not calculate stats for {index_name}: {e}")
    
    return stats


def interpret_soil_indices(stats: Dict) -> Dict:
    """
    Provide interpretation of soil index statistics.
    
    Args:
        stats: Dictionary of soil index statistics.
    
    Returns:
        dict: Interpretations for each index.
    """
    interpretations = {}
    
    if "NDVI" in stats:
        ndvi_mean = stats["NDVI"]["mean"]
        if ndvi_mean is not None:
            if ndvi_mean < 0.2:
                interpretations["vegetation"] = "Sparse/bare - good for soil analysis"
            elif ndvi_mean < 0.4:
                interpretations["vegetation"] = "Moderate vegetation cover"
            else:
                interpretations["vegetation"] = "Dense vegetation - soil may be obscured"
    
    if "NDMI" in stats:
        ndmi_mean = stats["NDMI"]["mean"]
        if ndmi_mean is not None:
            if ndmi_mean < 0:
                interpretations["moisture"] = "Dry conditions"
            elif ndmi_mean < 0.2:
                interpretations["moisture"] = "Moderate moisture"
            else:
                interpretations["moisture"] = "High moisture content"
    
    if "CI" in stats:
        ci_mean = stats["CI"]["mean"]
        if ci_mean is not None:
            if ci_mean > 0.1:
                interpretations["soil_color"] = "Reddish soil - possible iron oxidation"
            elif ci_mean < -0.1:
                interpretations["soil_color"] = "Greenish/dark soil"
            else:
                interpretations["soil_color"] = "Neutral soil color"
    
    if "BSI" in stats:
        bsi_mean = stats["BSI"]["mean"]
        if bsi_mean is not None:
            if bsi_mean > 120:
                interpretations["bare_soil"] = "High bare soil exposure"
            elif bsi_mean > 100:
                interpretations["bare_soil"] = "Moderate bare soil"
            else:
                interpretations["bare_soil"] = "Low bare soil index"
    
    if "ClayIndex" in stats:
        clay_mean = stats["ClayIndex"]["mean"]
        if clay_mean is not None:
            if clay_mean > 1.5:
                interpretations["clay_content"] = "Potentially high clay content"
            elif clay_mean > 1.2:
                interpretations["clay_content"] = "Moderate clay indicators"
            else:
                interpretations["clay_content"] = "Lower clay indicators"
    
    return interpretations


def print_soil_analysis(stats: Dict, roi_name: str = "ROI"):
    """
    Print formatted soil analysis report.
    
    Args:
        stats: Dictionary of soil index statistics.
        roi_name: Name of the region for display.
    """
    print(f"\n{'='*50}")
    print(f"SOIL ANALYSIS REPORT: {roi_name}")
    print(f"{'='*50}\n")
    
    print("Index Statistics:")
    print("-" * 40)
    
    for index_name, values in stats.items():
        if values["mean"] is not None:
            print(f"\n{index_name}:")
            print(f"  Mean:   {values['mean']:.4f}")
            print(f"  Min:    {values['min']:.4f}")
            print(f"  Max:    {values['max']:.4f}")
            print(f"  StdDev: {values['stdDev']:.4f}")
    
    print("\n" + "-" * 40)
    print("Interpretation:")
    print("-" * 40)
    
    interpretations = interpret_soil_indices(stats)
    for aspect, interpretation in interpretations.items():
        print(f"  {aspect}: {interpretation}")
    
    print(f"\n{'='*50}\n")