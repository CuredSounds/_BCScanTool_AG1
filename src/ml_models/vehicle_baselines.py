"""
Vehicle-Specific Baseline Profiling
Creates and compares against manufacturer/model-specific baselines
"""

import pandas as pd
import numpy as np
import json
import os
from typing import Dict, List


class VehicleBaseline:
    """
    Stores and manages baseline performance metrics for a specific vehicle
    """

    def __init__(self, vin, make, model, year):
        """
        Initialize vehicle baseline

        Args:
            vin: Vehicle Identification Number
            make: Vehicle manufacturer
            model: Vehicle model
            year: Model year
        """
        self.vin = vin
        self.make = make
        self.model = model
        self.year = year
        self.baselines = {}
        self.health_history = []

    def set_baseline(self, parameter, min_val, max_val, mean_val, std_val):
        """Set baseline range for a parameter"""
        self.baselines[parameter] = {
            'min': min_val,
            'max': max_val,
            'mean': mean_val,
            'std': std_val,
            'range': (min_val, max_val)
        }

    def check_parameter(self, parameter, value):
        """
        Check if parameter value is within baseline range

        Returns:
            dict with status and deviation
        """
        if parameter not in self.baselines:
            return {
                'status': 'UNKNOWN',
                'message': 'No baseline available',
                'deviation': None
            }

        baseline = self.baselines[parameter]
        min_val, max_val = baseline['range']
        mean_val = baseline['mean']

        if min_val <= value <= max_val:
            deviation_pct = abs((value - mean_val) / mean_val * 100) if mean_val != 0 else 0
            return {
                'status': 'NORMAL',
                'message': f'Within normal range ({min_val:.1f}-{max_val:.1f})',
                'deviation': deviation_pct
            }
        else:
            deviation = value - mean_val
            if value < min_val:
                return {
                    'status': 'LOW',
                    'message': f'Below normal range (expected: {min_val:.1f})',
                    'deviation': deviation
                }
            else:
                return {
                    'status': 'HIGH',
                    'message': f'Above normal range (expected: {max_val:.1f})',
                    'deviation': deviation
                }

    def to_dict(self):
        """Convert to dictionary for serialization"""
        return {
            'vin': self.vin,
            'make': self.make,
            'model': self.model,
            'year': self.year,
            'baselines': self.baselines,
            'health_history': self.health_history
        }

    @classmethod
    def from_dict(cls, data):
        """Create from dictionary"""
        baseline = cls(data['vin'], data['make'], data['model'], data['year'])
        baseline.baselines = data.get('baselines', {})
        baseline.health_history = data.get('health_history', [])
        return baseline


class BaselineManager:
    """
    Manages baselines for multiple vehicles
    """

    def __init__(self, data_dir='data'):
        """
        Initialize baseline manager

        Args:
            data_dir: Directory to store baseline data
        """
        self.data_dir = data_dir
        self.baselines_file = os.path.join(data_dir, 'vehicle_baselines.json')
        self.vehicle_baselines = {}
        self.load_baselines()

    def create_baseline_from_data(self, vin, make, model, year, pdf_data, csv_data=None):
        """
        Create baseline profile from historical vehicle data

        Args:
            vin: Vehicle VIN
            make: Manufacturer
            model: Model
            year: Year
            pdf_data: PDF snapshot data for this vehicle
            csv_data: Optional CSV time-series data
        """
        print(f"\nCreating baseline for {year} {make} {model} (VIN: {vin})")

        baseline = VehicleBaseline(vin, make, model, year)

        # Use first 25% of data as "healthy baseline" (when vehicle was newer)
        baseline_count = max(3, len(pdf_data) // 4)
        baseline_data = pdf_data.head(baseline_count)

        print(f"  Using {baseline_count} early scans to establish baseline")

        # Engine Speed (RPM)
        if 'engine_speed_rpm' in pdf_data.columns:
            rpm_data = pd.to_numeric(baseline_data['engine_speed_rpm'], errors='coerce').dropna()
            if len(rpm_data) > 0:
                # Filter to idle range
                idle_rpm = rpm_data[(rpm_data > 500) & (rpm_data < 1000)]
                if len(idle_rpm) > 0:
                    baseline.set_baseline(
                        'idle_rpm',
                        idle_rpm.min(),
                        idle_rpm.max(),
                        idle_rpm.mean(),
                        idle_rpm.std()
                    )
                    print(f"  ✓ Idle RPM baseline: {idle_rpm.mean():.0f} RPM (±{idle_rpm.std():.0f})")

        # Coolant Temperature
        if 'coolant_temp_f' in pdf_data.columns:
            temp_data = pd.to_numeric(baseline_data['coolant_temp_f'], errors='coerce').dropna()
            if len(temp_data) > 0:
                operating_temp = temp_data[temp_data > 160]  # Operating temperature
                if len(operating_temp) > 0:
                    baseline.set_baseline(
                        'operating_temp',
                        operating_temp.min(),
                        operating_temp.max(),
                        operating_temp.mean(),
                        operating_temp.std()
                    )
                    print(f"  ✓ Operating temp baseline: {operating_temp.mean():.0f}°F (±{operating_temp.std():.0f})")

        # Misfire baseline (should be low/zero when healthy)
        misfire_cols = [c for c in pdf_data.columns if 'misfire_history' in c]
        if misfire_cols:
            total_misfires = []
            for col in misfire_cols:
                mf = pd.to_numeric(baseline_data[col], errors='coerce').dropna()
                total_misfires.extend(mf.values)

            if total_misfires:
                total_misfires = np.array(total_misfires)
                baseline.set_baseline(
                    'misfire_per_cylinder',
                    total_misfires.min(),
                    np.percentile(total_misfires, 75),  # 75th percentile as max "normal"
                    total_misfires.mean(),
                    total_misfires.std()
                )
                print(f"  ✓ Misfire baseline: {total_misfires.mean():.1f} per cylinder (max normal: {np.percentile(total_misfires, 75):.0f})")

        # Store baseline
        self.vehicle_baselines[vin] = baseline
        self.save_baselines()

        return baseline

    def get_baseline(self, vin):
        """Get baseline for specific vehicle"""
        return self.vehicle_baselines.get(vin)

    def compare_to_baseline(self, vin, current_data):
        """
        Compare current vehicle state to baseline

        Args:
            vin: Vehicle VIN
            current_data: Current sensor readings (dict or Series)

        Returns:
            Comparison results
        """
        baseline = self.get_baseline(vin)
        if not baseline:
            return {
                'status': 'NO_BASELINE',
                'message': 'No baseline available for this vehicle'
            }

        comparisons = {}

        # Check idle RPM
        if 'engine_speed_rpm' in current_data:
            rpm = current_data.get('engine_speed_rpm', current_data.get('engine_speed_rpm'))
            if rpm and 500 < rpm < 1000:  # Idle range
                result = baseline.check_parameter('idle_rpm', rpm)
                comparisons['idle_rpm'] = result

        # Check temperature
        if 'coolant_temp_f' in current_data:
            temp = current_data.get('coolant_temp_f')
            if temp and temp > 160:  # Operating temp
                result = baseline.check_parameter('operating_temp', temp)
                comparisons['operating_temp'] = result

        # Check misfires
        misfire_cols = [k for k in current_data.keys() if 'misfire_history' in str(k)]
        if misfire_cols:
            total_mf = sum([current_data.get(col, 0) for col in misfire_cols])
            avg_mf = total_mf / len(misfire_cols) if misfire_cols else 0
            result = baseline.check_parameter('misfire_per_cylinder', avg_mf)
            comparisons['misfire_per_cylinder'] = result

        return comparisons

    def save_baselines(self):
        """Save baselines to file"""
        data = {
            vin: baseline.to_dict()
            for vin, baseline in self.vehicle_baselines.items()
        }

        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.baselines_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"\n✓ Baselines saved to {self.baselines_file}")

    def load_baselines(self):
        """Load baselines from file"""
        if not os.path.exists(self.baselines_file):
            return

        try:
            with open(self.baselines_file, 'r') as f:
                data = json.load(f)

            for vin, baseline_data in data.items():
                self.vehicle_baselines[vin] = VehicleBaseline.from_dict(baseline_data)

            print(f"✓ Loaded {len(self.vehicle_baselines)} vehicle baselines")
        except Exception as e:
            print(f"Error loading baselines: {e}")

    def generate_baseline_report(self):
        """Generate report of all baselines"""
        print("\n" + "="*70)
        print("VEHICLE BASELINE PROFILES")
        print("="*70)

        for vin, baseline in self.vehicle_baselines.items():
            print(f"\n{baseline.year} {baseline.make} {baseline.model}")
            print(f"VIN: {vin}")
            print("\nBaseline Parameters:")

            for param, values in baseline.baselines.items():
                print(f"  {param}:")
                print(f"    Range: {values['min']:.1f} - {values['max']:.1f}")
                print(f"    Mean: {values['mean']:.1f} (±{values['std']:.1f})")


def create_vehicle_baselines(pdf_data):
    """
    Create baselines for all vehicles in dataset

    Args:
        pdf_data: PDF diagnostic data with VIN info
    """
    if 'vin' not in pdf_data.columns:
        print("No VIN data available")
        return None

    manager = BaselineManager()

    # Create baseline for each vehicle
    for vin in pdf_data['vin'].unique():
        vehicle_data = pdf_data[pdf_data['vin'] == vin].copy()

        if 'test_time' in vehicle_data.columns:
            vehicle_data['test_time_dt'] = pd.to_datetime(vehicle_data['test_time'], errors='coerce')
            vehicle_data = vehicle_data.sort_values('test_time_dt')

        if len(vehicle_data) < 3:
            print(f"Not enough data for {vin}")
            continue

        # Get vehicle info
        make = vehicle_data['make'].iloc[0] if 'make' in vehicle_data.columns else 'Unknown'
        model = vehicle_data['model'].iloc[0] if 'model' in vehicle_data.columns else 'Unknown'
        year = vehicle_data['year'].iloc[0] if 'year' in vehicle_data.columns else 'Unknown'

        manager.create_baseline_from_data(vin, make, model, year, vehicle_data)

    # Generate report
    manager.generate_baseline_report()

    return manager
