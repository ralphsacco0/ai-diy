"""
API endpoints for model management and OpenRouter integration.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from pydantic import BaseModel

from core.models_config import ModelsConfig

router = APIRouter(prefix="/models", tags=["models"])

# Initialize models config
models_config = ModelsConfig()

class ModelInfo(BaseModel):
    """Model information schema."""
    id: str
    prompt_per_m: Optional[float] = None
    completion_per_m: Optional[float] = None
    ctx: Optional[int] = None
    description: str

class ModelsResponse(BaseModel):
    """Response for models list."""
    models: List[ModelInfo]
    error: Optional[str] = None

class FavoritesRequest(BaseModel):
    """Request to update favorites."""
    favorites: List[str]
    default_model: Optional[str] = None

class ConfigResponse(BaseModel):
    """Model configuration response."""
    favorites: List[str]
    default_model: str
    meta: Dict
    last_session_name: str

@router.get("/", response_model=ModelsResponse)
async def get_models(
    show_free_only: bool = Query(False, description="Show only free models"),
    sort_by: str = Query("Alphabetical", description="Sort by: Alphabetical, Price (input), Price (output)"),
    filter_text: str = Query("", description="Filter models by text")
):
    """Fetch available models from OpenRouter."""
    models, error = models_config.fetch_openrouter_models()
    
    if error:
        return ModelsResponse(models=[], error=error)
    
    # Apply filters and sorting
    filtered_models = models_config.filter_models(models, filter_text, show_free_only)
    sorted_models = models_config.sort_models(filtered_models, sort_by)
    
    # Convert to response format
    model_infos = []
    for model in sorted_models:
        model_infos.append(ModelInfo(
            id=model["id"],
            prompt_per_m=model.get("prompt_per_m"),
            completion_per_m=model.get("completion_per_m"),
            ctx=model.get("ctx"),
            description=models_config.describe_model_row(model)
        ))
    
    return ModelsResponse(models=model_infos, error=None)

@router.get("/config", response_model=ConfigResponse)
async def get_config():
    """Get current model configuration."""
    favorites, default_model, meta, last_session_name = models_config.load_config()
    
    return ConfigResponse(
        favorites=favorites,
        default_model=default_model,
        meta=meta,
        last_session_name=last_session_name
    )

@router.post("/favorites")
async def update_favorites(request: FavoritesRequest):
    """Update favorite models and default."""
    favorites, current_default, meta, last_session_name = models_config.load_config()

    # Update favorites
    new_favorites = request.favorites

    # Auto-set default model logic:
    # 1. If default_model is explicitly provided, use it
    # 2. Otherwise, use the first favorite as default (common UX pattern)
    # 3. If no favorites provided, keep current default
    if request.default_model:
        new_default = request.default_model
    elif new_favorites:
        new_default = new_favorites[0]  # First favorite becomes default
    else:
        new_default = current_default

    # Ensure default is in favorites
    if new_default and new_default not in new_favorites:
        new_favorites.append(new_default)

    # Save configuration with updated default and last_used
    success, error = models_config.save_config(new_favorites, new_default, meta, last_session_name)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {error}")

@router.post("/set-default")
async def set_default_model(request: dict):
    """Set the default model explicitly."""
    model_id = request.get("model_id")
    if not model_id:
        raise HTTPException(status_code=400, detail="model_id is required")

    favorites, current_default, meta, last_session_name = models_config.load_config()
    new_favorites = favorites.copy()

    # Ensure the model is in favorites
    if model_id not in new_favorites:
        new_favorites.append(model_id)

    # Update configuration
    success, error = models_config.save_config(new_favorites, model_id, meta, last_session_name)

    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {error}")

    return {"success": True, "default_model": model_id, "favorites": new_favorites}

@router.post("/reset")
async def reset_to_defaults():
    """Reset model configuration - REMOVED: No default fallbacks allowed.
    
    This endpoint has been removed because the application uses fail-fast configuration.
    Users must explicitly configure their models in models_config.json.
    """
    raise HTTPException(
        status_code=501,
        detail="Reset to defaults not supported. Configure models explicitly in models_config.json"
    )

@router.get("/credits")
async def get_credits():
    """Get OpenRouter credits information."""
    credits, error = models_config.fetch_openrouter_credits()
    
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    return credits or {}
