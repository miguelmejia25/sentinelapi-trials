import config
from retrieval import get_sentinel2_collection, get_s2_cloudless_collection
from cloud import apply_comprehensive_cloud_mask
from compositing import create_composite
from soil import (calculate_selected_indices, create_bare_soil_mask, 
                  get_soil_statistics)
from main import (get_all_indices_histograms, get_all_visualization_urls)
import ee


class AnalysisError(Exception):
    pass

def analyze_fun(
    latitude: float = None,
    longitude: float = None,
    buffer_m: int = None,
    cloud_max: int = None,
    start_date: str = None, 
    end_date: str = None
):
    
    results = {}
    
    lat = latitude 
    lon = longitude 
    buffer = buffer_m 
    cloud_thresh = cloud_max or config.CLOUD_PROBABILITY_THRESHOLD
    try:
        point = ee.Geometry.Point([lon, lat])
        roi = point.buffer(buffer)
    except Exception as e:
        raise AnalysisError("Error creando roi: "+ e)

    try:
        s2_collection, s2_count = get_sentinel2_collection(roi, start_date, end_date)
        if s2_count == 0:
            raise AnalysisError("Error obteniendo coleccion de imagenes s2, intenta cambiando el rango de tiempo")

        s2_cloudless = get_s2_cloudless_collection(roi)
    except AnalysisError:
        raise
    except Exception as e:
        raise AnalysisError("Error obteniendo imagenes del satelite")
    
    results["image_count"] = s2_count
    try:
        masked_collection = apply_comprehensive_cloud_mask(
            s2_collection,
            s2_cloudless,
            cloud_threshold= cloud_max or config.CLOUD_PROBABILITY_THRESHOLD
        )
    except Exception as e:
        raise AnalysisError("Error masking clouds: " + e)
    
    
    try:
        composite = create_composite(
            masked_collection,
            method=config.COMPOSITE_METHOD
        )
    except Exception as e:
        raise AnalysisError("Error creando imagen compuesta: " + e)
    
    try:
        composite = composite.clip(roi)
        results["composite"] = composite
    
        composite_with_indices = calculate_selected_indices(
            composite,
            indices=config.SOIL_INDICES
        )
        results["composite_with_indices"] = composite_with_indices
    except Exception as e:
        raise AnalysisError("error calculando indices: " + e)
    # Create bare soil mask

    try:
        bare_soil_mask = create_bare_soil_mask(composite_with_indices)
        results["bare_soil_mask"] = bare_soil_mask
    except Exception as e:
        raise AnalysisError("error creando mask de suelo: " + e)
    
    try:
        stats = get_soil_statistics(
            composite_with_indices,
            roi,
            indices=config.SOIL_INDICES
        )
        results["statistics"] = stats
    except Exception as e:
        raise AnalysisError("Error obteniendo estadisticas del suelo: "+ e)
    
    try:
        histograms = get_all_indices_histograms(
            composite_with_indices,
            roi,
            indices=config.SOIL_INDICES
        )
        results["histograms"] = histograms
    except Exception as e:
        raise AnalysisError("Error obteniendo hisotgramas: " + e)
    try:
        image_urls = get_all_visualization_urls(composite, roi, dimensions=600)
    except Exception as e:
        raise AnalysisError("error obteniendo urls de imagenes: " + e)
    
    results = {
        "metadata": {
            "coordinates": {
                "lat": latitude,
                "lon": longitude
            },
            "buffer_m": buffer_m,
            "date_range": {
                "start": start_date,
                "end": end_date
            },
            "images_used": s2_count,
            "cloud_threshold": cloud_thresh
        },
        "images": image_urls,
        "indices": stats,
        "histograms": histograms
    }

    return results