"""
Testing API endpoints for app-based test execution.
Separate from Windsurf integration for cleaner test environment.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import importlib.util
import traceback
import subprocess
import json
from pathlib import Path

router = APIRouter(prefix="/testing", tags=["testing"])

class TestCase(BaseModel):
    name: str
    description: str
    test_type: str  # "function", "output", "import", "command"
    target: str     # function name, file path, or command
    expected: Any   # expected result
    parameters: Optional[Dict[str, Any]] = None

class TestRequest(BaseModel):
    test_cases: List[TestCase]
    target_file: str = "helloworld.py"

class TestResult(BaseModel):
    test_name: str
    status: str  # "PASS", "FAIL", "ERROR"
    actual: Any
    expected: Any
    error_message: Optional[str] = None

class TestResponse(BaseModel):
    results: List[TestResult]
    summary: Dict[str, int]  # {"passed": 2, "failed": 1, "errors": 0}

# Use consistent path resolution (matches sprint_orchestrator.py pattern)
# Working directory is /app/development/src on Railway, repo/development/src locally
PROJECT_ROOT = Path("static/appdocs/execution-sandbox/client-projects")

@router.post("/run-tests", response_model=TestResponse)
async def run_tests(test_request: TestRequest):
    """Execute test cases and return results."""
    results = []
    
    # Add target file directory to Python path
    target_path = PROJECT_ROOT / test_request.target_file
    target_dir = os.path.dirname(target_path)
    if str(target_dir) not in sys.path:
        sys.path.insert(0, str(target_dir))
    
    for test_case in test_request.test_cases:
        try:
            result = await execute_test_case(test_case, test_request.target_file)
            results.append(result)
        except Exception as e:
            results.append(TestResult(
                test_name=test_case.name,
                status="ERROR",
                actual=None,
                expected=test_case.expected,
                error_message=str(e)
            ))
    
    # Calculate summary
    summary = {
        "passed": sum(1 for r in results if r.status == "PASS"),
        "failed": sum(1 for r in results if r.status == "FAIL"),
        "errors": sum(1 for r in results if r.status == "ERROR")
    }
    
    return TestResponse(results=results, summary=summary)

async def execute_test_case(test_case: TestCase, target_file: str) -> TestResult:
    """Execute a single test case."""
    
    if test_case.test_type == "function":
        return await test_function_call(test_case, target_file)
    elif test_case.test_type == "output":
        return await test_output_match(test_case, target_file)
    elif test_case.test_type == "import":
        return await test_import_success(test_case, target_file)
    elif test_case.test_type == "command":
        return await test_command_execution(test_case)
    else:
        raise ValueError(f"Unknown test type: {test_case.test_type}")

async def test_function_call(test_case: TestCase, target_file: str) -> TestResult:
    """Test calling a function and checking its return value."""
    try:
        # Import the module
        module_name = target_file.replace('.py', '')
        spec = importlib.util.spec_from_file_location(
            module_name, 
            str(PROJECT_ROOT / target_file)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Get the function
        func = getattr(module, test_case.target)
        
        # Call with parameters if provided
        if test_case.parameters:
            actual = func(**test_case.parameters)
        else:
            actual = func()
        
        # Check result
        status = "PASS" if actual == test_case.expected else "FAIL"
        
        return TestResult(
            test_name=test_case.name,
            status=status,
            actual=actual,
            expected=test_case.expected
        )
        
    except Exception as e:
        return TestResult(
            test_name=test_case.name,
            status="ERROR",
            actual=None,
            expected=test_case.expected,
            error_message=str(e)
        )

async def test_output_match(test_case: TestCase, target_file: str) -> TestResult:
    """Test script output matches expected."""
    try:
        result = subprocess.run(
            ["python3", str(PROJECT_ROOT / target_file)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        actual = result.stdout.strip()
        status = "PASS" if actual == test_case.expected else "FAIL"
        
        return TestResult(
            test_name=test_case.name,
            status=status,
            actual=actual,
            expected=test_case.expected,
            error_message=result.stderr if result.stderr else None
        )
        
    except Exception as e:
        return TestResult(
            test_name=test_case.name,
            status="ERROR",
            actual=None,
            expected=test_case.expected,
            error_message=str(e)
        )

async def test_import_success(test_case: TestCase, target_file: str) -> TestResult:
    """Test that a module can be imported successfully."""
    try:
        module_name = target_file.replace('.py', '')
        spec = importlib.util.spec_from_file_location(
            module_name, 
            str(PROJECT_ROOT / target_file)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        return TestResult(
            test_name=test_case.name,
            status="PASS",
            actual="Import successful",
            expected="Import successful"
        )
        
    except Exception as e:
        return TestResult(
            test_name=test_case.name,
            status="FAIL",
            actual=None,
            expected="Import successful",
            error_message=str(e)
        )

async def test_command_execution(test_case: TestCase) -> TestResult:
    """Test command execution."""
    try:
        result = subprocess.run(
            test_case.target.split(),
            capture_output=True,
            text=True,
            timeout=10
        )
        
        actual = result.returncode
        status = "PASS" if actual == test_case.expected else "FAIL"
        
        return TestResult(
            test_name=test_case.name,
            status=status,
            actual=actual,
            expected=test_case.expected,
            error_message=result.stderr if result.stderr else None
        )
        
    except Exception as e:
        return TestResult(
            test_name=test_case.name,
            status="ERROR",
            actual=None,
            expected=test_case.expected,
            error_message=str(e)
        )
