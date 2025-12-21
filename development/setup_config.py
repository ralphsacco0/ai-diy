#!/usr/bin/env python3
"""
Configuration setup and validation script for AI-DIY application.

This script helps set up and validate configuration for different environments.
Demonstrates fail-fast behavior and provides clear error messages.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from config_manager import ConfigManager, validate_startup_configuration
except ImportError as e:
    print(f"❌ Failed to import configuration management: {e}")
    print("🔧 Ensure config_manager.py is in the src directory")
    sys.exit(1)


class ConfigSetup:
    """Handles configuration setup and validation for different environments."""

    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.config_manager = ConfigManager()

    def setup_development_config(self) -> None:
        """Set up configuration for development environment."""
        print("🔧 Setting up development configuration...")

        # Set development-specific environment variables
        dev_config = {
            "LOG_LEVEL": "DEBUG",
            "DATA_ROOT": "static/appdocs",
            "PORT": "8000",
            "HOST": "127.0.0.1",
            "PRODUCTION": "false"
        }

        # Set environment variables
        for key, value in dev_config.items():
            os.environ[key] = value
            print(f"  ✓ Set {key}={value}")

        # Create default models config if it doesn't exist
        models_file = Path("models_config.json")
        if not models_file.exists():
            print("  📝 Creating default models configuration...")

            default_models = {
                "favorites": [
                    "deepseek/deepseek-chat-v3-0324",
                    "deepseek/deepseek-r1:free"
                ],
                "default": None,  # No default - require explicit selection
                "meta": {},
                "last_used": None,
                "last_session_name": ""
            }

            with open(models_file, 'w') as f:
                json.dump(default_models, f, indent=2)

            print(f"  ✓ Created {models_file}")

        print("✅ Development configuration setup complete!")

    def setup_production_config(self) -> None:
        """Set up configuration for production environment."""
        print("🔧 Setting up production configuration...")

        # Check for required production environment variables
        required_prod_vars = [
            "LOG_LEVEL",
            "DATA_ROOT",
            "OPENROUTER_API_KEY"  # Example production requirement
        ]

        missing_vars = []
        for var in required_prod_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            print(f"❌ Missing required production environment variables: {', '.join(missing_vars)}")
            print("\n🔧 Please set the following environment variables:")
            for var in missing_vars:
                print(f"  export {var}=your_value_here")
            sys.exit(1)

        # Set production-specific defaults
        prod_config = {
            "PORT": "8000",
            "HOST": "0.0.0.0",
            "PRODUCTION": "true"
        }

        for key, value in prod_config.items():
            if not os.getenv(key):
                os.environ[key] = value
                print(f"  ✓ Set {key}={value}")

        print("✅ Production configuration setup complete!")

    def validate_configuration(self) -> bool:
        """Validate current configuration."""
        print("🔍 Validating configuration...")

        try:
            validate_startup_configuration()
            print("✅ Configuration validation successful!")
            return True

        except ValueError as e:
            print(f"❌ Configuration validation failed: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected validation error: {e}")
            return False

    def show_current_config(self) -> None:
        """Show current configuration status."""
        print("\n📊 Current Configuration Status:")

        try:
            # Try to load configuration to show current state
            self.config_manager.load_configuration()

            app_config = self.config_manager.get_app_config()
            models_config = self.config_manager.get_models_config()

            print(f"  Environment: {'Production' if app_config.is_production else 'Development'}")
            print(f"  Log Level: {app_config.log_level}")
            print(f"  Data Root: {app_config.data_root}")
            print(f"  Server: {app_config.host}:{app_config.port}")
            print(f"  Models Available: {len(models_config.favorites)}")
            print(f"  Default Model: {models_config.default or 'None (explicit selection required)'}")

        except Exception as e:
            print(f"  ❌ Cannot load configuration: {e}")
            print("  🔧 Run setup first or check your environment variables")


def main():
    """Main configuration setup function."""
    parser = argparse.ArgumentParser(description="AI-DIY Configuration Setup")
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "production"],
        default="development",
        help="Environment to configure (default: development)"
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Validate current configuration"
    )
    parser.add_argument(
        "--show", "-s",
        action="store_true",
        help="Show current configuration status"
    )

    args = parser.parse_args()

    setup = ConfigSetup(args.environment)

    if args.validate:
        success = setup.validate_configuration()
        sys.exit(0 if success else 1)

    elif args.show:
        setup.show_current_config()
        sys.exit(0)

    else:
        # Default action: setup for specified environment
        if args.environment == "development":
            setup.setup_development_config()
        elif args.environment == "production":
            setup.setup_production_config()

        # Validate the setup
        print("\n🔍 Validating setup...")
        if setup.validate_configuration():
            print(f"\n🚀 {args.environment.title()} environment ready!")
            print("   Start the application with: python src/main_integrated.py"
            sys.exit(0)
        else:
            print(f"\n❌ {args.environment.title()} setup failed validation")
            sys.exit(1)


if __name__ == "__main__":
    main()