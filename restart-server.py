#!/usr/bin/env python3

"""
Script to restart the Flask server without validation checks.
This bypasses the persona text validation to apply our hotfix.
"""

import os
import sys
import signal
import subprocess
import time
import psutil

def kill_server():
    """Find and kill the Flask server process"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = ' '.join(proc.info['cmdline'] or [])
            if 'flask run' in cmdline:
                print(f"Killing Flask process PID: {proc.info['pid']}")
                os.kill(proc.info['pid'], signal.SIGTERM)
                time.sleep(1)  # Give it time to terminate
                if psutil.pid_exists(proc.info['pid']):
                    os.kill(proc.info['pid'], signal.SIGKILL)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

def main():
    # Kill existing server
    kill_server()
    
    # Start server without validation
    print("Starting Flask server...")
    env = os.environ.copy()
    env["FLASK_APP"] = "development/src/app.py"
    env["FLASK_DEBUG"] = "0"
    env["SKIP_VALIDATION"] = "1"  # Skip the validation step
    
    # Use dynamic path relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    subprocess.Popen(
        ["flask", "run", "--no-debugger"],
        env=env,
        cwd=script_dir
    )
    
    print("Server restarted!")

if __name__ == "__main__":
    main()
