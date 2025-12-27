"""
Download API for generated applications.
Provides direct browser download of packaged apps.
"""

import os
import tempfile
import zipfile
from pathlib import Path
from fastapi import HTTPException, Response, APIRouter
from fastapi.responses import StreamingResponse
import io

from api.conventions import create_success_response, create_error_response, HTTP_STATUS_MAP, ApiErrorCode
from api.conventions import log_api_call

# Import paths
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.test_app_downloader import TestAppDownloader

router = APIRouter()

@router.get("/app")
async def download_generated_app():
    """Download the generated application as a ZIP file."""
    try:
        log_api_call(
            route="/api/download/app",
            action="download",
            id="app",
            status="start"
        )
        
        # Initialize downloader
        downloader = TestAppDownloader()
        
        # Create ZIP package
        zip_path = downloader.download_app()
        
        # Verify package
        verification = downloader.verify_package(zip_path)
        
        if not verification.get("valid_zip", False):
            raise HTTPException(
                status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
                detail=create_error_response(
                    "Failed to create valid application package",
                    ApiErrorCode.SERVER_ERROR
                ).model_dump()
            )
        
        # Read ZIP file for streaming
        def generate_zip():
            with open(zip_path, 'rb') as f:
                while chunk := f.read(8192):
                    yield chunk
        
        # Clean up test files
        downloader.cleanup_test_files()
        
        # Get filename for download
        filename = zip_path.name
        
        log_api_call(
            route="/api/download/app",
            action="download",
            id="app",
            status="success"
        )
        
        # Stream ZIP file to browser
        return StreamingResponse(
            generate_zip(),
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_api_call(
            route="/api/download/app",
            action="download",
            id="app",
            status="error"
        )
        raise HTTPException(
            status_code=HTTP_STATUS_MAP[ApiErrorCode.SERVER_ERROR],
            detail=create_error_response(
                f"Failed to download application: {str(e)}",
                ApiErrorCode.SERVER_ERROR
            ).model_dump()
        )
