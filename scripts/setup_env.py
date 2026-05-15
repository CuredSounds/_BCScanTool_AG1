#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

def check_tkinter():
    print("Checking for Tkinter...")
    try:
        import tkinter
        print(f"✅ Tkinter version {tkinter.TkVersion} found.")
        return True
    except ImportError:
        print("❌ Tkinter not found in current environment.")
        return False

def check_dependencies():
    print("\nChecking dependencies...")
    required = ['pandas', 'numpy', 'matplotlib']
    all_found = True
    for pkg in required:
        try:
            __import__(pkg)
            print(f"✅ {pkg} found.")
        except ImportError:
            print(f"❌ {pkg} NOT found.")
            all_found = False
    return all_found

def main():
    print("="*60)
    print("BC Scan Tool - Environment Setup & Diagnosis")
    print("="*60)
    
    python_path = sys.executable
    print(f"\nCurrent Python: {python_path}")
    print(f"Python Version: {sys.version.split()[0]}")
    
    tk_ok = check_tkinter()
    deps_ok = check_dependencies()
    
    if tk_ok and deps_ok:
        print("\n🎉 Environment looks good! You should be able to run the GUI.")
        print("Run with: python scripts/launch.py")
    else:
        print("\n" + "!"*60)
        print(" ISSUES DETECTED")
        print(" " + "!"*60)
        
        if not tk_ok:
            print("\nTkinter is missing.")
            if sys.platform == "darwin":
                print("macOS detected. Please run:")
                print("   brew install python-tk@3.11")
                print("\nAlternatively, use a Python distribution that includes Tkinter,")
                print("like the one from Python.org.")
            elif sys.platform == "linux":
                print("Linux detected. Please run:")
                print("   sudo apt-get install python3-tk")
        
        if not deps_ok:
            print("\nSome Python dependencies are missing. Run:")
            print("   pip install pandas numpy matplotlib")
            
    print("\n" + "="*60)

if __name__ == "__main__":
    main()
