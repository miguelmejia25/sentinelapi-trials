from flask import Flask, request, jsonify
from flask_cors import CORS
from flasgger import Swagger, swag_from
from datetime import datetime
from analysis import analyze_fun, AnalysisError
from auth import setup_gee

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Swagger configuration
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/apispec.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs"  # ← URL para ver la documentación
}

swagger_template = {
    "info": {
        "title": "Soil Analysis API",
        "description": "API para análisis de suelos usando imágenes satelitales de Sentinel-2",
        "version": "1.0.0"
    }
}

swagger = Swagger(app, config=swagger_config, template=swagger_template)

# Initialize GEE on startup
gee_connected = False
try:
    gee_connected = setup_gee()
except Exception as e:
    print(f"Error inicializando GEE: {e}")


def validate_analyze_request(data: dict) -> list:
    # ... tu código de validación existente ...
    pass


@app.route("/api/health", methods=["GET"])
def health():
    """
    Health check endpoint
    ---
    tags:
      - Health
    responses:
      200:
        description: Server status
        schema:
          type: object
          properties:
            status:
              type: string
              example: healthy
            gee_connected:
              type: boolean
              example: true
    """
    return jsonify({
        "status": "healthy",
        "gee_connected": gee_connected
    }), 200


@app.route("/api/analyze", methods=["POST"])
def analyze_endpoint():
    """
    Analyze soil quality from satellite imagery
    ---
    tags:
      - Analysis
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          required:
            - lat
            - lon
            - buffer
            - start_date
            - end_date
          properties:
            lat:
              type: number
              description: Latitude (-90 to 90)
              example: -1.841927
            lon:
              type: number
              description: Longitude (-180 to 180)
              example: -80.741419
            buffer:
              type: integer
              description: Buffer radius in meters (1 to 10000)
              example: 5000
            start_date:
              type: string
              description: Start date (YYYY-MM-DD)
              example: "2025-01-01"
            end_date:
              type: string
              description: End date (YYYY-MM-DD)
              example: "2025-06-01"
            cloud_threshold:
              type: integer
              description: Cloud probability threshold 0-100 (optional)
              example: 50
    responses:
      200:
        description: Analysis successful
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: true
            data:
              type: object
              properties:
                metadata:
                  type: object
                  properties:
                    coordinates:
                      type: object
                      properties:
                        lat:
                          type: number
                        lon:
                          type: number
                    buffer_m:
                      type: integer
                    date_range:
                      type: object
                      properties:
                        start:
                          type: string
                        end:
                          type: string
                    images_used:
                      type: integer
                    cloud_threshold:
                      type: integer
                images:
                  type: object
                  description: URLs to satellite imagery visualizations
                indices:
                  type: object
                  description: Soil quality indices statistics
                histograms:
                  type: object
                  description: Histogram data for each index
      400:
        description: Validation error
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
              example: "Validation failed"
            details:
              type: array
              items:
                type: string
      422:
        description: Analysis failed
        schema:
          type: object
          properties:
            success:
              type: boolean
              example: false
            error:
              type: string
            message:
              type: string
      503:
        description: GEE not connected
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
    cloud_threshold = data.get("cloud_threshold")
    start_date = data["start_date"]
    end_date = data["end_date"]
    
    # Run analysis
    try:
        results = analyze_fun(
            latitude=lat,
            longitude=lon,
            buffer_m=radius_m,
            cloud_max=cloud_threshold,
            start_date=start_date,
            end_date=end_date
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