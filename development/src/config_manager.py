"""
Configuration management system for AI-DIY application.

Implements fail-fast validation for all required configuration.
No defaults or silent fallbacks - explicit configuration required.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

from .api.conventions import (
    create_error_response, ApiErrorCode, fail_fast_on_missing_config,
    validate_required_config, SafetyConfig
)

logger = logging.getLogger(__name__)


class ModelsConfig(BaseModel):
    """Models configuration - no defaults allowed."""

    favorites: List[str] = Field(min_items=1, description="List of available model identifiers")
    default: Optional[str] = Field(None, description="Default model identifier (must be in favorites)")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Model metadata")
    last_used: Optional[str] = Field(None, description="Last used model identifier")
    last_session_name: str = Field("", description="Last session name")

    def model_post_init(self, __context) -> None:
        """Validate configuration after initialization."""
        if self.default and self.default not in self.favorites:
            raise ValueError(f"Default model '{self.default}' not in favorites list")


class AppConfig(BaseModel):
    """Main application configuration."""

    # Required configuration
    log_level: str = Field("INFO", description="Logging level")
    data_root: str = Field("static/appdocs", description="Root directory for application data")
    models_config_path: str = Field("models_config.json", description="Path to models configuration file")

    # Optional configuration with safe defaults
    port: int = Field(8000, description="Server port")
    host: str = Field("0.0.0.0", description="Server host")

    # Environment-specific settings
    is_production: bool = Field(False, description="Production mode flag")

    def model_post_init(self, __context) -> None:
        """Validate and normalize configuration."""
        # Normalize log level
        self.log_level = self.log_level.upper()
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            raise ValueError(f"Invalid log level: {self.log_level}")


class ConfigManager:
    """Manages application configuration with fail-fast validation."""

    def __init__(self):
        self.config: Optional[AppConfig] = None
        self.models_config: Optional[ModelsConfig] = None
        self._config_file = Path("app_config.json")
        self._models_config_file = Path("models_config.json")

    def load_configuration(self) -> None:
        """Load and validate all configuration with fail-fast on errors."""
        logger.info("Loading application configuration...")

        try:
            # Load main app configuration
            self.config = self._load_app_config()

            # Load models configuration
            self.models_config = self._load_models_config()

            # Validate models configuration
            self._validate_models_config()

            logger.info("Configuration loaded and validated successfully")

        except Exception as e:
            logger.error(f"Configuration loading failed: {e}")
            raise ValueError(f"Configuration error: {e}")

    def _load_app_config(self) -> AppConfig:
        """Load main application configuration."""
        # Start with environment-based defaults
        config_data = {
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "data_root": os.getenv("DATA_ROOT", "static/appdocs"),
            "models_config_path": os.getenv("MODELS_CONFIG_PATH", "models_config.json"),
            "port": int(os.getenv("PORT", "8000")),
            "host": os.getenv("HOST", "0.0.0.0"),
            "is_production": os.getenv("PRODUCTION", "false").lower() == "true"
        }

        # Check for config file override
        if self._config_file.exists():
            try:
                with open(self._config_file, 'r') as f:
                    file_config = json.load(f)
                config_data.update(file_config)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load config file {self._config_file}: {e}")

        return AppConfig(**config_data)

    def _load_models_config(self) -> ModelsConfig:
        """Load models configuration without defaults."""
        models_path = self.config.models_config_path if self.config else "models_config.json"
        
        # Resolve relative to repository root
        if not Path(models_path).is_absolute():
            repo_root = Path(__file__).parent.parent.parent
            models_path = repo_root / models_path
        else:
            models_path = Path(models_path)

        if not models_path.exists():
            raise FileNotFoundError(
                f"❌ Models configuration file not found: {models_path}\n"
                f"🔧 Create models_config.json at repository root"
            )

        try:
            with open(models_path, 'r') as f:
                models_data = json.load(f)

            return ModelsConfig(**models_data)

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in models configuration: {e}")
        except Exception as e:
            raise ValueError(f"Failed to load models configuration: {e}")

    def _validate_models_config(self) -> None:
        """Validate that models configuration is complete and valid."""
        if not self.models_config:
            raise ValueError("Models configuration not loaded")

        # Check that favorites list is not empty
        if not self.models_config.favorites:
            raise ValueError("Models configuration must include at least one favorite model")

        # Validate default model if specified
        if self.models_config.default:
            if self.models_config.default not in self.models_config.favorites:
                raise ValueError(
                    f"Default model '{self.models_config.default}' not found in favorites list"
                )

    def get_models_config(self) -> ModelsConfig:
        """Get validated models configuration."""
        if not self.models_config:
            raise RuntimeError("Configuration not loaded. Call load_configuration() first.")
        return self.models_config

    def get_app_config(self) -> AppConfig:
        """Get validated application configuration."""
        if not self.config:
            raise RuntimeError("Configuration not loaded. Call load_configuration() first.")
        return self.config

    def save_models_config(self, config: ModelsConfig) -> None:
        """Save models configuration with validation."""
        try:
            # Validate before saving
            self._validate_models_config_for_save(config)

            models_path = self.config.models_config_path if self.config else "models_config.json"
            
            # Resolve relative to repository root
            if not Path(models_path).is_absolute():
                repo_root = Path(__file__).parent.parent.parent
                models_path = repo_root / models_path
            else:
                models_path = Path(models_path)

            with open(models_path, 'w') as f:
                # Save with pretty formatting
                json.dump(config.model_dump(), f, indent=2)

            # Update in-memory config
            self.models_config = config

            logger.info(f"Models configuration saved to {models_path}")

        except Exception as e:
            logger.error(f"Failed to save models configuration: {e}")
            raise ValueError(f"Configuration save failed: {e}")

    def _validate_models_config_for_save(self, config: ModelsConfig) -> None:
        """Validate models configuration before saving."""
        # Same validation as load
        self._validate_models_config()


# Global configuration manager instance
config_manager = ConfigManager()


def validate_startup_configuration() -> None:
    """Validate all required configuration at startup."""
    logger.info("Validating startup configuration...")

    required_env_vars = [
        "LOG_LEVEL",
        "DATA_ROOT"
    ]

    # Check environment variables
    missing_env = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_env.append(var)

    if missing_env:
        error_msg = f"Missing required environment variables: {', '.join(missing_env)}"
        logger.error(f"STARTUP_CONFIG_ERROR: {error_msg}")
        raise ValueError(error_msg)

    # Load and validate full configuration
    try:
        config_manager.load_configuration()
    except Exception as e:
        logger.error(f"STARTUP_CONFIG_ERROR: Configuration loading failed: {e}")
        raise ValueError(f"Configuration validation failed: {e}")

    logger.info("Startup configuration validation complete")


def get_required_models() -> List[str]:
    """Get list of required model identifiers."""
    try:
        models_config = config_manager.get_models_config()
        return models_config.favorites.copy()
    except RuntimeError as e:
        logger.error(f"Cannot get required models: {e}")
        raise ValueError(f"Configuration not available: {e}")


def get_default_model() -> Optional[str]:
    """Get default model identifier - may be None if not configured."""
    try:
        models_config = config_manager.get_models_config()
        return models_config.default
    except RuntimeError as e:
        logger.error(f"Cannot get default model: {e}")
        raise ValueError(f"Configuration not available: {e}")


def update_last_used_model(model_id: str) -> None:
    """Update the last used model in configuration."""
    try:
        models_config = config_manager.get_models_config()
        if model_id not in models_config.favorites:
            raise ValueError(f"Model '{model_id}' not in favorites list")

        # Create updated config
        updated_config = ModelsConfig(
            favorites=models_config.favorites,
            default=models_config.default,
            meta=models_config.meta,
            last_used=model_id,
            last_session_name=models_config.last_session_name
        )

        config_manager.save_models_config(updated_config)

    except Exception as e:
        logger.error(f"Failed to update last used model: {e}")
        # Don't raise - this is not a critical failure