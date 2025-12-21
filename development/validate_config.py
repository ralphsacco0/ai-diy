#!/usr/bin/env python3
"""
Startup configuration validation for AI-DIY application.

This script validates all required configuration before allowing
the application to start. Implements fail-fast behavior with
clear error messages for missing or invalid configuration.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_manager import validate_startup_configuration


def main():
    """Validate configuration and exit with appropriate code."""
    # Configure logging for validation
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        print("🔍 Validating AI-DIY startup configuration...")

        # Run full configuration validation
        validate_startup_configuration()

        print("✅ Configuration validation successful!")
        print("🚀 Application can start safely.")
        return 0

    except ValueError as e:
        print(f"❌ Configuration validation failed: {e}")
        print("\n🔧 To fix this:")
        print("1. Ensure all required environment variables are set")
        print("2. Check that models_config.json exists and is valid")
        print("3. Verify LOG_LEVEL and DATA_ROOT are properly configured")
        print("4. See logs above for detailed error information")
        return 1

    except Exception as e:
        print(f"❌ Unexpected error during validation: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())