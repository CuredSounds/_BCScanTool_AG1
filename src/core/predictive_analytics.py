"""
Predictive Analytics Engine for Vehicle Diagnostics
Predicts future failures and maintenance needs based on historical data trends
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
from scipy.interpolate import interp1d
import warnings
from src import config
warnings.filterwarnings('ignore')


class PredictiveAnalytics:
    """
    Predictive maintenance and failure forecasting engine
    """

    def __init__(self, pdf_data, csv_data=None, baseline_confirmed_dates=None):
        """
        Initialize predictive analytics engine

        Args:
            pdf_data: Historical PDF diagnostic snapshots
            csv_data: Time-series sensor data (optional)
            baseline_confirmed_dates: Dict of VIN -> datetime of confirmed healthy state
        """
        self.pdf_data = pdf_data
        self.csv_data = csv_data
        self.baseline_confirmed_dates = baseline_confirmed_dates or {}
        self.predictions = []
        self.health_scores = {}
        self.baselines = {}

    def analyze(self):
        """Run complete predictive analysis"""
        print("\n" + "="*70)
        print("PREDICTIVE ANALYTICS ENGINE")
        print("="*70)

        if self.pdf_data is None or self.pdf_data.empty:
            print("No historical data available for predictions")
            return

        # 1. Build baselines for normal behavior
        self._build_baselines()

        # 2. Analyze trends over time
        self._analyze_trends()

        # 3. Predict component failures
        self._predict_failures()

        # 4. Calculate health scores
        self._calculate_health_scores()

        # 5. Estimate time to failure
        self._estimate_time_to_failure()

        # 6. Generate maintenance recommendations
        self._generate_maintenance_schedule()

        # 7. Display predictions
        self._display_predictions()

        return self.predictions

    def _build_baselines(self):
        """Build baseline profiles for normal vehicle operation"""
        print("\nBuilding baseline profiles...")

        if 'vin' not in self.pdf_data.columns:
            return

        for vin in self.pdf_data['vin'].unique():
            vehicle_data = self.pdf_data[self.pdf_data['vin'] == vin].copy()

            if 'test_time' in vehicle_data.columns:
                vehicle_data['test_time_dt'] = pd.to_datetime(vehicle_data['test_time'], errors='coerce')
                vehicle_data = vehicle_data.sort_values('test_time_dt')

            # Use confirmed baseline date if available, else first 5 scans
            confirmed_date = self.baseline_confirmed_dates.get(vin)
            if confirmed_date and 'test_time_dt' in vehicle_data.columns:
                # Scans around the confirmed date (+/- 7 days) are used as baseline
                # This ensures we use data when the vehicle was known to be healthy
                mask = (vehicle_data['test_time_dt'] >= confirmed_date - timedelta(days=7)) & \
                       (vehicle_data['test_time_dt'] <= confirmed_date + timedelta(days=7))
                baseline_scans = vehicle_data[mask]
                
                if baseline_scans.empty:
                    # Fallback to the scan closest to confirmed date
                    idx = (vehicle_data['test_time_dt'] - confirmed_date).abs().idxmin()
                    baseline_scans = vehicle_data.loc[[idx]]
                
                print(f"  Using confirmed baseline for {vin} around {confirmed_date}")
            else:
                baseline_scans = vehicle_data.head(min(5, len(vehicle_data) // 2))
                print(f"  Using heuristic baseline (first {len(baseline_scans)} scans) for {vin}")

            baseline = {}

            # Baseline misfire rates
            misfire_cols = [c for c in vehicle_data.columns if 'misfire_history' in c]
            for col in misfire_cols:
                values = pd.to_numeric(baseline_scans[col], errors='coerce').dropna()
                if len(values) > 0:
                    baseline[col] = {
                        'mean': values.mean(),
                        'std': values.std(),
                        'max': values.max()
                    }

            # Baseline RPM (from snapshots)
            if 'engine_speed_rpm' in vehicle_data.columns:
                rpm_values = pd.to_numeric(baseline_scans['engine_speed_rpm'], errors='coerce').dropna()
                if len(rpm_values) > 0:
                    baseline['engine_speed_rpm'] = {
                        'mean': rpm_values.mean(),
                        'std': rpm_values.std()
                    }

            # Baseline temperature
            if 'coolant_temp_f' in vehicle_data.columns:
                temp_values = pd.to_numeric(baseline_scans['coolant_temp_f'], errors='coerce').dropna()
                if len(temp_values) > 0:
                    baseline['coolant_temp_f'] = {
                        'mean': temp_values.mean(),
                        'std': temp_values.std()
                    }

            self.baselines[vin] = baseline

    def _analyze_trends(self):
        """Analyze trends over time to detect degradation"""
        print("Analyzing degradation trends...")

        if 'vin' not in self.pdf_data.columns:
            return

        for vin in self.pdf_data['vin'].unique():
            vehicle_data = self.pdf_data[self.pdf_data['vin'] == vin].copy()

            if len(vehicle_data) < 3:  # Need at least 3 data points for trend
                continue

            # Sort by time
            if 'test_time' in vehicle_data.columns:
                vehicle_data['test_time_dt'] = pd.to_datetime(vehicle_data['test_time'], errors='coerce')
                vehicle_data = vehicle_data.sort_values('test_time_dt').dropna(subset=['test_time_dt'])

            if len(vehicle_data) < 3:
                continue

            # Analyze misfire trends
            self._analyze_misfire_trends(vehicle_data, vin)

            # Analyze temperature trends
            self._analyze_temperature_trends(vehicle_data, vin)

    def _analyze_misfire_trends(self, vehicle_data, vin):
        """Analyze misfire count trends over time"""
        misfire_cols = [c for c in vehicle_data.columns if 'misfire_history' in c]

        for col in misfire_cols:
            cyl_num = col.split('cyl')[1]
            misfire_counts = pd.to_numeric(vehicle_data[col], errors='coerce').dropna()

            if len(misfire_counts) < 3:
                continue

            # Calculate trend (linear regression)
            x = np.arange(len(misfire_counts))
            y = misfire_counts.values

            # Skip if all zeros
            if y.sum() == 0:
                continue

            slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

            # Increasing trend with statistical significance
            if slope > 5 and p_value < 0.1:  # More than 5 misfires increase per scan
                severity = 'CRITICAL' if slope > 20 else 'WARNING'

                self.predictions.append({
                    'type': 'TREND',
                    'severity': severity,
                    'category': 'Component Degradation',
                    'issue': f'Cylinder {cyl_num} Degrading',
                    'details': f'Misfire count increasing by {slope:.1f} per scan (R²={r_value**2:.2f})',
                    'prediction': f'Cylinder {cyl_num} will require attention soon',
                    'confidence': f'{min(abs(r_value) * 100, 100):.0f}%',
                    'vin': vin
                })

    def _analyze_temperature_trends(self, vehicle_data, vin):
        """Analyze temperature trends over time"""
        if 'coolant_temp_f' not in vehicle_data.columns:
            return

        temps = pd.to_numeric(vehicle_data['coolant_temp_f'], errors='coerce').dropna()

        if len(temps) < 3:
            return

        x = np.arange(len(temps))
        y = temps.values

        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)

        # Rising temperature trend
        slope_threshold = 2 if config.TEMP_UNIT == "celsius" else 3
        unit = "°C" if config.TEMP_UNIT == "celsius" else "°F"

        if slope > slope_threshold and p_value < 0.1:
            self.predictions.append({
                'type': 'TREND',
                'severity': 'WARNING',
                'category': 'Cooling System',
                'issue': 'Engine Running Hotter Over Time',
                'details': f'Temperature increasing by {slope:.1f}{unit} per scan',
                'prediction': 'Cooling system degradation - may overheat soon',
                'confidence': f'{min(abs(r_value) * 100, 100):.0f}%',
                'vin': vin
            })

    def _predict_failures(self):
        """Predict component failures based on current state"""
        print("Predicting component failures...")

        if 'vin' not in self.pdf_data.columns:
            return

        for vin in self.pdf_data['vin'].unique():
            vehicle_data = self.pdf_data[self.pdf_data['vin'] == vin].copy()

            if 'test_time' in vehicle_data.columns:
                vehicle_data['test_time_dt'] = pd.to_datetime(vehicle_data['test_time'], errors='coerce')
                vehicle_data = vehicle_data.sort_values('test_time_dt')

            latest = vehicle_data.iloc[-1]

            # Predict ignition coil failure
            self._predict_coil_failure(latest, vin)

            # Predict catalytic converter failure
            self._predict_catalyst_failure(latest, vin, vehicle_data)

            # Predict fuel injector failure
            self._predict_injector_failure(latest, vin)

    def _predict_coil_failure(self, latest_scan, vin):
        """Predict ignition coil failure based on misfire patterns"""
        misfire_current_cols = [c for c in latest_scan.index if 'misfire_current' in c]

        for col in misfire_current_cols:
            count = latest_scan.get(col, 0)
            if pd.notna(count) and count > 20:  # Significant current misfires
                cyl_num = col.split('cyl')[1]

                # Check historical data
                hist_col = f'misfire_history_cyl{cyl_num}'
                hist_count = latest_scan.get(hist_col, 0)

                if pd.notna(hist_count) and hist_count > 500:
                    self.predictions.append({
                        'type': 'FAILURE_PREDICTION',
                        'severity': 'CRITICAL',
                        'category': 'Ignition System',
                        'issue': f'Cylinder {cyl_num} Coil Failure Imminent',
                        'details': f'Current misfires: {int(count)}, Historical: {int(hist_count)}',
                        'prediction': f'Ignition coil #{cyl_num} likely to fail within 30 days',
                        'confidence': '85%',
                        'vin': vin
                    })

    def _predict_catalyst_failure(self, latest_scan, vin, vehicle_data):
        """Predict catalytic converter failure"""
        # High misfire counts damage catalysts
        total_misfires = latest_scan.get('total_misfire', 0)

        if pd.notna(total_misfires) and total_misfires > 200:
            # Check if misfires are persistent
            if len(vehicle_data) >= 3:
                recent_scans = vehicle_data.tail(3)
                total_misfire_trend = pd.to_numeric(recent_scans['total_misfire'], errors='coerce').dropna()

                if len(total_misfire_trend) >= 2 and total_misfire_trend.mean() > 100:
                    self.predictions.append({
                        'type': 'FAILURE_PREDICTION',
                        'severity': 'WARNING',
                        'category': 'Emissions System',
                        'issue': 'Catalytic Converter Damage Risk',
                        'details': f'Prolonged misfires ({int(total_misfires)} total) damage catalyst',
                        'prediction': 'Catalytic converter may fail within 3-6 months if misfires continue',
                        'confidence': '70%',
                        'vin': vin
                    })

    def _predict_injector_failure(self, latest_scan, vin):
        """Predict fuel injector failure"""
        # Check for cylinder-specific misfires
        misfire_history_cols = [c for c in latest_scan.index if 'misfire_history' in c]

        for col in misfire_history_cols:
            count = latest_scan.get(col, 0)
            if pd.notna(count) and 100 < count < 500:  # Moderate but persistent
                cyl_num = col.split('cyl')[1]

                self.predictions.append({
                    'type': 'FAILURE_PREDICTION',
                    'severity': 'WARNING',
                    'category': 'Fuel System',
                    'issue': f'Cylinder {cyl_num} Fuel Injector Wearing',
                    'details': f'Moderate misfire count: {int(count)}',
                    'prediction': f'Fuel injector #{cyl_num} may need cleaning or replacement',
                    'confidence': '60%',
                    'vin': vin
                })
                break  # Only report once per vehicle

    def _calculate_health_scores(self):
        """Calculate overall vehicle health scores (0-100)"""
        print("Calculating health scores...")

        if 'vin' not in self.pdf_data.columns:
            return

        for vin in self.pdf_data['vin'].unique():
            vehicle_data = self.pdf_data[self.pdf_data['vin'] == vin].copy()

            if 'test_time' in vehicle_data.columns:
                vehicle_data['test_time_dt'] = pd.to_datetime(vehicle_data['test_time'], errors='coerce')
                vehicle_data = vehicle_data.sort_values('test_time_dt')

            latest = vehicle_data.iloc[-1]

            # Start with perfect score
            health_score = 100.0

            # Deduct points for misfires
            total_misfires = latest.get('total_misfire', 0)
            if pd.notna(total_misfires):
                health_score -= min(total_misfires / 10, 40)  # Max 40 points deduction

            # Deduct for individual cylinder issues
            misfire_history_cols = [c for c in latest.index if 'misfire_history' in c]
            max_cylinder_misfire = 0
            for col in misfire_history_cols:
                count = latest.get(col, 0)
                if pd.notna(count):
                    max_cylinder_misfire = max(max_cylinder_misfire, count)

            health_score -= min(max_cylinder_misfire / 20, 30)  # Max 30 points

            # Deduct for trend deterioration
            trend_penalty = len([p for p in self.predictions if p.get('vin') == vin and p['type'] == 'TREND']) * 5
            health_score -= min(trend_penalty, 20)

            # Keep in range
            health_score = max(0, min(100, health_score))

            self.health_scores[vin] = {
                'score': health_score,
                'grade': self._get_health_grade(health_score),
                'status': self._get_health_status(health_score)
            }

    def _get_health_grade(self, score):
        """Convert health score to letter grade"""
        if score >= 90:
            return 'A'
        elif score >= 80:
            return 'B'
        elif score >= 70:
            return 'C'
        elif score >= 60:
            return 'D'
        else:
            return 'F'

    def _get_health_status(self, score):
        """Get health status description"""
        if score >= 90:
            return 'Excellent - No immediate concerns'
        elif score >= 80:
            return 'Good - Minor issues to monitor'
        elif score >= 70:
            return 'Fair - Some maintenance needed'
        elif score >= 60:
            return 'Poor - Attention required soon'
        else:
            return 'Critical - Immediate attention required'

    def _estimate_time_to_failure(self):
        """Estimate time until component failures"""
        print("Estimating time to failure...")

        # This is done within individual prediction functions
        # Could be expanded with more sophisticated models

    def _generate_maintenance_schedule(self):
        """Generate recommended maintenance schedule"""
        print("Generating maintenance recommendations...")

        for vin in self.health_scores.keys():
            score = self.health_scores[vin]['score']

            # Get all predictions for this VIN
            vin_predictions = [p for p in self.predictions if p.get('vin') == vin]

            if score < 70 and vin_predictions:
                # Generate maintenance schedule
                critical = [p for p in vin_predictions if p['severity'] == 'CRITICAL']
                warnings = [p for p in vin_predictions if p['severity'] == 'WARNING']

                schedule = {
                    'vin': vin,
                    'immediate': len(critical),
                    'within_30_days': len([p for p in vin_predictions if 'within 30 days' in str(p.get('prediction', ''))]),
                    'within_90_days': len(warnings),
                    'health_score': score
                }

                self.predictions.append({
                    'type': 'MAINTENANCE_SCHEDULE',
                    'severity': 'INFO',
                    'category': 'Preventive Maintenance',
                    'issue': 'Scheduled Maintenance Required',
                    'details': f'Immediate: {schedule["immediate"]}, 30-day: {schedule["within_30_days"]}, 90-day: {schedule["within_90_days"]}',
                    'prediction': f'Health Score: {score:.0f}/100 - Schedule maintenance to prevent failures',
                    'confidence': '100%',
                    'vin': vin
                })

    def _display_predictions(self):
        """Display prediction results"""
        if not self.predictions and not self.health_scores:
            print("\n✓ No predictive insights available (insufficient historical data)")
            return

        # Display health scores
        print("\n" + "-"*70)
        print("VEHICLE HEALTH SCORES")
        print("-"*70)

        for vin, health in self.health_scores.items():
            vehicle_info = self._get_vehicle_info(vin)
            print(f"\n{vehicle_info}")
            print(f"  Health Score: {health['score']:.0f}/100 (Grade: {health['grade']})")
            print(f"  Status: {health['status']}")

        # Display predictions
        if self.predictions:
            print("\n" + "-"*70)
            print("PREDICTIVE INSIGHTS")
            print("-"*70)

            # Group by type
            trends = [p for p in self.predictions if p['type'] == 'TREND']
            failures = [p for p in self.predictions if p['type'] == 'FAILURE_PREDICTION']
            maintenance = [p for p in self.predictions if p['type'] == 'MAINTENANCE_SCHEDULE']

            if trends:
                print("\n📊 DEGRADATION TRENDS:")
                for pred in trends:
                    severity_icon = {'CRITICAL': '🔴', 'WARNING': '⚠️', 'INFO': 'ℹ️'}.get(pred['severity'], '•')
                    print(f"\n{severity_icon} {pred['issue']}")
                    print(f"   {pred['details']}")
                    print(f"   Prediction: {pred['prediction']} (Confidence: {pred['confidence']})")

            if failures:
                print("\n⚠️  FAILURE PREDICTIONS:")
                for pred in failures:
                    severity_icon = {'CRITICAL': '🔴', 'WARNING': '⚠️', 'INFO': 'ℹ️'}.get(pred['severity'], '•')
                    print(f"\n{severity_icon} {pred['issue']}")
                    print(f"   {pred['details']}")
                    print(f"   Prediction: {pred['prediction']} (Confidence: {pred['confidence']})")

            if maintenance:
                print("\n🔧 MAINTENANCE SCHEDULE:")
                for pred in maintenance:
                    print(f"\n   {pred['details']}")
                    print(f"   {pred['prediction']}")

        print("\n" + "="*70)

    def _get_vehicle_info(self, vin):
        """Get vehicle information string"""
        vehicle_data = self.pdf_data[self.pdf_data['vin'] == vin].iloc[0]

        year = vehicle_data.get('year', 'Unknown')
        make = vehicle_data.get('make', 'Unknown')
        model = vehicle_data.get('model', 'Unknown')

        return f"{year} {make} {model} (VIN: {vin})"

    def export_predictions(self, output_path):
        """Export predictions to CSV"""
        if not self.predictions:
            print("No predictions to export")
            return

        df = pd.DataFrame(self.predictions)
        df.to_csv(output_path, index=False)
        print(f"Predictions exported to: {output_path}")


def run_predictive_analytics(pdf_data, csv_data=None, baseline_confirmed_dates=None):
    """
    Main entry point for predictive analytics

    Args:
        pdf_data: DataFrame with PDF diagnostic snapshots
        csv_data: DataFrame with time-series sensor data (optional)
        baseline_confirmed_dates: Dict of VIN -> datetime
    """
    engine = PredictiveAnalytics(pdf_data, csv_data, baseline_confirmed_dates)
    predictions = engine.analyze()

    # Export predictions
    from src import config
    output_path = config.PROCESSED_DIR / 'predictions.csv'
    engine.export_predictions(output_path)

    return predictions, engine.health_scores
