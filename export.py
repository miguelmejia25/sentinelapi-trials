"""
Export module.
Handles exporting processed images to Google Drive, Cloud Storage, or as GEE assets.
"""

import ee
from typing import List, Optional, Dict
import time

import config
import compression


def export_to_drive(
    image: ee.Image,
    roi: ee.Geometry,
    description: str,
    folder: str = None,
    file_prefix: str = None,
    scale: int = None,
    bands: List[str] = None,
    crs: str = "EPSG:4326",
    start_task: bool = True
) -> ee.batch.Task:
    """
    Export image to Google Drive.
    
    Args:
        image: Image to export.
        roi: Region of interest.
        description: Task description (also used as filename).
        folder: Drive folder name. Defaults to config.DRIVE_FOLDER.
        file_prefix: Optional prefix for filename.
        scale: Export scale in meters. Defaults to config.EXPORT_SCALE.
        bands: Bands to export. If None, exports all.
        crs: Coordinate reference system.
        start_task: If True, starts the export task immediately.
    
    Returns:
        ee.batch.Task: The export task object.
    """
    folder = folder or config.DRIVE_FOLDER
    scale = scale or config.EXPORT_SCALE
    
    if bands:
        image = image.select(bands)
    
    # Build filename
    if file_prefix:
        filename = f"{file_prefix}_{description}"
    else:
        filename = description
    
    # Create export task
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=filename,
        folder=folder,
        region=roi,
        scale=scale,
        crs=crs,
        maxPixels=config.MAX_PIXELS,
        fileFormat="GeoTIFF",
        formatOptions={
            "cloudOptimized": True
        }
    )
    
    if start_task:
        task.start()
        print(f"✓ Started export task: {filename}")
        print(f"  Destination: Google Drive/{folder}")
        print(f"  Scale: {scale}m, CRS: {crs}")
    else:
        print(f"✓ Created export task: {filename} (not started)")
    
    return task


def export_to_cloud_storage(
    image: ee.Image,
    roi: ee.Geometry,
    description: str,
    bucket: str,
    file_prefix: str = None,
    scale: int = None,
    bands: List[str] = None,
    crs: str = "EPSG:4326",
    start_task: bool = True
) -> ee.batch.Task:
    """
    Export image to Google Cloud Storage.
    
    Args:
        image: Image to export.
        roi: Region of interest.
        description: Task description.
        bucket: GCS bucket name.
        file_prefix: Path prefix within bucket.
        scale: Export scale in meters.
        bands: Bands to export.
        crs: Coordinate reference system.
        start_task: If True, starts the export task immediately.
    
    Returns:
        ee.batch.Task: The export task object.
    """
    scale = scale or config.EXPORT_SCALE
    
    if bands:
        image = image.select(bands)
    
    task = ee.batch.Export.image.toCloudStorage(
        image=image,
        description=description,
        bucket=bucket,
        fileNamePrefix=file_prefix or description,
        region=roi,
        scale=scale,
        crs=crs,
        maxPixels=config.MAX_PIXELS,
        fileFormat="GeoTIFF",
        formatOptions={
            "cloudOptimized": True
        }
    )
    
    if start_task:
        task.start()
        print(f"✓ Started export task: {description}")
        print(f"  Destination: gs://{bucket}/{file_prefix or description}")
    
    return task


def export_as_asset(
    image: ee.Image,
    roi: ee.Geometry,
    asset_id: str,
    description: str = None,
    scale: int = None,
    bands: List[str] = None,
    start_task: bool = True
) -> ee.batch.Task:
    """
    Export image as Earth Engine asset.
    
    Assets can be loaded quickly in future GEE scripts without re-processing.
    
    Args:
        image: Image to export.
        roi: Region of interest.
        asset_id: Full asset ID (e.g., 'users/username/asset_name').
        description: Task description.
        scale: Export scale in meters.
        bands: Bands to export.
        start_task: If True, starts the export task immediately.
    
    Returns:
        ee.batch.Task: The export task object.
    """
    scale = scale or config.EXPORT_SCALE
    
    if bands:
        image = image.select(bands)
    
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description or asset_id.split("/")[-1],
        assetId=asset_id,
        region=roi,
        scale=scale,
        maxPixels=config.MAX_PIXELS
    )
    
    if start_task:
        task.start()
        print(f"✓ Started asset export: {asset_id}")
    
    return task


def export_multiple_products(
    composite: ee.Image,
    roi: ee.Geometry,
    prefix: str = None,
    folder: str = None,
    scale: int = None,
    products: List[str] = None
) -> Dict[str, ee.batch.Task]:
    """
    Export multiple derived products from a composite.
    
    Exports separate files for:
    - RGB visualization
    - Soil indices
    - Full spectral bands
    
    Args:
        composite: Processed composite image with all bands.
        roi: Region of interest.
        prefix: Filename prefix. Defaults to config.FILE_PREFIX.
        folder: Drive folder. Defaults to config.DRIVE_FOLDER.
        scale: Export scale. Defaults to config.EXPORT_SCALE.
        products: List of products to export. Options:
                 "rgb", "agriculture", "soil_vis", "indices", "spectral"
    
    Returns:
        dict: Dictionary of task name to task object.
    """
    prefix = prefix or config.FILE_PREFIX
    folder = folder or config.DRIVE_FOLDER
    scale = scale or config.EXPORT_SCALE
    products = products or ["rgb", "indices", "spectral"]
    
    tasks = {}
    
    if "rgb" in products:
        # True color RGB
        rgb = compression.prepare_rgb_visualization(
            composite, 
            config.VIS_BANDS_RGB
        )
        tasks["rgb"] = export_to_drive(
            rgb, roi, 
            f"{prefix}_rgb",
            folder=folder, 
            scale=scale
        )
    
    if "agriculture" in products:
        # False color for agriculture
        agri = compression.prepare_rgb_visualization(
            composite,
            config.VIS_BANDS_AGRICULTURE,
            max_val=5000
        )
        tasks["agriculture"] = export_to_drive(
            agri, roi,
            f"{prefix}_agriculture",
            folder=folder,
            scale=scale
        )
    
    if "soil_vis" in products:
        # SWIR composite for soil/geology
        soil_vis = compression.prepare_rgb_visualization(
            composite,
            config.VIS_BANDS_SOIL,
            max_val=5000
        )
        tasks["soil_vis"] = export_to_drive(
            soil_vis, roi,
            f"{prefix}_soil_swir",
            folder=folder,
            scale=scale
        )
    
    if "indices" in products:
        # Soil indices as float
        index_bands = [b for b in config.SOIL_INDICES 
                      if b in composite.bandNames().getInfo()]
        if index_bands:
            indices = composite.select(index_bands).toFloat()
            tasks["indices"] = export_to_drive(
                indices, roi,
                f"{prefix}_soil_indices",
                folder=folder,
                scale=scale
            )
    
    if "spectral" in products:
        # All spectral bands
        spectral_bands = ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B8A", "B11", "B12"]
        available_bands = [b for b in spectral_bands 
                         if b in composite.bandNames().getInfo()]
        if available_bands:
            spectral = composite.select(available_bands).toFloat()
            tasks["spectral"] = export_to_drive(
                spectral, roi,
                f"{prefix}_spectral",
                folder=folder,
                scale=scale
            )
    
    print(f"\n✓ Started {len(tasks)} export tasks")
    return tasks


def check_task_status(task: ee.batch.Task) -> dict:
    """
    Check status of an export task.
    
    Args:
        task: Export task to check.
    
    Returns:
        dict: Status information.
    """
    status = task.status()
    return {
        "id": status["id"],
        "state": status["state"],
        "description": status["description"],
        "creation_time": status.get("creation_timestamp_ms"),
        "start_time": status.get("start_timestamp_ms"),
        "update_time": status.get("update_timestamp_ms"),
        "error_message": status.get("error_message"),
    }


def wait_for_task(
    task: ee.batch.Task,
    timeout_minutes: int = 30,
    poll_interval: int = 30
) -> bool:
    """
    Wait for an export task to complete.
    
    Args:
        task: Export task to wait for.
        timeout_minutes: Maximum wait time in minutes.
        poll_interval: Seconds between status checks.
    
    Returns:
        bool: True if completed successfully, False otherwise.
    """
    print(f"Waiting for task: {task.status()['description']}")
    
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    while True:
        status = task.status()
        state = status["state"]
        
        if state == "COMPLETED":
            elapsed = (time.time() - start_time) / 60
            print(f"✓ Task completed in {elapsed:.1f} minutes")
            return True
        
        elif state == "FAILED":
            print(f"✗ Task failed: {status.get('error_message', 'Unknown error')}")
            return False
        
        elif state == "CANCELLED":
            print("✗ Task was cancelled")
            return False
        
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"✗ Timeout after {timeout_minutes} minutes")
            return False
        
        remaining = (timeout_seconds - elapsed) / 60
        print(f"  Status: {state} (waiting... {remaining:.0f} min remaining)")
        time.sleep(poll_interval)


def wait_for_all_tasks(
    tasks: Dict[str, ee.batch.Task],
    timeout_minutes: int = 60,
    poll_interval: int = 30
) -> Dict[str, bool]:
    """
    Wait for multiple export tasks to complete.
    
    Args:
        tasks: Dictionary of task name to task object.
        timeout_minutes: Maximum total wait time.
        poll_interval: Seconds between status checks.
    
    Returns:
        dict: Task name to success status.
    """
    print(f"\nMonitoring {len(tasks)} export tasks...")
    
    results = {}
    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    
    pending = set(tasks.keys())
    
    while pending:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            print(f"\n✗ Timeout after {timeout_minutes} minutes")
            for name in pending:
                results[name] = False
            break
        
        for name in list(pending):
            status = tasks[name].status()
            state = status["state"]
            
            if state == "COMPLETED":
                print(f"  ✓ {name}: completed")
                results[name] = True
                pending.remove(name)
            
            elif state == "FAILED":
                print(f"  ✗ {name}: failed - {status.get('error_message', 'Unknown')}")
                results[name] = False
                pending.remove(name)
            
            elif state == "CANCELLED":
                print(f"  ✗ {name}: cancelled")
                results[name] = False
                pending.remove(name)
        
        if pending:
            remaining = (timeout_seconds - elapsed) / 60
            print(f"  {len(pending)} tasks pending... ({remaining:.0f} min remaining)")
            time.sleep(poll_interval)
    
    completed = sum(1 for v in results.values() if v)
    print(f"\n✓ Completed: {completed}/{len(tasks)} tasks")
    
    return results


def list_running_tasks() -> List[dict]:
    """
    List all currently running export tasks.
    
    Returns:
        list: List of task status dictionaries.
    """
    tasks = ee.batch.Task.list()
    running = [t for t in tasks if t.status()["state"] in ["READY", "RUNNING"]]
    
    print(f"\nRunning tasks: {len(running)}")
    for task in running:
        status = task.status()
        print(f"  - {status['description']}: {status['state']}")
    
    return [t.status() for t in running]


def cancel_all_tasks():
    """
    Cancel all pending and running tasks.
    """
    tasks = ee.batch.Task.list()
    cancelled = 0
    
    for task in tasks:
        state = task.status()["state"]
        if state in ["READY", "RUNNING"]:
            task.cancel()
            cancelled += 1
    
    print(f"✓ Cancelled {cancelled} tasks")