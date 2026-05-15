1#!/usr/bin/env python3
"""
BC Scan Tool - Unified Launch Script
Main entry point for vehicle diagnostic analysis platform
"""

import os
import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def print_banner():
    """Print application banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════════╗
    ║                                                                  ║
    ║              BC SCAN TOOL - Vehicle Diagnostics                  ║
    ║           Professional OBD2 Analysis & Predictions               ║
    ║                                                                  ║
    ║  Features:                                                       ║
    ║    • Real-time diagnostic analysis                               ║
    ║    • Predictive maintenance (LSTM + Autoencoder)                 ║
    ║    • Health scoring & trend analysis                             ║
    ║    • Repair cost estimation                                      ║
    ║    • Multi-vehicle baseline learning                             ║
    ║                                                                  ║
    ╚══════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_dependencies():
    """Check if required packages are installed"""
    required = {
        'pandas': 'Data processing',
        'numpy': 'Numerical computations',
        'scipy': 'Scientific computing',
    }

    optional = {
        'PyPDF2': 'PDF parsing',
        'tensorflow': 'Machine learning (LSTM, Autoencoder)',
        'sklearn': 'ML preprocessing',
    }

    missing_required = []
    missing_optional = []

    for package, description in required.items():
        try:
            __import__(package)
        except ImportError:
            missing_required.append((package, description))

    for package, description in optional.items():
        try:
            __import__(package)
        except ImportError:
            missing_optional.append((package, description))

    if missing_required:
        print("\n❌ MISSING REQUIRED PACKAGES:")
        for pkg, desc in missing_required:
            print(f"   • {pkg}: {desc}")
        print("\nInstall with: pip install " + " ".join([p[0] for p in missing_required]))
        return False

    if missing_optional:
        print("\n⚠️  MISSING OPTIONAL PACKAGES (some features disabled):")
        for pkg, desc in missing_optional:
            print(f"   • {pkg}: {desc}")
        print("\nInstall with: pip install " + " ".join([p[0] for p in missing_optional]))

    return True

def run_cli_analysis():
    """Run command-line analysis"""
    print("\n" + "="*70)
    print("RUNNING COMPREHENSIVE VEHICLE ANALYSIS")
    print("="*70 + "\n")

    try:
        from src.core import obd2_analyzer
        obd2_analyzer.main()
    except Exception as e:
        print(f"\n❌ Error running analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def launch_gui():
    """Launch GUI dashboard"""
    print("\n" + "="*70)
    print("LAUNCHING GUI DASHBOARD")
    print("="*70 + "\n")

    try:
        # Check if tkinter is available
        import tkinter as tk
        from src.gui.dashboard import VehicleDiagnosticGUI

        root = tk.Tk()
        app = VehicleDiagnosticGUI(root)
        root.mainloop()

    except ImportError as e:
        if 'tkinter' in str(e):
            print("\n" + "!"*70)
            print(" ERROR: TKINTER NOT FOUND")
            print(" " + "!"*70)
            print("\nThe 'tkinter' module is required for the GUI Dashboard.")
            print("\nHOW TO FIX (macOS):")
            print("1. Install python-tk using Homebrew:")
            print("   brew install python-tk@3.11")
            print("\n2. OR use the official Python.org installer which includes Tkinter.")
            print("\n3. OR if you are using PyCharm, go to Settings -> Project -> Python Interpreter")
            print("   and select a Python version that has Tkinter (e.g., /usr/bin/python3).")
            print("\n" + "!"*70 + "\n")
            print("Falling back to CLI mode...")
            return run_cli_analysis()
        else:
            print(f"❌ Error importing GUI: {e}")
            print("\nFalling back to CLI mode...")
            return run_cli_analysis()
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True

def quick_scan():
    """Run quick diagnostic scan"""
    print("\n📊 Running Quick Scan...\n")

    try:
        import pandas as pd
        from src.core.diagnostic_engine import DiagnosticEngine
        from src.core.predictive_analytics import PredictiveAnalytics

        # Load latest data
        data_dir = PROJECT_ROOT / 'data'

        # Check for processed data
        processed_file = data_dir / 'processed' / 'diagnostic_reports.csv'
        if processed_file.exists():
            pdf_data = pd.read_csv(processed_file)

            # Run quick analysis
            engine = DiagnosticEngine(None, pdf_data)
            issues = engine.analyze()

            predictor = PredictiveAnalytics(pdf_data)
            predictions, health_scores = predictor.analyze()

            print("\n✅ Quick scan complete!")
            print(f"   Issues detected: {len(issues)}")
            print(f"   Vehicles analyzed: {len(health_scores)}")

        else:
            print("⚠️  No processed data found. Run full analysis first.")
            return False

    except Exception as e:
        print(f"❌ Error in quick scan: {e}")
        return False

    return True

def show_menu():
    """Show interactive menu"""
    while True:
        print("\n" + "="*70)
        print("MAIN MENU")
        print("="*70)
        print("\n1. Launch GUI Dashboard")
        print("2. Run Full Analysis (CLI)")
        print("3. Quick Scan (Latest Data)")
        print("4. View Reports")
        print("5. Export Data")
        print("6. Check System Status")
        print("7. Exit")

        choice = input("\nSelect option (1-7): ").strip()

        if choice == '1':
            launch_gui()
        elif choice == '2':
            run_cli_analysis()
        elif choice == '3':
            quick_scan()
        elif choice == '4':
            view_reports()
        elif choice == '5':
            export_data()
        elif choice == '6':
            check_system_status()
        elif choice == '7':
            print("\n👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please select 1-7.")

def view_reports():
    """View generated reports"""
    data_dir = PROJECT_ROOT / 'data'

    reports = {
        'Diagnostic Report': data_dir / 'diagnostic_report.csv',
        'Predictions': data_dir / 'predictions.csv',
        'Health Scores': data_dir / 'processed' / 'diagnostic_reports.csv',
    }

    print("\n" + "="*70)
    print("AVAILABLE REPORTS")
    print("="*70 + "\n")

    for name, path in reports.items():
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            print(f"✅ {name}: {path.name} ({size:.1f} KB)")
        else:
            print(f"❌ {name}: Not found")

def export_data():
    """Export data in various formats"""
    print("\n" + "="*70)
    print("DATA EXPORT")
    print("="*70 + "\n")

    data_dir = PROJECT_ROOT / 'data'
    db_file = data_dir / 'obd2_data.db'

    if db_file.exists():
        print(f"✅ SQLite database: {db_file}")
        print("\nExport options:")
        print("1. Export to Excel")
        print("2. Export to JSON")
        print("3. Export to CSV")
        print("4. Back")

        choice = input("\nSelect option: ").strip()

        if choice in ['1', '2', '3']:
            print("⚠️  Export functionality coming soon!")
    else:
        print("❌ No database found. Run analysis first.")

def check_system_status():
    """Check system status and data"""
    print("\n" + "="*70)
    print("SYSTEM STATUS")
    print("="*70 + "\n")

    # Check data directory
    data_dir = PROJECT_ROOT / 'data'
    if data_dir.exists():
        # Count files
        raw_files = list((data_dir / 'raw').rglob('*.csv')) if (data_dir / 'raw').exists() else []
        pdf_files = list((data_dir / 'raw').rglob('*.pdf')) if (data_dir / 'raw').exists() else []

        print(f"📁 Data Directory: {data_dir}")
        print(f"   Raw CSV files: {len(raw_files)}")
        print(f"   PDF reports: {len(pdf_files)}")

        # Check database
        db_file = data_dir / 'obd2_data.db'
        if db_file.exists():
            size_mb = db_file.stat().st_size / (1024 * 1024)
            print(f"   Database size: {size_mb:.2f} MB")
        else:
            print("   Database: Not created yet")

    # Check baselines
    baseline_file = data_dir / 'vehicle_baselines.json'
    if baseline_file.exists():
        import json
        with open(baseline_file) as f:
            baselines = json.load(f)
        print(f"\n🚗 Vehicle Baselines: {len(baselines)} vehicles")
        for vin, data in baselines.items():
            print(f"   • {data.get('year')} {data.get('make')} {data.get('model')}")

    # Check dependencies
    print("\n📦 Dependencies:")
    check_dependencies()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='BC Scan Tool - Vehicle Diagnostic Analysis Platform',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch.py                 # Interactive menu
  python launch.py --gui           # Launch GUI directly
  python launch.py --analyze       # Run full analysis
  python launch.py --quick         # Quick scan
        """
    )

    parser.add_argument('--gui', action='store_true', help='Launch GUI dashboard')
    parser.add_argument('--analyze', action='store_true', help='Run full CLI analysis')
    parser.add_argument('--quick', action='store_true', help='Quick scan (latest data)')
    parser.add_argument('--status', action='store_true', help='Show system status')
    parser.add_argument('--no-banner', action='store_true', help='Skip banner')

    args = parser.parse_args()

    # Print banner
    if not args.no_banner:
        print_banner()

    # Check dependencies
    if not check_dependencies():
        print("\n❌ Please install required packages before continuing.")
        sys.exit(1)

    # Execute based on arguments
    if args.gui:
        launch_gui()
    elif args.analyze:
        run_cli_analysis()
    elif args.quick:
        quick_scan()
    elif args.status:
        check_system_status()
    else:
        # No arguments - show menu
        show_menu()

if __name__ == "__main__":
    main()
