#!/usr/bin/env python3
import subprocess
import time
import sys
import os

from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_SCRIPT = PROJECT_ROOT / "src" / "api" / "main.py"
GUI_SCRIPT = PROJECT_ROOT / "src" / "gui" / "streamlit_app.py"

def main():
    print("="*60)
    print("  Starting BCScanTool Phase 3 Dashboard")
    print("="*60)
    
    # Try to use virtual environment python if it exists
    venv_python = PROJECT_ROOT / ".venv" / "bin" / "python"
    python_exec = str(venv_python) if venv_python.exists() else "python3"
    
    # 1. Start FastAPI Backend
    print("\n[1/2] Starting FastAPI Backend server...")
    api_process = subprocess.Popen(
        [python_exec, "-m", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", "8080"],
        cwd=PROJECT_ROOT
    )
    
    # Give API a moment to start
    time.sleep(2)
    
    # 2. Start Streamlit Frontend
    print("\n[2/2] Starting Streamlit Web Dashboard...")
    gui_process = subprocess.Popen(
        [python_exec, "-m", "streamlit", "run", str(GUI_SCRIPT)],
        cwd=PROJECT_ROOT
    )
    
    print("\n✅ Dashboard is running!")
    print("Close this terminal window to stop the servers.")
    
    try:
        # Keep main thread alive
        api_process.wait()
        gui_process.wait()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        api_process.terminate()
        gui_process.terminate()
        print("Shutdown complete.")

if __name__ == "__main__":
    main()
