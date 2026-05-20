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
    print("  3. 🧠  Train Fleet-Wide LSTM Model (21 Features)")
    print("  4. 🎯  Train Vehicle-Specific LSTM (200+ Features)")
    print("  5. 🗄️  Seed/Reset SQLite Database (From CSV)")
    print("  6. 🛠️  Convert Raw .x431 Files to CSV")
    print("  7. 🔌  Launch Mock ELM327 Wi-Fi Server (TCP 35000)")
    print("  8. 🚪  Exit")
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
            raw_input = input("Enter option(s) (e.g. '3, 4, 1' or '1'): ").strip()
            import re
            choices = [c.strip() for c in re.split(r'[, ]+', raw_input) if c.strip()]
            
            should_exit = False
            for choice in choices:
                if choice == '1':
                    print("\nStarting the complete Dashboard stack...")
                    # We use start_phase3.py which already forks the process
                    subprocess.run([python_exec, str(project_root / "scripts" / "start_phase3.py")])
                
                elif choice == '2':
                    print("\nInitiating Machine Learning Training Pipeline...")
                    subprocess.run([python_exec, str(project_root / "scripts" / "run_full_analysis.py")])
                    time.sleep(1)
                
                elif choice == '3':
                    print("\nInitiating Fleet-Wide Deep Learning LSTM Training...")
                    subprocess.run([python_exec, str(project_root / "src" / "ml_models" / "train_lstm_keras.py")])
                    time.sleep(1)
                    
                elif choice == '4':
                    print("\nInitiating Vehicle-Specific Deep Learning Autoencoder Training...")
                    make = input("Enter Vehicle Make (e.g. Toyota): ").strip() or "Toyota"
                    model = input("Enter Vehicle Model (e.g. Tacoma): ").strip() or "Tacoma"
                    subprocess.run([python_exec, str(project_root / "src" / "ml_models" / "train_vehicle_specific_lstm.py"), "--make", make, "--model", model])
                    time.sleep(1)
                
                elif choice == '5':
                    print("\nSeeding SQLite Database with existing data...")
                    subprocess.run([python_exec, str(project_root / "scripts" / "seed_database.py")])
                    time.sleep(1)
                    
                elif choice == '6':
                    print("\nRunning X431 Converter Tool...")
                    subprocess.run([python_exec, str(project_root / "scripts" / "convert_x431.py")])
                    time.sleep(1)
                    
                elif choice == '7':
                    print("\nStarting Mock ELM327 Wi-Fi Server...")
                    subprocess.run([python_exec, str(project_root / "scripts" / "mock_elm327.py")])
                    time.sleep(1)
                    
                elif choice == '8':
                    print("\nShutting down Master Control Panel. Goodbye!\n")
                    should_exit = True
                    break
                else:
                    print(f"\n⚠️ Invalid option '{choice}'. Please enter numbers between 1 and 8.")
            
            if should_exit:
                break
                
        except KeyboardInterrupt:
            print("\n\nShutting down Master Control Panel. Goodbye!\n")
            break

if __name__ == "__main__":
    main()
