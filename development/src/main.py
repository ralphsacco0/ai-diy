"""
AI-DIY Application - Consolidated Entry Point

Combines all enhanced features from Phases 2-5:
- Phase 2: Fail-Fast Configuration (optional, graceful degradation)
- Phase 3: Data Management (integrated)
- Phase 4: Structured Logging (optional, graceful degradation)
- Phase 5: Security Middleware (optional, graceful degradation)

Enhanced features activate automatically if dependencies are available.
Falls back to basic functionality if dependencies are missing.
"""

import os
import sys
import signal
import logging
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Track which enhanced features are available
FEATURES = {
    "config_manager": False,
    "logging_middleware": False,
    "security_middleware": False,
    "data_manager": False
}

# Try to import and validate configuration (Phase 2: Fail-Fast)
try:
    from config_manager import validate_startup_configuration, config_manager
    validate_startup_configuration()
    app_config = config_manager.get_app_config()
    models_config = config_manager.get_models_config()
    FEATURES["config_manager"] = True
    print("✅ Fail-fast configuration loaded")
except ImportError:
    print("⚠️  Config manager not available - using defaults")
    # Fallback configuration
    class AppConfig:
        log_level = os.environ.get("LOG_LEVEL", "INFO")
        data_root = os.environ.get("DATA_ROOT", "static")
        host = "0.0.0.0"
        port = 8000
        is_production = os.environ.get("PRODUCTION", "false").lower() == "true" or os.environ.get("APP_ENV", "DEV") == "STABLE"
    
    class ModelsConfig:
        favorites = []
        default = None
        last_used = None
    
    app_config = AppConfig()
    models_config = ModelsConfig()
except ValueError as e:
    print(f"❌ Configuration validation failed: {e}")
    print("\n🔧 Required environment variables:")
    print("  - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR)")
    print("  - DATA_ROOT (path to data directory)")
    sys.exit(1)

# Setup logging
log_level = getattr(logging, app_config.log_level.upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Try to import structured logging middleware (Phase 4)
try:
    from logging_middleware import setup_structured_logging, logging_middleware
    setup_structured_logging(app_config)
    FEATURES["logging_middleware"] = True
    logger.info("✅ Structured logging middleware loaded")
except ImportError:
    logger.warning("⚠️  Logging middleware not available - using basic logging")
    logging_middleware = None

# Try to import security middleware (Phase 5)
try:
    from security_middleware import (
        SecurityMiddleware, InputValidationMiddleware,
        SecurityConfig, security_audit, rate_limiter
    )
    from security_utils import SecurityUtils, FileSecurityValidator, security_logger
    FEATURES["security_middleware"] = True
    logger.info("✅ Security middleware loaded")
except ImportError:
    logger.warning("⚠️  Security middleware not available - running without enhanced security")
    SecurityMiddleware = None
    InputValidationMiddleware = None

# Try to import data manager (Phase 3)
try:
    from data_manager import data_manager
    FEATURES["data_manager"] = True
    logger.info("✅ Data manager loaded")
except ImportError:
    logger.warning("⚠️  Data manager not available")
    data_manager = None

# Configure structured logging from core
from core.logging_config import get_structured_logger
structured_logger = get_structured_logger("main")

# Create FastAPI application
app = FastAPI(
    title="AI-DIY: Scrum Sim V3",
    description="AI-First Virtual Scrum Team with Enhanced Features",
    version="1.0.0"
)

# Add HTTP Basic Authentication (always enabled in production)
from auth_middleware import BasicAuthMiddleware
if app_config.is_production or os.environ.get("ENABLE_BASIC_AUTH") == "true":
    app.add_middleware(BasicAuthMiddleware)
    logger.info("🔒 HTTP Basic Auth enabled")

# Add CORS middleware
if not app_config.is_production:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("Development CORS enabled")

# Add security middleware if available (Phase 5)
if FEATURES["security_middleware"]:
    app.add_middleware(SecurityMiddleware)
    app.add_middleware(InputValidationMiddleware)
    logger.info("🔒 Security middleware active")

# Add structured logging middleware if available (Phase 4)
if FEATURES["logging_middleware"] and logging_middleware:
    app.middleware("http")(logging_middleware)
    logger.info("📊 Structured logging middleware active")

# Import and include routers
from streaming import router as streaming_router
from api.models import router as models_router
from api.change_requests import router as change_requests_router
from api.testing import router as testing_router
from api.chat import router as chat_router
from api.vision import router as vision_router
from api.backlog import router as backlog_router
from api.scribe import router as scribe_router
from api.sprint import router as sprint_router
from api.sandbox import router as sandbox_router
from api.session import router as session_router

app.include_router(streaming_router)
app.include_router(models_router)
app.include_router(change_requests_router)
app.include_router(testing_router)
app.include_router(chat_router)
app.include_router(vision_router)
app.include_router(backlog_router)
app.include_router(scribe_router)
app.include_router(sprint_router)
app.include_router(sandbox_router)
app.include_router(session_router)

logger.info("✅ All API routers loaded successfully")

# App control endpoint
from pydantic import BaseModel as PydanticBaseModel
import subprocess
import asyncio
import signal
from core.project_metadata import get_project_name_safe

# Module-level variable to track the running generated app process
_generated_app_process = None

class AppControlRequest(PydanticBaseModel):
    action: str  # "start" or "stop"

@app.post("/api/control-app")
async def control_app(request: AppControlRequest):
    """Start or stop the generated application.

    Works on both Mac and Railway (Linux) by using Python subprocess directly
    instead of shell scripts. Uses get_project_name_safe() to find the project.
    """
    global _generated_app_process

    try:
        # Get project name dynamically
        project_name = get_project_name_safe()
        if not project_name or project_name in ("Unknown", "default_project"):
            raise HTTPException(status_code=400, detail="No approved project found. Complete a sprint first.")

        # Project is in execution sandbox
        sandbox_base = Path(__file__).parent / "static" / "appdocs" / "execution-sandbox" / "client-projects"
        project_dir = sandbox_base / project_name

        if not project_dir.exists():
            raise HTTPException(status_code=404, detail=f"Project directory not found: {project_name}")

        # Check for package.json to verify it's a valid Node project
        if not (project_dir / "package.json").exists():
            raise HTTPException(status_code=400, detail=f"No package.json found in {project_name}. Sprint may not have completed.")

        if request.action == "start":
            # Ruthlessly kill ANY process on port 3000 first (manual, orphaned, or managed)
            logger.info("Ruthlessly clearing port 3000 before starting app")
            
            # Kill Python-managed process and its entire process group if it exists
            if _generated_app_process is not None:
                if _generated_app_process.poll() is None:  # Still running
                    pid = _generated_app_process.pid
                    logger.info(f"Force killing process group for PID {pid}")
                    try:
                        # Kill the entire process group (parent and all children)
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                    except Exception as e:
                        logger.warning(f"Error killing process group: {e}, trying direct kill")
                        _generated_app_process.kill()
                    _generated_app_process.wait()
                _generated_app_process = None
            
            # Kill ALL node processes (including child processes)
            try:
                logger.info("Killing all node processes")
                subprocess.run(["pkill", "-9", "node"], timeout=5)
            except Exception as e:
                logger.warning(f"Error killing node processes: {e}")
            
            # Wait for OS to fully release port 3000
            import time
            time.sleep(5)
            
            logger.info("Port 3000 cleared, ready to start app")

            # Install npm dependencies if node_modules doesn't exist
            node_modules_dir = project_dir / "node_modules"
            if not node_modules_dir.exists():
                logger.info(f"Installing npm dependencies using shell script for {project_name}...")
                
                # Get script path (relative to main.py)
                script_path = Path(__file__).parent / "scripts" / "install-deps.sh"
                
                if not script_path.exists():
                    raise HTTPException(status_code=500, detail=f"Install script not found: {script_path}")
                
                # Run the shell script
                result = os.system(f"bash {script_path}")
                
                if result != 0:
                    raise HTTPException(status_code=500, detail=f"npm install script failed with exit code {result}")
                
                logger.info("Dependencies installed successfully via shell script")

            # Run npm start in project directory
            # Capture output to log any startup errors
            env = {**os.environ, "PORT": "3000"}
            
            # Start the process with output capture in a new process group
            _generated_app_process = subprocess.Popen(
                ["npm", "start"],
                cwd=str(project_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid  # Start in new process group
            )
            
            # Wait briefly to check for immediate failures
            import time
            time.sleep(2)
            
            # Check if process is still running
            if _generated_app_process.poll() is not None:
                # Process already exited - capture output
                stdout, stderr = _generated_app_process.communicate()
                exit_code = _generated_app_process.returncode
                logger.error(f"App failed to start. Exit code: {exit_code}")
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
                _generated_app_process = None
                raise HTTPException(
                    status_code=500, 
                    detail=f"App failed to start. Exit code: {exit_code}. Check logs for details."
                )

            logger.info(f"Started {project_name} app with PID {_generated_app_process.pid} on port 3000")
            return {
                "success": True,
                "message": f"Started {project_name}",
                "pid": _generated_app_process.pid,
                "project_name": project_name,
                "url": "/yourapp/"
            }

        elif request.action == "stop":
            # Kill the entire process group to ensure all child processes are terminated
            logger.info("Stopping app - killing process group")
            
            # Kill Python-managed process and its entire process group if it exists
            if _generated_app_process is not None and _generated_app_process.poll() is None:
                pid = _generated_app_process.pid
                logger.info(f"Stopping process group for PID {pid}")
                try:
                    # Kill the entire process group (parent and all children)
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                    logger.info(f"Killed process group for PID {pid}")
                except Exception as e:
                    logger.warning(f"Error killing process group: {e}, trying direct kill")
                    _generated_app_process.kill()
                _generated_app_process.wait()
                logger.info(f"Stopped Python-managed process (PID {pid})")

            _generated_app_process = None
            logger.info(f"Stopped all processes on port 3000")
            return {"success": True, "message": f"Stopped {project_name} and cleared port 3000"}

        elif request.action == "status":
            if _generated_app_process is None:
                return {"success": True, "running": False, "message": "No app started"}
            elif _generated_app_process.poll() is None:
                return {
                    "success": True,
                    "running": True,
                    "pid": _generated_app_process.pid,
                    "project_name": project_name,
                    "url": "/yourapp/"
                }
            else:
                return {"success": True, "running": False, "message": "App has exited", "exit_code": _generated_app_process.returncode}

        else:
            raise HTTPException(status_code=400, detail="Invalid action. Use 'start', 'stop', or 'status'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error controlling app: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Reverse proxy to generated app on port 3000
# Access your generated app at /yourapp/ (e.g., /yourapp/login, /yourapp/api/users)
import httpx
import re

def rewrite_html_paths(html: str, prefix: str = "/yourapp") -> str:
    """Rewrite absolute paths in HTML to go through the proxy.

    This allows generated apps to use standard absolute paths (e.g., href="/dashboard")
    while still working behind the /yourapp/ proxy prefix.

    The generated app stays clean and deployable standalone - this rewriting
    only happens when served through the AI-DIY proxy.
    """
    # Rewrite href, action, src attributes with absolute paths
    # Matches: href="/path" or href='/path' (not href="http://", href="#", or href="path")
    html = re.sub(r'(href|action|src)="(/[^"]*)"', rf'\1="{prefix}\2"', html)
    html = re.sub(r"(href|action|src)='(/[^']*)'", rf"\1='{prefix}\2'", html)

    # Rewrite fetch() calls with absolute paths
    html = re.sub(r"fetch\('(/[^']*)'", rf"fetch('{prefix}\1'", html)
    html = re.sub(r'fetch\("(/[^"]*)"', rf'fetch("{prefix}\1"', html)

    # Rewrite window.location.href assignments with absolute paths
    html = re.sub(r"window\.location\.href\s*=\s*'(/[^']*)'", rf"window.location.href = '{prefix}\1'", html)
    html = re.sub(r'window\.location\.href\s*=\s*"(/[^"]*)"', rf'window.location.href = "{prefix}\1"', html)

    return html

@app.api_route("/yourapp/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_to_generated_app(path: str, request: Request):
    """Proxy requests to the generated app running on port 3000.

    Works on both Mac and Railway. The generated app is started via /api/control-app.

    This proxy handles all path rewriting so generated apps can use standard
    absolute paths and remain deployable standalone without modification.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Forward the request to localhost:3000
            url = f"http://localhost:3000/{path}"

            # Get request body if present
            body = await request.body()

            # Forward headers (except host and authorization which are for AI-DIY)
            headers = {k: v for k, v in request.headers.items() if k.lower() not in ['host', 'authorization']}

            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body,
                timeout=30.0,
                follow_redirects=False
            )

            # Return the response, handling redirects and HTML rewriting
            from starlette.responses import Response
            resp_headers = dict(response.headers)

            # Rewrite Location header for redirects to go through proxy (case-insensitive)
            location_key = None
            for key in resp_headers:
                if key.lower() == 'location':
                    location_key = key
                    break
            if location_key:
                loc = resp_headers[location_key]
                if loc.startswith('/'):
                    resp_headers[location_key] = f"/yourapp{loc}"

            # Rewrite HTML content to prefix absolute paths with /yourapp
            content_type = resp_headers.get('content-type', '')
            if 'text/html' in content_type.lower():
                try:
                    html = response.content.decode('utf-8')
                    html = rewrite_html_paths(html)
                    content = html.encode('utf-8')
                    # Update content-length header
                    resp_headers['content-length'] = str(len(content))
                except UnicodeDecodeError:
                    # Not valid UTF-8, return as-is
                    content = response.content
            else:
                content = response.content

            return Response(
                content=content,
                status_code=response.status_code,
                headers=resp_headers
            )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Generated app not running. Start it first via POST /api/control-app with {\"action\": \"start\"}")
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Also handle root path for /yourapp (without trailing path)
@app.api_route("/yourapp", methods=["GET"])
async def proxy_to_generated_app_root(request: Request):
    """Redirect /yourapp to /yourapp/ for cleaner URLs"""
    from starlette.responses import RedirectResponse
    return RedirectResponse(url="/yourapp/", status_code=307)

# Ensure required directory structure exists
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)

# Create required appdocs subdirectories
appdocs_dirs = [
    static_dir / "appdocs" / "visions",
    static_dir / "appdocs" / "backlog" / "wireframes",
    static_dir / "appdocs" / "sprints" / "backups",
    static_dir / "appdocs" / "scribe",
    static_dir / "appdocs" / "sessions",
]
for dir_path in appdocs_dirs:
    dir_path.mkdir(parents=True, exist_ok=True)

logger.info(f"Static directory ready: {static_dir}")

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def serve_index():
    """Serve the main UI."""
    return FileResponse("static/index.html")

@app.get("/progress")
async def serve_progress():
    """Serve the sprint progress page."""
    return FileResponse("static/progress.html")

@app.get("/progress_demo.html")
async def serve_progress_demo():
    """Serve the progress demo page."""
    return FileResponse("static/progress_demo.html")

@app.get("/api/env")
async def get_environment():
    """Returns the current application environment with feature status."""
    return {
        "environment": "PRODUCTION" if app_config.is_production else "DEVELOPMENT",
        "app_env": os.environ.get("APP_ENV", "DEV"),
        "features": FEATURES,
        "data_root": app_config.data_root if FEATURES["config_manager"] else "static",
        "log_level": app_config.log_level,
        "available_models": len(models_config.favorites) if FEATURES["config_manager"] else 0,
        "default_model": models_config.default if FEATURES["config_manager"] else None
    }

@app.get("/health")
async def health_check():
    """Comprehensive health check with feature validation."""
    try:
        health_data = {
            "status": "healthy",
            "version": "1.0.0",
            "approach": "ai-first",
            "features": FEATURES
        }
        
        # Add config info if available
        if FEATURES["config_manager"]:
            health_data.update({
                "config_valid": True,
                "models_available": len(models_config.favorites),
                "default_model": models_config.default,
                "data_root": app_config.data_root
            })
        
        # Test data manager if available
        if FEATURES["data_manager"]:
            try:
                test_vision_list = data_manager.list_visions()
                health_data["data_manager_healthy"] = isinstance(test_vision_list, list)
            except Exception as e:
                health_data["data_manager_healthy"] = False
                health_data["data_manager_error"] = str(e)
        
        # Test security if available
        if FEATURES["security_middleware"]:
            try:
                security_report = SecurityUtils.generate_security_report()
                health_data["security_healthy"] = "error" not in security_report
            except Exception as e:
                health_data["security_healthy"] = False
                health_data["security_error"] = str(e)
        
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "features": FEATURES
        }

@app.get("/api/config/models")
async def get_models_config_endpoint():
    """Get current models configuration."""
    if not FEATURES["config_manager"]:
        return {
            "error": "Config manager not available",
            "favorites": [],
            "default": None
        }
    
    try:
        models = config_manager.get_models_config()
        return {
            "favorites": models.favorites,
            "default": models.default,
            "last_used": models.last_used,
            "available_count": len(models.favorites)
        }
    except Exception as e:
        logger.error(f"Models config error: {e}")
        return {
            "error": str(e),
            "favorites": [],
            "default": None
        }

@app.get("/api/security/status")
async def get_security_status():
    """Get comprehensive security status (if security features enabled)."""
    if not FEATURES["security_middleware"]:
        return {
            "security_status": "not_available",
            "message": "Security middleware not loaded"
        }
    
    try:
        security_report = SecurityUtils.generate_security_report()
        security_report.update({
            "rate_limiter_clients": len(rate_limiter.requests),
            "max_rate_limit": SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE,
            "request_size_limit_mb": SecurityConfig.MAX_REQUEST_SIZE / (1024 * 1024),
            "file_size_limit_mb": SecurityConfig.MAX_FILE_SIZE / (1024 * 1024)
        })
        
        return {
            "security_status": "active",
            "report": security_report
        }
    except Exception as e:
        security_logger.error(f"Security status check failed: {e}")
        return {
            "security_status": "error",
            "error": str(e)
        }

@app.get("/api/data/status")
async def get_data_status():
    """Get data management status and statistics (if data manager enabled)."""
    if not FEATURES["data_manager"]:
        return {
            "data_status": "not_available",
            "message": "Data manager not loaded"
        }
    
    try:
        visions = data_manager.list_visions()
        return {
            "visions_count": len(visions),
            "data_root": app_config.data_root if FEATURES["config_manager"] else "static",
            "visions_dir_exists": Path(app_config.data_root, "visions").exists() if FEATURES["config_manager"] else False,
            "backlog_dir_exists": Path(app_config.data_root, "backlog").exists() if FEATURES["config_manager"] else False,
            "last_vision_update": visions[0].get("updated_at") if visions else None
        }
    except Exception as e:
        logger.error(f"Data status check failed: {e}")
        return {
            "error": str(e),
            "data_root": app_config.data_root if FEATURES["config_manager"] else "static"
        }

# Production-specific configurations
if app_config.is_production:
    if FEATURES["security_middleware"]:
        logger.info("Production security middleware active")
    else:
        # Add basic security headers if security middleware not available
        @app.middleware("http")
        async def add_basic_security_headers(request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            # Allow wireframes to be framed (they're displayed in iframes on same domain)
            if not request.url.path.startswith("/api/backlog/wireframe/"):
                response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            return response
        logger.info("Basic production security headers enabled")

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting AI-DIY Application - Consolidated Entry Point")
    logger.info("=" * 60)
    logger.info(f"📊 Configuration:")
    logger.info(f"   • Environment: {'Production' if app_config.is_production else 'Development'}")
    logger.info(f"   • Log level: {app_config.log_level}")
    logger.info(f"   • Data root: {app_config.data_root if FEATURES['config_manager'] else 'static'}")
    logger.info(f"   • Server: {app_config.host}:{app_config.port}")
    
    logger.info(f"🎯 Active Features:")
    logger.info(f"   • Fail-Fast Config: {'✅ Active' if FEATURES['config_manager'] else '❌ Not Available'}")
    logger.info(f"   • Data Manager: {'✅ Active' if FEATURES['data_manager'] else '❌ Not Available'}")
    logger.info(f"   • Structured Logging: {'✅ Active' if FEATURES['logging_middleware'] else '❌ Not Available'}")
    logger.info(f"   • Security Middleware: {'✅ Active' if FEATURES['security_middleware'] else '❌ Not Available'}")
    
    if FEATURES["config_manager"]:
        logger.info(f"📦 Models:")
        logger.info(f"   • Available: {len(models_config.favorites)}")
        logger.info(f"   • Default: {models_config.default or 'None (explicit selection required)'}")
    
    if FEATURES["security_middleware"]:
        logger.info(f"🔒 Security:")
        logger.info(f"   • Rate limiting: {SecurityConfig.RATE_LIMIT_REQUESTS_PER_MINUTE} req/min")
        logger.info(f"   • Request size limit: {SecurityConfig.MAX_REQUEST_SIZE / (1024*1024):.1f}MB")
        logger.info(f"   • File size limit: {SecurityConfig.MAX_FILE_SIZE / (1024*1024):.1f}MB")
    
    logger.info("=" * 60)
    
    try:
        uvicorn.run(
            app,
            host=app_config.host,
            port=app_config.port,
            log_level=app_config.log_level.lower(),
            access_log=FEATURES["logging_middleware"]
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
