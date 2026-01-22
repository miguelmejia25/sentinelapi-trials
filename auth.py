"""
Google Earth Engine authentication module.
Handles authentication and initialization of the GEE API.
"""

import ee
import os


# =============================================================================
# CONFIGURATION - Update these for service account auth
# =============================================================================

# Path to service account JSON key file (set to None for interactive auth)
SERVICE_ACCOUNT_KEY_FILE = os.environ.get("GEE_KEY_FILE", None)

# Service account email (only needed if using service account)
SERVICE_ACCOUNT_EMAIL = os.environ.get("GEE_SERVICE_ACCOUNT", None)

# Default project ID
DEFAULT_PROJECT_ID = os.environ.get("GEE_PROJECT", "enginetrial")


def authenticate_with_service_account(
    key_file: str,
    service_account_email: str = None
) -> bool:
    """
    Authenticate using a service account.
    
    This is the recommended method for:
    - GitHub Codespaces
    - CI/CD pipelines
    - Server deployments
    - Any environment without a browser
    
    Args:
        key_file: Path to the service account JSON key file.
        service_account_email: Service account email. If None, extracted from key file.
    
    Returns:
        bool: True if authentication successful.
    """
    try:
        if service_account_email:
            credentials = ee.ServiceAccountCredentials(
                email=service_account_email,
                key_file=key_file
            )
        else:
            credentials = ee.ServiceAccountCredentials(
                email=None,
                key_file=key_file
            )
        
        ee.Initialize(credentials, project=DEFAULT_PROJECT_ID)
        print(f"✓ Authenticated with service account")
        print(f"  Project: {DEFAULT_PROJECT_ID}")
        return True
    except Exception as e:
        print(f"✗ Service account authentication failed: {e}")
        return False


def authenticate_gee(project_id: str = None) -> bool:
    """
    Authenticate with Google Earth Engine.
    
    On first run, this will open a browser window for OAuth authentication.
    Subsequent runs use cached credentials.
    
    Args:
        project_id: Optional GEE cloud project ID. Required for some operations.
                   If None, uses default project.
    
    Returns:
        bool: True if authentication successful, False otherwise.
    
    Usage:
        from auth import authenticate_gee, initialize_gee
        
        if authenticate_gee():
            initialize_gee()
            # Now you can use ee functions
    """
    try:
        # Try to authenticate
        # This will use existing credentials if available,
        # otherwise opens browser for OAuth flow
        ee.Authenticate()
        print("✓ GEE authentication successful")
        return True
    except Exception as e:
        print(f"✗ GEE authentication failed: {e}")
        print("\nTo authenticate manually, run:")
        print("  earthengine authenticate")
        return False


def initialize_gee(project_id: str = None, high_volume: bool = False) -> bool:
    """
    Initialize the Earth Engine API.
    
    Must be called after authentication and before using any ee functions.
    
    Args:
        project_id: Cloud project ID. Required for high-volume endpoint.
        high_volume: If True, use high-volume endpoint (requires project_id).
    
    Returns:
        bool: True if initialization successful, False otherwise.
    """
    try:
        if high_volume and project_id:
            # High-volume endpoint for heavy processing
            ee.Initialize(
                project=project_id,
                opt_url="https://earthengine-highvolume.googleapis.com"
            )
            print(f"✓ GEE initialized with high-volume endpoint (project: {project_id})")
        elif project_id:
            # Standard endpoint with project
            ee.Initialize(project=project_id)
            print(f"✓ GEE initialized (project: {project_id})")
        else:
            # Standard endpoint, default project
            ee.Initialize()
            print("✓ GEE initialized (default project)")
        return True
    except Exception as e:
        print(f"✗ GEE initialization failed: {e}")
        print("\nMake sure you have:")
        print("  1. Authenticated with: earthengine authenticate")
        print("  2. A valid Earth Engine account")
        print("  3. (Optional) A Google Cloud project linked to EE")
        return False


def check_gee_connection() -> bool:
    """
    Verify GEE connection is working by running a simple operation.
    
    Returns:
        bool: True if connection is working, False otherwise.
    """
    try:
        # Simple test: get info about a known asset
        test = ee.Number(1).add(1).getInfo()
        if test == 2:
            print("✓ GEE connection verified")
            return True
        else:
            print("✗ GEE connection test returned unexpected result")
            return False
    except Exception as e:
        print(f"✗ GEE connection test failed: {e}")
        return False


def setup_gee(project_id: str = None, key_file: str = None) -> bool:
    """
    Complete GEE setup: authenticate, initialize, and verify connection.
    
    This is the main function to call at the start of your script.
    
    Args:
        project_id: Optional cloud project ID.
        key_file: Optional path to service account JSON key file.
                 If provided, uses service account auth.
                 Can also be set via GEE_KEY_FILE environment variable.
    
    Returns:
        bool: True if all steps successful, False otherwise.
    
    Usage:
        # Interactive auth (browser)
        from auth import setup_gee
        if setup_gee():
            # Ready to use GEE
            pass
        
        # Service account auth (no browser)
        if setup_gee(key_file='path/to/key.json'):
            # Ready to use GEE
            pass
    """
    print("Setting up Google Earth Engine...")
    print("-" * 40)
    
    # Check for service account key file
    key_file = key_file or SERVICE_ACCOUNT_KEY_FILE
    
    if key_file and os.path.exists(key_file):
        # Use service account authentication
        print("Using service account authentication...")
        if not authenticate_with_service_account(key_file, SERVICE_ACCOUNT_EMAIL):
            return False
    else:
        # Use interactive authentication
        if not authenticate_gee():
            return False
        
        if not initialize_gee(project_id or DEFAULT_PROJECT_ID):
            return False
    
    if not check_gee_connection():
        return False
    
    print("-" * 40)
    print("✓ GEE setup complete\n")
    return True


if __name__ == "__main__":
    # Test authentication when run directly
    setup_gee()