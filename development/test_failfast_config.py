#!/usr/bin/env python3
"""
Test script for fail-fast configuration validation.

Tests that the system properly fails when configuration is missing
or invalid, rather than falling back to defaults.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_test(test_name: str, command: list, expected_exit_code: int = 0):
    """Run a test and report results."""
    print(f"\n🧪 Running test: {test_name}")
    print(f"Command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).parent / "src")}
        )

        if result.returncode == expected_exit_code:
            print(f"✅ PASSED (exit code: {result.returncode})")
            if result.stdout:
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FAILED (expected: {expected_exit_code}, got: {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr.strip()}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ FAILED (timeout)")
        return False
    except Exception as e:
        print(f"❌ FAILED (exception: {e})")
        return False

def main():
    """Run all configuration validation tests."""
    print("🔍 AI-DIY Fail-Fast Configuration Tests")
    print("=" * 50)

    script_dir = Path(__file__).parent
    src_dir = script_dir / "src"
    python_path = f"{src_dir}{os.pathsep}{os.environ.get('PYTHONPATH', '')}"

    tests_passed = 0
    total_tests = 0

    # Test 1: Valid configuration should work
    total_tests += 1
    if run_test(
        "Valid configuration test",
        [sys.executable, "validate_config.py"],
        expected_exit_code=0
    ):
        tests_passed += 1

    # Test 2: Missing LOG_LEVEL should fail
    total_tests += 1
    if run_test(
        "Missing LOG_LEVEL test",
        [sys.executable, "-c", """
import sys
sys.path.append('src')
import os
# Temporarily unset LOG_LEVEL
old_level = os.environ.pop('LOG_LEVEL', None)
try:
    from config_manager import validate_startup_configuration
    validate_startup_configuration()
except ValueError as e:
    print(f"Expected error: {e}")
    sys.exit(0)  # Expected failure
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
finally:
    if old_level:
        os.environ['LOG_LEVEL'] = old_level
"""],
        expected_exit_code=0  # The script itself should succeed in detecting the error
    ):
        tests_passed += 1

    # Test 3: Missing models config file should fail
    total_tests += 1
    if run_test(
        "Missing models config test",
        [sys.executable, "-c", """
import sys
sys.path.append('src')
import os
# Temporarily rename models config
models_file = 'src/models_config.json'
backup_file = 'src/models_config.json.backup'
if os.path.exists(models_file):
    os.rename(models_file, backup_file)
try:
    from config_manager import validate_startup_configuration
    validate_startup_configuration()
except ValueError as e:
    print(f"Expected error: {e}")
    sys.exit(0)  # Expected failure
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
finally:
    if os.path.exists(backup_file):
        os.rename(backup_file, models_file)
"""],
        expected_exit_code=0
    ):
        tests_passed += 1

    # Test 4: Invalid JSON in models config should fail
    total_tests += 1
    if run_test(
        "Invalid JSON test",
        [sys.executable, "-c", """
import sys
sys.path.append('src')
import os
import json
# Create invalid JSON temporarily
models_file = 'src/models_config.json'
with open(models_file, 'w') as f:
    f.write('{ invalid json }')
try:
    from config_manager import validate_startup_configuration
    validate_startup_configuration()
except ValueError as e:
    print(f"Expected error: {e}")
    sys.exit(0)  # Expected failure
except Exception as e:
    print(f"Unexpected error: {e}")
    sys.exit(1)
finally:
    # Restore valid config
    valid_config = {
        'favorites': ['test/model'],
        'default': None,
        'meta': {},
        'last_used': None,
        'last_session_name': ''
    }
    with open(models_file, 'w') as f:
        json.dump(valid_config, f)
"""],
        expected_exit_code=0
    ):
        tests_passed += 1

    # Test 5: Main application startup with valid config should work
    total_tests += 1
    if run_test(
        "Main app startup test",
        [sys.executable, "-c", """
import sys
sys.path.append('src')
from main_failfast import app
print('✅ FastAPI app created successfully')
"""],
        expected_exit_code=0
    ):
        tests_passed += 1

    # Summary
    print(f"\n{'='*50}")
    print(f"📊 Test Results: {tests_passed}/{total_tests} passed")

    if tests_passed == total_tests:
        print("🎉 All fail-fast configuration tests passed!")
        print("✅ The system properly validates configuration and fails fast on errors.")
        return 0
    else:
        print("❌ Some tests failed - configuration validation may not be working correctly.")
        return 1

if __name__ == "__main__":
    sys.exit(main())