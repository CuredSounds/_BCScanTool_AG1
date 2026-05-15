#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
import time

def print_menu():
    print("\n" + "=" * 60)
    print("   🚀 BCScanTool - Master Control Panel 🚀")
    print("=" * 60)
    print("Please select an action:")
    print("  1. 🏎️  Launch Phase 3 Dashboard (API + Streamlit)")
    print("  2. 🧠  Train Machine Learning Models (Scikit-Learn)")
    print("  3. 🗄️  Seed/Reset SQLite Database (From CSV)")
    print("  4. 🛠️  Convert Raw .x431 Files to CSV")
    print("  5. 🚪  Exit")
    print("=" * 60)

def get_python_exec(project_root):
    venv_python = project_root / ".venv" / "bin" / "python"
    return str(venv_python) if venv_python.exists() else "python3"

def main():
    project_root = Path(__file__).resolve().parent.parent
    python_exec = get_python_exec(project_root)
    
    while True:
        print_menu()
        try:
            choice = input("Enter option (1-5): ").strip()
            
            if choice == '1':
                print("\nStarting the complete Dashboard stack...")
                # We use start_phase3.py which already forks the process
                subprocess.run([python_exec, str(project_root / "scripts" / "start_phase3.py")])
            
            elif choice == '2':
                print("\nInitiating Machine Learning Training Pipeline...")
                subprocess.run([python_exec, str(project_root / "scripts" / "run_full_analysis.py")])
                time.sleep(1)
            
            elif choice == '3':
                print("\nSeeding SQLite Database with existing data...")
                subprocess.run([python_exec, str(project_root / "scripts" / "seed_database.py")])
                time.sleep(1)
                
            elif choice == '4':
                print("\nRunning X431 Converter Tool...")
                subprocess.run([python_exec, str(project_root / "scripts" / "convert_x431.py")])
                time.sleep(1)
                
            elif choice == '5':
                print("\nShutting down Master Control Panel. Goodbye!\n")
                break
            else:
                print("\n⚠️ Invalid option. Please enter a number between 1 and 5.")
                
        except KeyboardInterrupt:
            print("\n\nShutting down Master Control Panel. Goodbye!\n")
            break

if __name__ == "__main__":
    main()
