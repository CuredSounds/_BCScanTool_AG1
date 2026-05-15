#!/usr/bin/env python3
"""
BC Scan Tool - GUI Dashboard
Professional vehicle diagnostic interface with data visualization
"""

try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, filedialog, messagebox
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False
import sys
from pathlib import Path
import json
import sqlite3
from datetime import datetime
import pandas as pd

# Project imports
try:
    from src.core.diagnostic_engine import DiagnosticEngine
    from src.core.predictive_analytics import PredictiveAnalytics
    DIAGNOSTIC_AVAILABLE = True
except ImportError:
    try:
        from diagnostic_engine import DiagnosticEngine
        from predictive_analytics import PredictiveAnalytics
        DIAGNOSTIC_AVAILABLE = True
    except ImportError:
        DIAGNOSTIC_AVAILABLE = False

try:
    import matplotlib
    matplotlib.use('TkAgg')
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except Exception:
    MATPLOTLIB_AVAILABLE = False


class VehicleDiagnosticGUI:
    """Main GUI Dashboard for BC Scan Tool"""

    def __init__(self, root):
        self.root = root
        self.root.title("BC Scan Tool - Vehicle Diagnostics")
        self.root.geometry("1200x800")

        from src import config
        self.project_root = config.PROJECT_ROOT
        self.data_dir = config.DATA_DIR

        # Data storage
        self.vehicles = {}
        self.current_vehicle = None
        self.diagnostic_data = None
        self.predictions = None

        # Load vehicle baselines
        self.load_vehicle_baselines()

        # Create UI
        self.create_widgets()

        # Load initial data
        self.refresh_data()

    def load_vehicle_baselines(self):
        """Load vehicle baselines from JSON"""
        baseline_file = self.data_dir / 'vehicle_baselines.json'
        if baseline_file.exists():
            try:
                with open(baseline_file) as f:
                    self.vehicles = json.load(f)
            except Exception as e:
                print(f"Error loading baselines: {e}")
                self.vehicles = {}

    def create_widgets(self):
        """Create all GUI widgets"""
        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=80)
        header.pack(fill=tk.X)

        title_label = tk.Label(
            header,
            text="BC SCAN TOOL",
            font=('Arial', 24, 'bold'),
            fg='white',
            bg='#2c3e50'
        )
        title_label.pack(pady=20)

        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel - Vehicle selection and info
        left_panel = tk.Frame(main_container, width=300, relief=tk.RAISED, borderwidth=1)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        self.create_vehicle_panel(left_panel)

        # Right panel - Main content
        right_panel = tk.Frame(main_container)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Notebook for tabs
        self.notebook = ttk.Notebook(right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.create_overview_tab()
        self.create_diagnostics_tab()
        self.create_predictions_tab()
        self.create_data_tab()
        self.create_reports_tab()

        # Status bar
        self.create_status_bar()

    def create_vehicle_panel(self, parent):
        """Create vehicle selection and info panel"""
        # Vehicle selection
        selection_frame = tk.LabelFrame(parent, text="Vehicle Selection", padx=10, pady=10)
        selection_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(selection_frame, text="Select Vehicle:").pack(anchor=tk.W)

        self.vehicle_var = tk.StringVar()
        self.vehicle_dropdown = ttk.Combobox(
            selection_frame,
            textvariable=self.vehicle_var,
            state='readonly',
            width=25
        )
        self.vehicle_dropdown.pack(fill=tk.X, pady=5)
        self.vehicle_dropdown.bind('<<ComboboxSelected>>', self.on_vehicle_selected)

        # Refresh button
        tk.Button(
            selection_frame,
            text="🔄 Refresh Data",
            command=self.refresh_data
        ).pack(fill=tk.X, pady=5)

        # Vehicle info display
        self.info_frame = tk.LabelFrame(parent, text="Vehicle Information", padx=10, pady=10)
        self.info_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.info_text = scrolledtext.ScrolledText(
            self.info_frame,
            height=15,
            width=30,
            wrap=tk.WORD,
            font=('Courier', 9)
        )
        self.info_text.pack(fill=tk.BOTH, expand=True)

        # Action buttons
        action_frame = tk.Frame(parent)
        action_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(
            action_frame,
            text="Run Analysis",
            command=self.run_analysis,
            bg='#3498db',
            fg='white'
        ).pack(fill=tk.X, pady=2)

        tk.Button(
            action_frame,
            text="Export Report",
            command=self.export_report
        ).pack(fill=tk.X, pady=2)

    def create_overview_tab(self):
        """Create overview tab with health scores"""
        overview = tk.Frame(self.notebook)
        self.notebook.add(overview, text="Overview")

        # Health score display
        score_frame = tk.LabelFrame(overview, text="Vehicle Health Score", padx=20, pady=20)
        score_frame.pack(fill=tk.X, padx=10, pady=10)

        self.health_score_label = tk.Label(
            score_frame,
            text="--",
            font=('Arial', 48, 'bold'),
            fg='#2ecc71'
        )
        self.health_score_label.pack()

        self.health_grade_label = tk.Label(
            score_frame,
            text="Grade: --",
            font=('Arial', 18)
        )
        self.health_grade_label.pack()

        # Quick stats
        stats_frame = tk.Frame(overview)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create stat cards
        self.create_stat_card(stats_frame, "Total Scans", "total_scans", 0, 0)
        self.create_stat_card(stats_frame, "Active Issues", "active_issues", 0, 1)
        self.create_stat_card(stats_frame, "Predictions", "predictions", 1, 0)
        self.create_stat_card(stats_frame, "Last Scan", "last_scan", 1, 1)

    def create_stat_card(self, parent, title, key, row, col):
        """Create a stat display card"""
        card = tk.Frame(parent, relief=tk.RAISED, borderwidth=2, bg='white')
        card.grid(row=row, column=col, padx=10, pady=10, sticky='nsew')

        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(col, weight=1)

        tk.Label(
            card,
            text=title,
            font=('Arial', 12),
            bg='white'
        ).pack(pady=(10, 5))

        value_label = tk.Label(
            card,
            text="--",
            font=('Arial', 24, 'bold'),
            bg='white'
        )
        value_label.pack(pady=(0, 10))

        # Store reference
        setattr(self, f"{key}_label", value_label)

    def create_diagnostics_tab(self):
        """Create diagnostics tab with issue list"""
        diagnostics = tk.Frame(self.notebook)
        self.notebook.add(diagnostics, text="Diagnostics")

        # Issues list
        issues_frame = tk.LabelFrame(diagnostics, text="Detected Issues", padx=10, pady=10)
        issues_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Treeview for issues
        columns = ('Severity', 'Category', 'Issue', 'Details')
        self.issues_tree = ttk.Treeview(issues_frame, columns=columns, show='headings')

        self.issues_tree.heading('Severity', text='Severity')
        self.issues_tree.heading('Category', text='Category')
        self.issues_tree.heading('Issue', text='Issue')
        self.issues_tree.heading('Details', text='Details')

        self.issues_tree.column('Severity', width=100)
        self.issues_tree.column('Category', width=150)
        self.issues_tree.column('Issue', width=200)
        self.issues_tree.column('Details', width=400)

        # Scrollbar
        scrollbar = ttk.Scrollbar(issues_frame, orient=tk.VERTICAL, command=self.issues_tree.yview)
        self.issues_tree.configure(yscrollcommand=scrollbar.set)

        self.issues_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Configure tags for severity colors
        self.issues_tree.tag_configure('CRITICAL', background='#e74c3c', foreground='white')
        self.issues_tree.tag_configure('WARNING', background='#f39c12', foreground='white')
        self.issues_tree.tag_configure('INFO', background='#3498db', foreground='white')

    def create_predictions_tab(self):
        """Create predictions tab"""
        predictions = tk.Frame(self.notebook)
        self.notebook.add(predictions, text="Predictions")

        # Predictions list
        pred_frame = tk.LabelFrame(predictions, text="Failure Predictions", padx=10, pady=10)
        pred_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        columns = ('Type', 'Issue', 'Prediction', 'Confidence', 'Time Frame')
        self.pred_tree = ttk.Treeview(pred_frame, columns=columns, show='headings')

        self.pred_tree.heading('Type', text='Type')
        self.pred_tree.heading('Issue', text='Issue')
        self.pred_tree.heading('Prediction', text='Prediction')
        self.pred_tree.heading('Confidence', text='Confidence')
        self.pred_tree.heading('Time Frame', text='Time Frame')

        self.pred_tree.column('Type', width=150)
        self.pred_tree.column('Issue', width=200)
        self.pred_tree.column('Prediction', width=300)
        self.pred_tree.column('Confidence', width=100)
        self.pred_tree.column('Time Frame', width=150)

        scrollbar = ttk.Scrollbar(pred_frame, orient=tk.VERTICAL, command=self.pred_tree.yview)
        self.pred_tree.configure(yscrollcommand=scrollbar.set)

        self.pred_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def create_data_tab(self):
        """Create data viewing tab"""
        data = tk.Frame(self.notebook)
        self.notebook.add(data, text="Data View")

        # Data display
        data_frame = tk.LabelFrame(data, text="Diagnostic Data", padx=10, pady=10)
        data_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.data_text = scrolledtext.ScrolledText(
            data_frame,
            wrap=tk.NONE,
            font=('Courier', 9)
        )
        self.data_text.pack(fill=tk.BOTH, expand=True)

        # Horizontal scrollbar
        h_scrollbar = tk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.data_text.xview)
        self.data_text.configure(xscrollcommand=h_scrollbar.set)
        h_scrollbar.pack(fill=tk.X)

    def create_reports_tab(self):
        """Create reports tab"""
        reports = tk.Frame(self.notebook)
        self.notebook.add(reports, text="Reports")

        # Report viewer
        report_frame = tk.LabelFrame(reports, text="Generated Reports", padx=10, pady=10)
        report_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.report_text = scrolledtext.ScrolledText(
            report_frame,
            wrap=tk.WORD,
            font=('Courier', 10)
        )
        self.report_text.pack(fill=tk.BOTH, expand=True)

    def create_status_bar(self):
        """Create bottom status bar"""
        status_bar = tk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = tk.Label(
            status_bar,
            text="Ready",
            anchor=tk.W,
            padx=10
        )
        self.status_label.pack(side=tk.LEFT)

        self.time_label = tk.Label(
            status_bar,
            text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            anchor=tk.E,
            padx=10
        )
        self.time_label.pack(side=tk.RIGHT)

        # Update time every second
        self.update_time()

    def update_time(self):
        """Update status bar time"""
        self.time_label.config(text=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.root.after(1000, self.update_time)

    def refresh_data(self):
        """Refresh all data from files"""
        self.status_label.config(text="Refreshing data...")

        # Reload baselines
        self.load_vehicle_baselines()

        # Update vehicle dropdown
        vehicle_list = [
            f"{v.get('year', 'Unknown')} {v.get('make', 'Unknown')} {v.get('model', 'Unknown')}"
            for vin, v in self.vehicles.items()
        ]
        self.vehicle_dropdown['values'] = vehicle_list

        if vehicle_list and not self.vehicle_var.get():
            self.vehicle_dropdown.current(0)
            self.on_vehicle_selected()

        self.status_label.config(text=f"Loaded {len(vehicle_list)} vehicles")

    def on_vehicle_selected(self, event=None):
        """Handle vehicle selection"""
        selection = self.vehicle_var.get()
        if not selection:
            return

        # Find VIN from selection
        for vin, data in self.vehicles.items():
            vehicle_name = f"{data.get('year', 'Unknown')} {data.get('make', 'Unknown')} {data.get('model', 'Unknown')}"
            if vehicle_name == selection:
                self.current_vehicle = vin
                self.display_vehicle_info(vin, data)
                break

    def display_vehicle_info(self, vin, data):
        """Display vehicle information"""
        self.info_text.delete('1.0', tk.END)

        info = f"""
VEHICLE INFORMATION
{'='*30}

VIN: {vin}
Year: {data.get('year', 'Unknown')}
Make: {data.get('make', 'Unknown')}
Model: {data.get('model', 'Unknown')}

BASELINES
{'='*30}

"""

        if 'baselines' in data:
            for param, values in data['baselines'].items():
                info += f"\n{param}:\n"
                info += f"  Min: {values.get('min', 'N/A')}\n"
                info += f"  Max: {values.get('max', 'N/A')}\n"
                info += f"  Avg: {values.get('mean', 'N/A')}\n"

        self.info_text.insert('1.0', info)

    def run_analysis(self):
        """Run full diagnostic analysis"""
        if not self.current_vehicle:
            messagebox.showwarning("No Vehicle", "Please select a vehicle first")
            return

        if not DIAGNOSTIC_AVAILABLE:
            messagebox.showerror("Module Error", "Diagnostic modules not available")
            return

        self.status_label.config(text="Running analysis...")

        try:
            # Load data
            processed_file = self.data_dir / 'processed' / 'diagnostic_reports.csv'
            if not processed_file.exists():
                messagebox.showerror("No Data", "No processed data found. Run obd2.py first.")
                return

            pdf_data = pd.read_csv(processed_file)

            # Filter for current vehicle
            vehicle_data = pdf_data[pdf_data['vin'] == self.current_vehicle]

            if vehicle_data.empty:
                messagebox.showwarning("No Data", f"No data found for VIN {self.current_vehicle}")
                return

            # Run diagnostics
            engine = DiagnosticEngine(None, vehicle_data)
            issues = engine.analyze()

            # Run predictions
            predictor = PredictiveAnalytics(vehicle_data)
            predictions, health_scores = predictor.analyze()

            # Update displays
            self.update_diagnostics_display(issues)
            self.update_predictions_display(predictions)
            self.update_overview(health_scores, issues, predictions, vehicle_data)

            self.status_label.config(text="Analysis complete")

        except Exception as e:
            messagebox.showerror("Analysis Error", f"Error running analysis: {e}")
            self.status_label.config(text="Analysis failed")

    def update_diagnostics_display(self, issues):
        """Update diagnostics tab with issues"""
        # Clear existing
        for item in self.issues_tree.get_children():
            self.issues_tree.delete(item)

        # Add issues
        for issue in issues:
            severity = issue.get('severity', 'INFO')
            self.issues_tree.insert(
                '',
                tk.END,
                values=(
                    severity,
                    issue.get('category', ''),
                    issue.get('issue', ''),
                    issue.get('details', '')
                ),
                tags=(severity,)
            )

    def update_predictions_display(self, predictions):
        """Update predictions tab"""
        # Clear existing
        for item in self.pred_tree.get_children():
            self.pred_tree.delete(item)

        # Add predictions
        for pred in predictions:
            self.pred_tree.insert(
                '',
                tk.END,
                values=(
                    pred.get('type', ''),
                    pred.get('issue', ''),
                    pred.get('prediction', ''),
                    pred.get('confidence', ''),
                    pred.get('time_frame', 'N/A')
                )
            )

    def update_overview(self, health_scores, issues, predictions, data):
        """Update overview tab"""
        # Get health score for current vehicle
        if self.current_vehicle in health_scores:
            score = health_scores[self.current_vehicle]['overall_score']
            grade = health_scores[self.current_vehicle]['grade']

            self.health_score_label.config(text=f"{score:.0f}")
            self.health_grade_label.config(text=f"Grade: {grade}")

            # Color code
            if score >= 90:
                color = '#2ecc71'  # Green
            elif score >= 70:
                color = '#f39c12'  # Orange
            else:
                color = '#e74c3c'  # Red

            self.health_score_label.config(fg=color)

        # Update stats
        self.total_scans_label.config(text=str(len(data)))
        self.active_issues_label.config(text=str(len(issues)))
        self.predictions_label.config(text=str(len(predictions)))

        if 'test_time' in data.columns and len(data) > 0:
            last_scan = data['test_time'].iloc[-1]
            self.last_scan_label.config(text=last_scan[:10])

    def export_report(self):
        """Export analysis report"""
        if not self.current_vehicle:
            messagebox.showwarning("No Vehicle", "Please select a vehicle first")
            return

        # Ask for save location
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )

        if filename:
            try:
                # Generate report content
                report = self.generate_report()

                with open(filename, 'w') as f:
                    f.write(report)

                messagebox.showinfo("Success", f"Report exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Error exporting report: {e}")

    def generate_report(self):
        """Generate text report"""
        vehicle_info = self.vehicles.get(self.current_vehicle, {})

        report = f"""
BC SCAN TOOL - DIAGNOSTIC REPORT
{'='*70}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

VEHICLE INFORMATION
{'='*70}
VIN: {self.current_vehicle}
Year: {vehicle_info.get('year', 'Unknown')}
Make: {vehicle_info.get('make', 'Unknown')}
Model: {vehicle_info.get('model', 'Unknown')}

HEALTH SCORE
{'='*70}
Overall Score: {self.health_score_label.cget('text')}
Grade: {self.health_grade_label.cget('text').replace('Grade: ', '')}

DIAGNOSTICS
{'='*70}
"""

        # Add issues from tree
        for item in self.issues_tree.get_children():
            values = self.issues_tree.item(item)['values']
            report += f"\n[{values[0]}] {values[1]}: {values[2]}\n"
            report += f"  Details: {values[3]}\n"

        report += f"\n\nPREDICTIONS\n{'='*70}\n"

        # Add predictions from tree
        for item in self.pred_tree.get_children():
            values = self.pred_tree.item(item)['values']
            report += f"\n{values[1]}\n"
            report += f"  Prediction: {values[2]}\n"
            report += f"  Confidence: {values[3]}\n"

        return report


if __name__ == "__main__":
    if not TKINTER_AVAILABLE:
        print("\n" + "!"*70)
        print(" ERROR: TKINTER NOT FOUND")
        print(" " + "!"*70)
        print("\nThe 'tkinter' module is required for the GUI Dashboard.")
        print("\nDIAGNOSIS:")
        print("Your Python environment is missing the Tcl/Tk interface.")
        print("\nHOW TO FIX (macOS):")
        print("1. Install python-tk using Homebrew:")
        print("   brew install python-tk@3.11")
        print("\n2. OR use the official Python.org installer which includes Tkinter.")
        print("\n3. OR if you are using PyCharm, go to Settings -> Project -> Python Interpreter")
        print("   and select a Python version that has Tkinter (e.g., /usr/bin/python3).")
        print("\n" + "!"*70 + "\n")
        sys.exit(1)

    root = tk.Tk()
    app = VehicleDiagnosticGUI(root)
    root.mainloop()
