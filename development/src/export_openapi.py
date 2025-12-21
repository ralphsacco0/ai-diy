#!/usr/bin/env python3
"""
Export FastAPI OpenAPI spec to static/apidocs/api.json
"""
import json
import os
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from main import app

def export_openapi_spec():
    """Export the FastAPI OpenAPI specification to a JSON file."""
    
    # Get the OpenAPI schema
    openapi_schema = app.openapi()
    
    # Ensure the output directory exists
    output_dir = Path(__file__).parent / "static" / "apidocs"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write the schema to api.json
    output_file = output_dir / "api.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✅ OpenAPI spec exported to: {output_file}")
    print(f"📊 API contains {len(openapi_schema.get('paths', {}))} endpoints")
    
    # Print summary of endpoints
    paths = openapi_schema.get('paths', {})
    if paths:
        print("\n📋 API Endpoints:")
        for path, methods in paths.items():
            for method in methods.keys():
                if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    print(f"  {method.upper()} {path}")

if __name__ == "__main__":
    export_openapi_spec()
