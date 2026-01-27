#!/usr/bin/env python3
"""
Plantation Soil Analysis System
Main orchestration script for analyzing soil quality from satellite imagery.

Usage:
    python main.py                    # Run full pipeline with default config
    python main.py --info             # Show collection info without processing
    python main.py --export           # Run pipeline and export results
    python main.py --stats            # Calculate and display soil statistics

Author: Plantation Soil Analysis System
Location: Coastal Ecuador (Manabí Province)
"""

import argparse
import sys

# Import all modules
import config
from auth import setup_gee
from retrieval import (
    create_region_of_interest,
    get_sentinel2_collection,
    get_s2_cloudless_collection,
    get_sentinel1_collection,
    print_collection_info
)
from cloud import apply_comprehensive_cloud_mask
from compositing import create_composite, create_multi_composite
from soil import (
    calculate_selected_indices,
    get_soil_statistics,
    print_soil_analysis,
    create_bare_soil_mask
)
from compression_img import estimate_file_size, print_export_summary
from export import (
    export_to_drive,
    export_multiple_products,
    wait_for_all_tasks,
    list_running_tasks
)
from visualization import (
    get_all_indices_histograms,
    print_all_histograms,
    save_histogram_html,
    save_histogram_csv,
    save_histogram_json,
    get_all_visualization_urls
)


def print_header():
    """Print application header."""
    print("\n" + "=" * 60)
    print("  PLANTATION SOIL ANALYSIS SYSTEM")
    print("  Satellite-based soil quality assessment")
    print("=" * 60)
    print(f"\n  Location: {config.LATITUDE}, {config.LONGITUDE}")
    print(f"  Buffer: {config.BUFFER_RADIUS_M}m radius")
    print(f"  Date range: {config.START_DATE} to {config.END_DATE}")
    print(f"  Cloud threshold: {config.CLOUD_PROBABILITY_THRESHOLD}%")
    print("\n" + "-" * 60 + "\n")


def run_info_mode(roi):
    """Display information about available imagery without processing."""
    print("\n[INFO MODE] Checking available imagery...\n")
    
    # Get Sentinel-2 collection info
    s2_collection, s2_count = get_sentinel2_collection(roi)
    print_collection_info(s2_collection, "Sentinel-2")
    
    # Get Sentinel-1 collection info
    s1_collection, s1_count = get_sentinel1_collection(roi)
    print_collection_info(s1_collection, "Sentinel-1 SAR")
    
    # Summary
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    print(f"  Sentinel-2 images: {s2_count}")
    print(f"  Sentinel-1 images: {s1_count}")
    
    if s2_count == 0:
        print("\n  ⚠ No Sentinel-2 images found!")
        print("  Try adjusting date range or cloud threshold.")
    elif s2_count < 5:
        print("\n  ⚠ Few images available - composite may have gaps")
    else:
        print("\n  ✓ Sufficient imagery for analysis")


def run_pipeline(roi, calculate_stats=True, do_export=False, wait_for_export=False, generate_histograms=False):
    """
    Run the full processing pipeline.
    
    Args:
        roi: Region of interest geometry.
        calculate_stats: Whether to calculate soil statistics.
        do_export: Whether to export results to Drive.
        wait_for_export: Whether to wait for exports to complete.
        generate_histograms: Whether to generate histogram visualizations.
    
    Returns:
        dict: Results including composite, indices, and statistics.
    """
    results = {}
    
    # Step 1: Retrieve imagery
    print("\n[1/5] Retrieving satellite imagery...")
    print("-" * 40)
    
    s2_collection, s2_count = get_sentinel2_collection(roi)
    
    if s2_count == 0:
        print("\n✗ No imagery found for specified parameters.")
        print("  Suggestions:")
        print("  - Extend the date range")
        print("  - Increase MAX_SCENE_CLOUD_PERCENT in config.py")
        return None
    
    s2_cloudless = get_s2_cloudless_collection(roi)
    
    results["image_count"] = s2_count
    
    # Step 2: Apply cloud masking
    print("\n[2/5] Applying cloud masking...")
    print("-" * 40)
    
    masked_collection = apply_comprehensive_cloud_mask(
        s2_collection,
        s2_cloudless,
        cloud_threshold=config.CLOUD_PROBABILITY_THRESHOLD
    )
    
    # Step 3: Create composite
    print("\n[3/5] Creating temporal composite...")
    print("-" * 40)
    
    composite = create_composite(
        masked_collection,
        method=config.COMPOSITE_METHOD
    )
    
    # Clip to ROI
    composite = composite.clip(roi)
    results["composite"] = composite
    
    # Step 4: Calculate soil indices
    print("\n[4/5] Calculating soil indices...")
    print("-" * 40)
    
    composite_with_indices = calculate_selected_indices(
        composite,
        indices=config.SOIL_INDICES
    )
    results["composite_with_indices"] = composite_with_indices
    
    # Create bare soil mask
    bare_soil_mask = create_bare_soil_mask(composite_with_indices)
    results["bare_soil_mask"] = bare_soil_mask
    
    # Step 5: Calculate statistics
    if calculate_stats:
        print("\n[5/5] Calculating soil statistics...")
        print("-" * 40)
        
        stats = get_soil_statistics(
            composite_with_indices,
            roi,
            indices=config.SOIL_INDICES
        )
        results["statistics"] = stats
        
        # Print analysis report
        print_soil_analysis(stats, f"Coastal Ecuador ({config.LATITUDE}, {config.LONGITUDE})")
    
    # Generate histograms if requested
    if generate_histograms:
        print("\n[HISTOGRAMS] Generating index histograms...")
        print("-" * 40)
        
        histograms = get_all_indices_histograms(
            composite_with_indices,
            roi,
            indices=config.SOIL_INDICES
        )
        results["histograms"] = histograms
        
        # Print ASCII histograms to console
        print_all_histograms(histograms)
        
        # Generate thumbnail images
        print("\n[IMAGES] Generating visualization thumbnails...")
        print("-" * 40)
        
        image_urls = get_all_visualization_urls(composite, roi, dimensions=600)
        results["image_urls"] = image_urls
        
        # Save as HTML with images, CSV, and JSON
        save_histogram_html(
            histograms, 
            "histograms.html", 
            f"Soil Analysis - {config.LATITUDE}, {config.LONGITUDE}",
            images=image_urls
        )
        save_histogram_csv(histograms, "histograms.csv")
        save_histogram_json(histograms, "histograms.json")
    
    # Export if requested
    if do_export:
        print("\n[EXPORT] Exporting results to Google Drive...")
        print("-" * 40)
        
        # Estimate file sizes
        size_est = estimate_file_size(
            composite_with_indices,
            roi,
            scale=config.EXPORT_SCALE
        )
        print(f"  Estimated export size: ~{size_est['estimated_mb']:.1f} MB")
        
        # Export multiple products
        tasks = export_multiple_products(
            composite_with_indices,
            roi,
            prefix=config.FILE_PREFIX,
            products=["rgb", "soil_vis", "indices", "spectral"]
        )
        results["export_tasks"] = tasks
        
        if wait_for_export:
            print("\nWaiting for exports to complete...")
            export_results = wait_for_all_tasks(tasks, timeout_minutes=30)
            results["export_results"] = export_results
    
    print("\n" + "=" * 60)
    print("  PROCESSING COMPLETE")
    print("=" * 60 + "\n")
    
    return results


def main():
    """Main entry point."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Plantation Soil Analysis System"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Show imagery info without processing"
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export results to Google Drive"
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for exports to complete"
    )
    parser.add_argument(
        "--no-stats",
        action="store_true",
        help="Skip statistics calculation"
    )
    parser.add_argument(
        "--histograms",
        action="store_true",
        help="Generate histogram visualizations"
    )
    parser.add_argument(
        "--lat",
        type=float,
        help="Override latitude"
    )
    parser.add_argument(
        "--lon",
        type=float,
        help="Override longitude"
    )
    parser.add_argument(
        "--buffer",
        type=int,
        help="Override buffer radius in meters"
    )
    
    args = parser.parse_args()
    
    # Print header
    print_header()
    
    # Setup GEE
    print("[SETUP] Initializing Google Earth Engine...")
    print("-" * 40)
    
    if not setup_gee():
        print("\n✗ Failed to initialize GEE. Exiting.")
        sys.exit(1)
    
    # Create ROI (with optional overrides)
    lat = args.lat or config.LATITUDE
    lon = args.lon or config.LONGITUDE
    buffer = args.buffer or config.BUFFER_RADIUS_M
    
    roi = create_region_of_interest(lat, lon, buffer)
    
    # Run appropriate mode
    if args.info:
        run_info_mode(roi)
    else:
        results = run_pipeline(
            roi,
            calculate_stats=not args.no_stats,
            do_export=args.export,
            wait_for_export=args.wait,
            generate_histograms=args.histograms
        )
        
        if results is None:
            sys.exit(1)
        
        # Print summary
        print("Results summary:")
        print(f"  - Images processed: {results.get('image_count', 'N/A')}")
        print(f"  - Indices calculated: {len(config.SOIL_INDICES)}")
        
        if "statistics" in results:
            print(f"  - Statistics computed: Yes")
        
        if "histograms" in results:
            print(f"  - Histograms generated: Yes (histograms.html, .csv, .json)")
        
        if "export_tasks" in results:
            print(f"  - Exports started: {len(results['export_tasks'])}")
    
    print("\nDone!")


if __name__ == "__main__":
    main()