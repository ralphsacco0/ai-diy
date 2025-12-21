"""
Scrum Sim V3 - AI-First Virtual Scrum Team
Minimal FastAPI backend with AI-driven persona responses.
"""

import os
from datetime import datetime
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import uvicorn

# Configure structured logging
from core.logging_config import get_structured_logger
logger = get_structured_logger("main")

app = FastAPI(title="Scrum Sim V3", description="AI-First Virtual Scrum Team")

# Import routers
from streaming import router as streaming_router
from api.models import router as models_router

from api.change_requests import router as change_requests_router
from api.testing import router as testing_router
from api.chat import router as chat_router
from api.vision import router as vision_router
from api.backlog import router as backlog_router
from api.scribe import router as scribe_router
from api.sprint import router as sprint_router

app.include_router(streaming_router)
app.include_router(models_router)
app.include_router(change_requests_router)
app.include_router(testing_router)
app.include_router(chat_router)
app.include_router(vision_router)
app.include_router(backlog_router)
app.include_router(scribe_router)
app.include_router(sprint_router)

# Serve static files
static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_index():
    """Serve the main UI."""
    return FileResponse("static/index.html")

@app.get("/progress_demo.html")
async def serve_progress_demo():
    """Serve the progress demo page."""
    return FileResponse("progress_demo.html")

@app.get("/api/env")
async def get_environment():
    """Returns the current application environment."""
    app_env = os.environ.get("APP_ENV", "DEV")
    return {"environment": app_env}

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "v3", "approach": "ai-first"}

if __name__ == "__main__":
    logger.info("Starting Scrum Sim V3 - AI-First approach")
    uvicorn.run(app, host="127.0.0.1", port=8000)
