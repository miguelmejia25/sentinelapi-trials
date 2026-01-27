"""
Visualization module.
Generates histograms, charts, and visual analysis of soil indices.
"""

import ee
from typing import List, Dict, Optional, Tuple
import json

import config


def get_thumbnail_url(
    image: ee.Image,
    roi: ee.Geometry,
    bands: List[str],
    min_val: float,
    max_val: float,
    dimensions: int = 512,
    format: str = "jpg"
) -> str:
    """
    Get a thumbnail URL for an image visualization.
    
    Args:
        image: Image to visualize.
        roi: Region of interest.
        bands: List of 3 bands for RGB visualization.
        min_val: Minimum value for stretching.
        max_val: Maximum value for stretching.
        dimensions: Maximum dimension in pixels.
        format: Image format ('jpg' or 'png').
    
    Returns:
        str: URL to the thumbnail image.
    """
    vis_params = {
        'bands': bands,
        'min': min_val,
        'max': max_val,
        'dimensions': dimensions,
        'region': roi,
        'format': format
    }
    
    return image.getThumbURL(vis_params)


def get_all_visualization_urls(
    composite: ee.Image,
    roi: ee.Geometry,
    dimensions: int = 512
) -> Dict[str, str]:
    """
    Get thumbnail URLs for all standard visualizations.
    
    Args:
        composite: Composite image with all bands.
        roi: Region of interest.
        dimensions: Maximum dimension in pixels.
    
    Returns:
        dict: Visualization name to URL mapping.
    """
    visualizations = {}
    
    # True Color RGB
    try:
        visualizations["True Color (RGB)"] = get_thumbnail_url(
            composite, roi,
            bands=["B4", "B3", "B2"],
            min_val=0, max_val=3000,
            dimensions=dimensions
        )
        print("  ✓ Generated True Color thumbnail")
    except Exception as e:
        print(f"  ✗ Failed to generate True Color: {e}")
    
    # False Color Agriculture
    try:
        visualizations["False Color (Agriculture)"] = get_thumbnail_url(
            composite, roi,
            bands=["B8", "B4", "B3"],
            min_val=0, max_val=4000,
            dimensions=dimensions
        )
        print("  ✓ Generated False Color thumbnail")
    except Exception as e:
        print(f"  ✗ Failed to generate False Color: {e}")
    
    # SWIR Soil Composite
    try:
        visualizations["SWIR (Soil/Geology)"] = get_thumbnail_url(
            composite, roi,
            bands=["B11", "B8", "B4"],
            min_val=0, max_val=4000,
            dimensions=dimensions
        )
        print("  ✓ Generated SWIR Soil thumbnail")
    except Exception as e:
        print(f"  ✗ Failed to generate SWIR: {e}")
    
    # NDVI visualization (if available)
    try:
        # Create NDVI image with color palette
        ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
        ndvi_vis = ndvi.visualize(
            min=-0.2, max=0.8,
            palette=['red', 'yellow', 'green', 'darkgreen']
        )
        visualizations["NDVI (Vegetation Health)"] = ndvi_vis.getThumbURL({
            'dimensions': dimensions,
            'region': roi,
            'format': 'jpg'
        })
        print("  ✓ Generated NDVI thumbnail")
    except Exception as e:
        print(f"  ✗ Failed to generate NDVI: {e}")
    
    # Moisture visualization
    try:
        ndmi = composite.normalizedDifference(["B8", "B11"]).rename("NDMI")
        ndmi_vis = ndmi.visualize(
            min=-0.3, max=0.5,
            palette=['brown', 'yellow', 'cyan', 'blue']
        )
        visualizations["NDMI (Moisture)"] = ndmi_vis.getThumbURL({
            'dimensions': dimensions,
            'region': roi,
            'format': 'jpg'
        })
        print("  ✓ Generated NDMI thumbnail")
    except Exception as e:
        print(f"  ✗ Failed to generate NDMI: {e}")
    
    # Bare Soil visualization
    try:
        # BSI visualization
        swir2 = composite.select("B12")
        red = composite.select("B4")
        nir = composite.select("B8")
        blue = composite.select("B2")
        
        bsi = swir2.add(red).subtract(nir).subtract(blue) \
            .divide(swir2.add(red).add(nir).add(blue)) \
            .multiply(100).add(100).rename("BSI")
        
        bsi_vis = bsi.visualize(
            min=50, max=150,
            palette=['darkgreen', 'green', 'yellow', 'orange', 'red']
        )
        visualizations["BSI (Bare Soil Index)"] = bsi_vis.getThumbURL({
            'dimensions': dimensions,
            'region': roi,
            'format': 'jpg'
        })
        print("  ✓ Generated BSI thumbnail")
    except Exception as e:
        print(f"  ✗ Failed to generate BSI: {e}")
    
    return visualizations


def get_histogram_data(
    image: ee.Image,
    band_name: str,
    roi: ee.Geometry,
    scale: int = 30,
    min_val: float = -1,
    max_val: float = 1,
    num_buckets: int = 50
) -> Dict:
    """
    Get histogram data for a single band/index.
    
    Args:
        image: Image containing the band.
        band_name: Name of the band to analyze.
        roi: Region of interest.
        scale: Scale in meters for reduction.
        min_val: Minimum value for histogram range.
        max_val: Maximum value for histogram range.
        num_buckets: Number of histogram buckets.
    
    Returns:
        dict: Histogram data with buckets and counts.
    """
    band = image.select(band_name)
    
    histogram = band.reduceRegion(
        reducer=ee.Reducer.histogram(
            maxBuckets=num_buckets,
            minBucketWidth=(max_val - min_val) / num_buckets
        ),
        geometry=roi,
        scale=scale,
        maxPixels=1e9
    ).getInfo()
    
    hist_data = histogram.get(band_name, {})
    
    return {
        "band": band_name,
        "buckets": hist_data.get("bucketMeans", []),
        "counts": hist_data.get("histogram", []),
        "min": min_val,
        "max": max_val
    }


def get_all_indices_histograms(
    image: ee.Image,
    roi: ee.Geometry,
    indices: List[str] = None,
    scale: int = 30,
    num_buckets: int = 50
) -> Dict[str, Dict]:
    """
    Get histogram data for all soil indices.
    
    Args:
        image: Image with soil index bands.
        roi: Region of interest.
        indices: List of index names. Defaults to config.SOIL_INDICES.
        scale: Scale in meters.
        num_buckets: Number of histogram buckets.
    
    Returns:
        dict: Dictionary of index name to histogram data.
    """
    indices = indices or config.SOIL_INDICES
    
    # Define appropriate ranges for each index
    index_ranges = {
        "NDVI": (-1, 1),
        "NDSI": (-1, 1),
        "NDMI": (-1, 1),
        "BI": (-1, 1),
        "CI": (-1, 1),
        "SSI": (-1, 1),
        "BSI": (0, 200),
        "Brightness": (0, 15000),
        "ClayIndex": (0, 3),
        "SOM_Index": (-2, 2),
    }
    
    histograms = {}
    
    for index_name in indices:
        try:
            min_val, max_val = index_ranges.get(index_name, (-1, 1))
            hist = get_histogram_data(
                image, index_name, roi, scale, min_val, max_val, num_buckets
            )
            histograms[index_name] = hist
            print(f"  ✓ Generated histogram for {index_name}")
        except Exception as e:
            print(f"  ✗ Failed to generate histogram for {index_name}: {e}")
    
    return histograms


def print_ascii_histogram(
    hist_data: Dict,
    width: int = 50,
    height: int = 15
) -> None:
    """
    Print a simple ASCII histogram to the console.
    
    Args:
        hist_data: Histogram data from get_histogram_data().
        width: Width of the histogram in characters.
        height: Height of the histogram in lines.
    """
    buckets = hist_data.get("buckets", [])
    counts = hist_data.get("counts", [])
    band = hist_data.get("band", "Unknown")
    
    if not buckets or not counts:
        print(f"No data available for {band}")
        return
    
    max_count = max(counts) if counts else 1
    
    print(f"\n{'='*60}")
    print(f"  HISTOGRAM: {band}")
    print(f"{'='*60}")
    
    # Normalize counts to fit height
    normalized = [int((c / max_count) * height) for c in counts]
    
    # Print histogram rows (top to bottom)
    for row in range(height, 0, -1):
        line = "  │"
        for val in normalized:
            if val >= row:
                line += "█"
            else:
                line += " "
        print(line)
    
    # Print x-axis
    print("  └" + "─" * len(normalized))
    
    # Print range
    min_val = min(buckets) if buckets else 0
    max_val = max(buckets) if buckets else 1
    print(f"   {min_val:.2f}" + " " * (len(normalized) - 10) + f"{max_val:.2f}")
    
    # Print statistics
    total_pixels = sum(counts)
    weighted_sum = sum(b * c for b, c in zip(buckets, counts))
    mean_val = weighted_sum / total_pixels if total_pixels > 0 else 0
    
    print(f"\n  Total pixels: {total_pixels:,}")
    print(f"  Mean value: {mean_val:.4f}")
    print(f"{'='*60}\n")


def print_all_histograms(histograms: Dict[str, Dict]) -> None:
    """
    Print ASCII histograms for all indices.
    
    Args:
        histograms: Dictionary of histogram data from get_all_indices_histograms().
    """
    for index_name, hist_data in histograms.items():
        print_ascii_histogram(hist_data)


def generate_histogram_html(
    histograms: Dict[str, Dict],
    title: str = "Soil Index Histograms",
    images: Dict[str, str] = None
) -> str:
    """
    Generate an HTML page with interactive histograms using Chart.js.
    
    Args:
        histograms: Dictionary of histogram data.
        title: Page title.
        images: Dictionary of image name to base64 data URL or file path.
    
    Returns:
        str: HTML content.
    """
    charts_html = ""
    chart_scripts = ""
    images_html = ""
    
    colors = [
        'rgba(75, 192, 192, 0.7)',
        'rgba(255, 99, 132, 0.7)',
        'rgba(54, 162, 235, 0.7)',
        'rgba(255, 206, 86, 0.7)',
        'rgba(153, 102, 255, 0.7)',
        'rgba(255, 159, 64, 0.7)',
        'rgba(199, 199, 199, 0.7)',
        'rgba(83, 102, 255, 0.7)',
        'rgba(255, 99, 255, 0.7)',
        'rgba(99, 255, 132, 0.7)',
    ]
    
    # Generate images section if provided
    if images:
        images_html = """
        <h2 class="section-title">🛰️ Satellite Imagery</h2>
        <div class="images-grid">
        """
        for img_name, img_data in images.items():
            images_html += f"""
            <div class="image-container">
                <h3>{img_name}</h3>
                <img src="{img_data}" alt="{img_name}" />
            </div>
            """
        images_html += "</div>"
    
    for i, (index_name, hist_data) in enumerate(histograms.items()):
        buckets = hist_data.get("buckets", [])
        counts = hist_data.get("counts", [])
        
        if not buckets or not counts:
            continue
        
        # Calculate statistics
        total_pixels = sum(counts)
        weighted_sum = sum(b * c for b, c in zip(buckets, counts))
        mean_val = weighted_sum / total_pixels if total_pixels > 0 else 0
        
        canvas_id = f"chart_{index_name}"
        color = colors[i % len(colors)]
        
        charts_html += f"""
        <div class="chart-container">
            <canvas id="{canvas_id}"></canvas>
            <div class="stats">
                <span>Pixels: {total_pixels:,}</span>
                <span>Mean: {mean_val:.4f}</span>
            </div>
        </div>
        """
        
        # Format data for JavaScript
        labels = [f"{b:.3f}" for b in buckets]
        
        chart_scripts += f"""
        new Chart(document.getElementById('{canvas_id}'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: '{index_name}',
                    data: {json.dumps(counts)},
                    backgroundColor: '{color}',
                    borderColor: '{color.replace("0.7", "1")}',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: '{index_name} Distribution',
                        font: {{ size: 16 }}
                    }},
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        title: {{ display: true, text: 'Value' }},
                        ticks: {{ maxTicksLimit: 10 }}
                    }},
                    y: {{
                        title: {{ display: true, text: 'Pixel Count' }},
                        beginAtZero: true
                    }}
                }}
            }}
        }});
        """
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 10px;
            color: #00d4ff;
        }}
        .subtitle {{
            text-align: center;
            color: #888;
            margin-bottom: 30px;
        }}
        .section-title {{
            color: #00d4ff;
            margin: 40px 0 20px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #0f3460;
        }}
        .images-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            max-width: 1800px;
            margin: 0 auto 40px auto;
        }}
        .image-container {{
            background: #16213e;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        .image-container h3 {{
            color: #00d4ff;
            margin-bottom: 10px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .image-container img {{
            width: 100%;
            height: auto;
            border-radius: 5px;
            border: 1px solid #333;
        }}
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
            gap: 20px;
            max-width: 1800px;
            margin: 0 auto;
        }}
        .chart-container {{
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        .chart-container canvas {{
            max-height: 300px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #333;
            color: #aaa;
            font-size: 14px;
        }}
        .stats span {{
            background: #0f3460;
            padding: 5px 15px;
            border-radius: 5px;
        }}
        .legend {{
            max-width: 1800px;
            margin: 40px auto;
            background: #16213e;
            border-radius: 10px;
            padding: 20px;
        }}
        .legend h3 {{
            color: #00d4ff;
            margin-bottom: 15px;
        }}
        .legend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }}
        .legend-item {{
            background: #0f3460;
            padding: 10px 15px;
            border-radius: 5px;
        }}
        .legend-item strong {{
            color: #00d4ff;
        }}
        .legend-item p {{
            font-size: 13px;
            color: #aaa;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <h1>📊 {title}</h1>
    <p class="subtitle">Satellite imagery and soil quality index analysis</p>
    
    {images_html}
    
    <h2 class="section-title">📈 Index Histograms</h2>
    <div class="charts-grid">
        {charts_html}
    </div>
    
    <div class="legend">
        <h3>📖 Index Interpretation Guide</h3>
        <div class="legend-grid">
            <div class="legend-item">
                <strong>NDVI</strong> (Vegetation)
                <p>-1 to 0: Bare/water | 0-0.3: Sparse | 0.3-0.6: Moderate | 0.6-1: Dense healthy</p>
            </div>
            <div class="legend-item">
                <strong>NDSI</strong> (Soil)
                <p>Negative: Vegetation | Near 0: Mixed | Positive: Bare soil</p>
            </div>
            <div class="legend-item">
                <strong>NDMI</strong> (Moisture)
                <p>&lt;0: Dry stress | 0-0.2: Moderate | &gt;0.2: Good moisture</p>
            </div>
            <div class="legend-item">
                <strong>BI</strong> (Bare Index)
                <p>Negative: Vegetated | Positive: Exposed soil</p>
            </div>
            <div class="legend-item">
                <strong>BSI</strong> (Bare Soil Index)
                <p>&lt;80: Dense veg | 80-100: Sparse | &gt;100: Bare soil</p>
            </div>
            <div class="legend-item">
                <strong>CI</strong> (Color Index)
                <p>Negative: Dark/organic soil | Positive: Red/iron-rich soil</p>
            </div>
        </div>
    </div>
    
    <script>
        {chart_scripts}
    </script>
</body>
</html>
"""
    
    return html


def save_histogram_html(
    histograms: Dict[str, Dict],
    filepath: str,
    title: str = "Soil Index Histograms",
    images: Dict[str, str] = None
) -> str:
    """
    Save histograms as an HTML file.
    
    Args:
        histograms: Dictionary of histogram data.
        filepath: Output file path.
        title: Page title.
        images: Optional dictionary of image name to URL.
    
    Returns:
        str: Path to saved file.
    """
    html = generate_histogram_html(histograms, title, images)
    
    with open(filepath, 'w') as f:
        f.write(html)
    
    print(f"✓ Saved histogram visualization to {filepath}")
    return filepath


def save_histogram_csv(
    histograms: Dict[str, Dict],
    filepath: str
) -> str:
    """
    Save histogram data as CSV for further analysis.
    
    Args:
        histograms: Dictionary of histogram data.
        filepath: Output file path.
    
    Returns:
        str: Path to saved file.
    """
    lines = ["index,bucket_value,pixel_count"]
    
    for index_name, hist_data in histograms.items():
        buckets = hist_data.get("buckets", [])
        counts = hist_data.get("counts", [])
        
        for bucket, count in zip(buckets, counts):
            lines.append(f"{index_name},{bucket:.6f},{int(count)}")
    
    with open(filepath, 'w') as f:
        f.write('\n'.join(lines))
    
    print(f"✓ Saved histogram data to {filepath}")
    return filepath


def save_histogram_json(
    histograms: Dict[str, Dict],
    filepath: str
) -> str:
    """
    Save histogram data as JSON.
    
    Args:
        histograms: Dictionary of histogram data.
        filepath: Output file path.
    
    Returns:
        str: Path to saved file.
    """
    # Add statistics to each histogram
    output = {}
    for index_name, hist_data in histograms.items():
        buckets = hist_data.get("buckets", [])
        counts = hist_data.get("counts", [])
        
        total_pixels = sum(counts) if counts else 0
        weighted_sum = sum(b * c for b, c in zip(buckets, counts)) if buckets and counts else 0
        mean_val = weighted_sum / total_pixels if total_pixels > 0 else 0
        
        output[index_name] = {
            **hist_data,
            "statistics": {
                "total_pixels": total_pixels,
                "mean": mean_val,
                "min_observed": min(buckets) if buckets else None,
                "max_observed": max(buckets) if buckets else None,
            }
        }
    
    with open(filepath, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"✓ Saved histogram JSON to {filepath}")
    return filepath


def calculate_percentiles(
    image: ee.Image,
    band_name: str,
    roi: ee.Geometry,
    percentiles: List[int] = [5, 25, 50, 75, 95],
    scale: int = 30
) -> Dict[int, float]:
    """
    Calculate percentile values for a band.
    
    Args:
        image: Image containing the band.
        band_name: Name of the band.
        roi: Region of interest.
        percentiles: List of percentiles to calculate.
        scale: Scale in meters.
    
    Returns:
        dict: Percentile to value mapping.
    """
    band = image.select(band_name)
    
    result = band.reduceRegion(
        reducer=ee.Reducer.percentile(percentiles),
        geometry=roi,
        scale=scale,
        maxPixels=1e9
    ).getInfo()
    
    percentile_values = {}
    for p in percentiles:
        key = f"{band_name}_p{p}"
        percentile_values[p] = result.get(key)
    
    return percentile_values


def get_comprehensive_stats(
    image: ee.Image,
    band_name: str,
    roi: ee.Geometry,
    scale: int = 30
) -> Dict:
    """
    Get comprehensive statistics for a band including histogram and percentiles.
    
    Args:
        image: Image containing the band.
        band_name: Name of the band.
        roi: Region of interest.
        scale: Scale in meters.
    
    Returns:
        dict: Comprehensive statistics.
    """
    band = image.select(band_name)
    
    # Basic statistics
    stats = band.reduceRegion(
        reducer=ee.Reducer.mean()
            .combine(ee.Reducer.stdDev(), sharedInputs=True)
            .combine(ee.Reducer.minMax(), sharedInputs=True)
            .combine(ee.Reducer.count(), sharedInputs=True),
        geometry=roi,
        scale=scale,
        maxPixels=1e9
    ).getInfo()
    
    # Percentiles
    percentiles = calculate_percentiles(image, band_name, roi, [5, 25, 50, 75, 95], scale)
    
    return {
        "band": band_name,
        "mean": stats.get(f"{band_name}_mean"),
        "std_dev": stats.get(f"{band_name}_stdDev"),
        "min": stats.get(f"{band_name}_min"),
        "max": stats.get(f"{band_name}_max"),
        "count": stats.get(f"{band_name}_count"),
        "percentiles": percentiles
    }