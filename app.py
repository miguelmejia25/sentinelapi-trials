from flask import Flask, request, jsonify
from flask_cors import CORS
from analysis import analyze_fun, AnalysisError
from auth import setup_gee

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize GEE on startup
gee_connected = False
try:
    gee_connected = setup_gee()
except Exception as e:
    print(f"Error inicializando GEE: {e}")



def validate_analyze_request(data: dict) -> list:
    """
    Validate the analyze request data.
    
    Args:
        data: Request JSON data
    
    Returns:
        list: List of error messages (empty if valid)
    """
    errors = []
    
    # Check if data exists
    if not data:
        return ["Request body is required"]
    
    # Validate lat
    if "lat" not in data:
        errors.append("lat is required")
    elif not isinstance(data["lat"], (int, float)):
        errors.append("lat must be a number")
    elif data["lat"] < -90 or data["lat"] > 90:
        errors.append("lat must be between -90 and 90")
    
    # Validate lon
    if "lon" not in data:
        errors.append("lon is required")
    elif not isinstance(data["lon"], (int, float)):
        errors.append("lon must be a number")
    elif data["lon"] < -180 or data["lon"] > 180:
        errors.append("lon must be between -180 and 180")
    
    # Validate radius_km
    if "buffer" not in data:
        errors.append("buffer is required")
    elif not isinstance(data["buffer"], (int, float)):
        errors.append("buffer must be a number")
    elif data["buffer"] < 1 or data["buffer"] > 10000:
        errors.append("radius_km must be between 1 and 10000")
    
    # Validate optional cloud_threshold
    if "cloud_threshold" in data:
        if not isinstance(data["cloud_threshold"], (int, float)):
            errors.append("cloud_threshold must be a number")
        elif data["cloud_threshold"] < 0 or data["cloud_threshold"] > 100:
            errors.append("cloud_threshold must be between 0 and 100")
    
    return errors




@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "gee_connected": gee_connected
    }), 200


@app.route("/api/analyze", methods=["POST"])
def analyze_endpoint():
    """
    Main analysis endpoint.
    
    Expects JSON body:
    {
        "lat": float,
        "lon": float,
        "radius_km": float,
        "cloud_threshold": int (optional)
    }
    """
    
    # Get JSON data
    try:
        data = request.get_json()
    except Exception:
        return jsonify({
            "success": False,
            "error": "Invalid JSON in request body"
        }), 400
    
    # Validate inputs
    validation_errors = validate_analyze_request(data)
    if validation_errors:
        return jsonify({
            "success": False,
            "error": "Validation failed",
            "details": validation_errors
        }), 400
    
    # Check GEE connection
    if not gee_connected:
        return jsonify({
            "success": False,
            "error": "Google Earth Engine is not connected"
        }), 503
    
    # Extract parameters
    lat = data["lat"]
    lon = data["lon"]
    radius_m = int(data["buffer"])  
    cloud_threshold = data.get("cloud_threshold")  # Optional
    
    # Run analysis
    try:
        results = analyze_fun(
            latitude=lat,
            longitude=lon,
            buffer_m=radius_m,
            cloud_max=cloud_threshold
        )
        
        return jsonify({
            "success": True,
            "data": results
        }), 200
        
    except AnalysisError as e:
        return jsonify({
            "success": False,
            "error": "Analysis failed",
            "message": str(e)
        }), 422
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "message": str(e)
        }), 500




@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": "Bad request",
        "message": str(error)
    }), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Not found",
        "message": "The requested endpoint does not exist"
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "message": "An unexpected error occurred"
    }), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)