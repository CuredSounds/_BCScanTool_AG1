"""
Intelligent Diagnostic Engine
Analyzes time-series vehicle data to detect patterns and diagnose problems
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.signal import find_peaks
import warnings
from src.core.pid_analyzer import PIDAnalyzer
warnings.filterwarnings('ignore')


class DiagnosticEngine:
    """
    Analyzes vehicle diagnostic data and identifies patterns indicating problems
    """

    def __init__(self, dataframe, pdf_data=None):
        """
        Initialize diagnostic engine with sensor data

        Args:
            dataframe: Time-series sensor data from CSVs
            pdf_data: Parsed PDF diagnostic report data
        """
        self.df = dataframe
        self.pdf_data = pdf_data
        self.issues = []

    def analyze(self):
        """Run complete diagnostic analysis"""
        print("\n" + "="*70)
        print("INTELLIGENT DIAGNOSTIC ANALYSIS")
        print("="*70)

        # Analyze each data source separately
        if self.df is not None and not self.df.empty:
            self._analyze_time_series()

        if self.pdf_data is not None and not self.pdf_data.empty:
            self._analyze_snapshot_data()

        # Generate final report
        self._generate_report()

        return self.issues

    def _analyze_time_series(self):
        """Analyze time-series data from CSV files"""
        print("\nAnalyzing time-series data...")

        # Group by source file to analyze individual scans
        if 'Source_File' in self.df.columns:
            for source_file in self.df['Source_File'].unique():
                scan_data = self.df[self.df['Source_File'] == source_file].copy()
                
                # Create PID analyzer for this specific scan
                pid_analyzer = PIDAnalyzer(scan_data)

                # Analyze this scan
                self._analyze_scan(scan_data, source_file, pid_analyzer)

    def _analyze_scan(self, scan_data, source_file, pid_analyzer):
        """Analyze a single diagnostic scan"""

        # 1. Check for idle RPM issues
        self._check_idle_rpm(source_file, pid_analyzer)

        # 2. Check for RPM fluctuations
        self._check_rpm_fluctuation(source_file, pid_analyzer)

        # 3. Check for misfire correlation
        self._check_misfire_correlation(source_file, pid_analyzer)

        # 4. Check for temperature issues
        self._check_temperature_issues(source_file, pid_analyzer)

        # 5. Check for fuel system issues
        self._check_fuel_system(source_file, pid_analyzer)

        # 6. Advanced FFT frequency analysis
        self._check_frequency_domain(source_file, pid_analyzer)

    def _check_idle_rpm(self, source_file, pid_analyzer):
        """Detect idle RPM issues"""
        rpm_data_list = pid_analyzer.get_all_pid_data('engine_speed')

        for rpm_data in rpm_data_list:
            rpm_data = rpm_data.dropna()

            if len(rpm_data) < 10:  # Need enough data points
                continue

            # Check if vehicle appears to be idling (RPM < 1000)
            idle_data = rpm_data[rpm_data < 1000]

            if len(idle_data) > len(rpm_data) * 0.5:  # More than 50% of time at idle
                mean_rpm = idle_data.mean()
                std_rpm = idle_data.std()

                # Normal idle: 600-800 RPM, std < 50
                if mean_rpm < 600:
                    self.issues.append({
                        'severity': 'WARNING',
                        'category': 'Engine Performance',
                        'issue': 'Low Idle RPM',
                        'details': f'Average idle RPM: {mean_rpm:.0f} (expected 650-800)',
                        'recommendation': 'Check for vacuum leaks, dirty throttle body, or idle control valve issues',
                        'source': source_file
                    })
                elif mean_rpm > 900:
                    self.issues.append({
                        'severity': 'WARNING',
                        'category': 'Engine Performance',
                        'issue': 'High Idle RPM',
                        'details': f'Average idle RPM: {mean_rpm:.0f} (expected 650-800)',
                        'recommendation': 'Check for vacuum leaks, throttle position sensor, or idle air control valve',
                        'source': source_file
                    })

                # Check for rough idle (high variation)
                if std_rpm > 50:
                    self.issues.append({
                        'severity': 'WARNING',
                        'category': 'Engine Performance',
                        'issue': 'Rough Idle - RPM Fluctuation',
                        'details': f'RPM variation: ±{std_rpm:.0f} RPM (should be <50)',
                        'recommendation': 'Check for misfires, vacuum leaks, or engine mount issues',
                        'source': source_file
                    })

    def _check_frequency_domain(self, source_file, pid_analyzer):
        """Perform FFT on engine RPM to detect cyclical mechanical issues"""
        rpm_data_list = pid_analyzer.get_all_pid_data('engine_speed')
        
        for rpm_data in rpm_data_list:
            rpm_data = rpm_data.dropna()
            
            if len(rpm_data) < 50:
                continue
                
            # Perform FFT
            fft_result = np.fft.rfft(rpm_data.values)
            fft_freq = np.fft.rfftfreq(len(rpm_data))
            
            # Get magnitudes (ignore DC component at index 0)
            magnitudes = np.abs(fft_result)[1:]
            freqs = fft_freq[1:]
            
            if len(magnitudes) == 0:
                continue
                
            max_mag_idx = np.argmax(magnitudes)
            max_mag = magnitudes[max_mag_idx]
            
            # If the maximum magnitude is very high relative to the mean, we have a strong cyclical anomaly
            mean_mag = np.mean(magnitudes)
            
            if max_mag > mean_mag * 5 and max_mag > 500: # Thresholds for anomaly
                self.issues.append({
                    'severity': 'WARNING',
                    'category': 'Frequency Domain Analysis',
                    'issue': 'Cyclical Mechanical Anomaly Detected',
                    'details': f'FFT analysis found a strong cyclical RPM anomaly (Magnitude: {max_mag:.0f}). '
                               'This indicates a rhythmic mechanical vibration.',
                    'recommendation': 'Check for timing chain stretch, dual-mass flywheel failure, or rhythmic misfires.',
                    'source': source_file
                })
                break # Only log once per scan

    def _check_rpm_fluctuation(self, source_file, pid_analyzer):
        """Detect abnormal RPM fluctuations"""
        rpm_data_list = pid_analyzer.get_all_pid_data('engine_speed')

        for rpm_data in rpm_data_list:
            rpm_data = rpm_data.dropna()

            if len(rpm_data) < 20:
                continue

            # Calculate rate of change
            rpm_diff = rpm_data.diff().abs()

            # Find sudden spikes (>200 RPM change in one reading)
            sudden_changes = rpm_diff[rpm_diff > 200]

            if len(sudden_changes) > 5:
                self.issues.append({
                    'severity': 'WARNING',
                    'category': 'Engine Performance',
                    'issue': 'Erratic RPM Behavior',
                    'details': f'Detected {len(sudden_changes)} sudden RPM changes (>200 RPM/reading)',
                    'recommendation': 'Possible misfire, fuel delivery issue, or sensor problem',
                    'source': source_file
                })

            # Detect oscillation patterns
            peaks, _ = find_peaks(rpm_data.values, prominence=30)
            if len(peaks) > len(rpm_data) * 0.3:  # More than 30% of data points are peaks
                self.issues.append({
                    'severity': 'WARNING',
                    'category': 'Engine Performance',
                    'issue': 'RPM Oscillation Pattern',
                    'details': f'RPM oscillating {len(peaks)} times during scan',
                    'recommendation': 'Check for misfires, ignition system, or engine control module issues',
                    'source': source_file
                })

    def _check_misfire_correlation(self, source_file, pid_analyzer):
        """Check correlation between RPM and misfire data"""
        rpm_data = pid_analyzer.get_pid_data('engine_speed')
        misfire_data_list = pid_analyzer.get_all_pid_data('misfire_count')

        if rpm_data.empty or not misfire_data_list:
            return

        for misfire_data in misfire_data_list:
            # Create aligned data
            combined = pd.DataFrame({'rpm': rpm_data, 'misfire': misfire_data}).dropna()

            if len(combined) < 10:
                continue

            # Check if misfires increase when RPM is unstable
            rpm_std = combined['rpm'].rolling(window=5).std()
            misfire_rate = combined['misfire'].rolling(window=5).mean()

            correlation_data = pd.DataFrame({'rpm_std': rpm_std, 'misfire_rate': misfire_rate}).dropna()

            if len(correlation_data) > 10:
                correlation = correlation_data.corr().iloc[0, 1]

                if correlation > 0.5:  # Strong positive correlation
                    self.issues.append({
                        'severity': 'CRITICAL',
                        'category': 'Engine Performance',
                        'issue': 'Misfires Causing RPM Instability',
                        'details': f'Strong correlation ({correlation:.2f}) between RPM fluctuation and misfires',
                        'recommendation': 'Address misfire issues - check spark plugs, coils, and fuel injectors',
                        'source': source_file
                    })

    def _check_temperature_issues(self, source_file, pid_analyzer):
        """Check for temperature-related issues"""
        temp_data_list = pid_analyzer.get_all_pid_data('coolant_temp')

        for temp_data in temp_data_list:
            temp_data = temp_data.dropna()

            if len(temp_data) < 5:
                continue

            mean_temp = temp_data.mean()

            # Check for overheating (>220°F is concerning)
            if mean_temp > 220:
                self.issues.append({
                    'severity': 'CRITICAL',
                    'category': 'Cooling System',
                    'issue': 'Engine Overheating',
                    'details': f'Coolant temperature: {mean_temp:.0f}°F (normal: 180-210°F)',
                    'recommendation': 'IMMEDIATE ATTENTION: Check coolant level, thermostat, radiator, and water pump',
                    'source': source_file
                })
            elif mean_temp < 160 and len(temp_data) > 100:  # Running cold for extended time
                self.issues.append({
                    'severity': 'WARNING',
                    'category': 'Cooling System',
                    'issue': 'Engine Running Cold',
                    'details': f'Coolant temperature: {mean_temp:.0f}°F (normal: 180-210°F)',
                    'recommendation': 'Check thermostat - may be stuck open',
                    'source': source_file
                })

            # Check for rapid temperature changes
            temp_changes = temp_data.diff().abs()
            rapid_changes = temp_changes[temp_changes > 20]

            if len(rapid_changes) > 3:
                self.issues.append({
                    'severity': 'WARNING',
                    'category': 'Cooling System',
                    'issue': 'Unstable Engine Temperature',
                    'details': f'Detected {len(rapid_changes)} rapid temperature fluctuations',
                    'recommendation': 'Check thermostat, coolant level, and temperature sensor',
                    'source': source_file
                })

    def _check_fuel_system(self, source_file, pid_analyzer):
        """Check for fuel system issues"""
        # Check all fuel trim banks
        trim_pids = ['stft_bank1', 'stft_bank2', 'ltft_bank1', 'ltft_bank2']

        for pid in trim_pids:
            trim_data_list = pid_analyzer.get_all_pid_data(pid)

            for trim_data in trim_data_list:
                trim_data = trim_data.dropna()

                if len(trim_data) < 5:
                    continue

                mean_trim = trim_data.mean()

                # Normal fuel trim: -10% to +10%
                if mean_trim > 15:
                    self.issues.append({
                        'severity': 'WARNING',
                        'category': 'Fuel System',
                        'issue': 'Lean Fuel Condition',
                        'details': f'Fuel trim: +{mean_trim:.1f}% (normal: -10% to +10%)',
                        'recommendation': 'Check for vacuum leaks, low fuel pressure, or dirty MAF sensor',
                        'source': source_file
                    })
                elif mean_trim < -15:
                    self.issues.append({
                        'severity': 'WARNING',
                        'category': 'Fuel System',
                        'issue': 'Rich Fuel Condition',
                        'details': f'Fuel trim: {mean_trim:.1f}% (normal: -10% to +10%)',
                        'recommendation': 'Check for leaking injectors, faulty O2 sensor, or high fuel pressure',
                        'source': source_file
                    })

    def _analyze_snapshot_data(self):
        """Analyze snapshot data from PDF reports"""
        print("\nAnalyzing diagnostic snapshots...")

        if 'vin' not in self.pdf_data.columns:
            return

        for vin in self.pdf_data['vin'].unique():
            vehicle_data = self.pdf_data[self.pdf_data['vin'] == vin].copy()

            # Convert test_time to datetime
            if 'test_time' in vehicle_data.columns:
                vehicle_data['test_time_dt'] = pd.to_datetime(vehicle_data['test_time'], errors='coerce')
                vehicle_data = vehicle_data.sort_values('test_time_dt')

            # --- FREEZE FRAME ANALYSIS ---
            if 'source_file' in vehicle_data.columns:
                dtc_snapshots = vehicle_data[vehicle_data['source_file'].str.contains('DTC|FreezeFrame', case=False, na=False)]
                for _, scan in dtc_snapshots.iterrows():
                    self._analyze_freeze_frame(scan, vin)

            latest = vehicle_data.iloc[-1]

            # Check for misfires
            self._check_pdf_misfires(latest, vin)

    def _analyze_freeze_frame(self, scan, vin):
        """Analyze Freeze Frame data captured at the moment of a DTC"""
        source = scan.get('source_file', f'VIN: {vin}')
        
        # We look at RPM and Temp during the fault
        rpm = pd.to_numeric(scan.get('engine_speed_rpm', np.nan), errors='coerce')
        temp = pd.to_numeric(scan.get('coolant_temp_f', np.nan), errors='coerce')
        
        if pd.notna(rpm) and rpm > 4000:
            self.issues.append({
                'severity': 'WARNING',
                'category': 'Freeze Frame Analysis',
                'issue': 'High RPM at Time of Fault',
                'details': f'Freeze frame shows fault occurred at {rpm:.0f} RPM, indicating an issue under heavy engine load.',
                'recommendation': 'Investigate fuel pressure, ignition timing, and mass air flow under high load conditions.',
                'source': source
            })
            
        if pd.notna(temp):
            if temp > 220:
                self.issues.append({
                    'severity': 'CRITICAL',
                    'category': 'Freeze Frame Analysis',
                    'issue': 'Overheating at Time of Fault',
                    'details': f'Freeze frame shows engine coolant was {temp:.0f}°F when the code was set.',
                    'recommendation': 'Check thermostat, coolant level, and water pump immediately.',
                    'source': source
                })
            elif temp < 160 and temp > 0:
                self.issues.append({
                    'severity': 'INFO',
                    'category': 'Freeze Frame Analysis',
                    'issue': 'Cold Engine at Time of Fault',
                    'details': f'Freeze frame shows engine was cold ({temp:.0f}°F) when the code was set.',
                    'recommendation': 'Fault only occurs during open-loop/cold start. Check cold enrichment, secondary air injection, or ECT sensor.',
                    'source': source
                })

    def _check_pdf_misfires(self, scan, vin):
        """Analyze misfire patterns from PDF data"""
        misfire_history_cols = [c for c in scan.index if 'misfire_history' in c]
        misfire_current_cols = [c for c in scan.index if 'misfire_current' in c]

        # Find cylinders with misfires
        problem_cylinders = []

        for col in misfire_history_cols:
            count = scan.get(col, 0)
            if pd.notna(count) and count > 0:
                cyl_num = col.split('cyl')[1]
                problem_cylinders.append((int(cyl_num), int(count)))

        if not problem_cylinders:
            return

        # Sort by misfire count
        problem_cylinders.sort(key=lambda x: x[1], reverse=True)

        # Identify worst cylinder
        worst_cyl, worst_count = problem_cylinders[0]

        if worst_count > 100:
            severity = 'CRITICAL'
        elif worst_count > 10:
            severity = 'WARNING'
        else:
            severity = 'INFO'

        # Check if it's isolated to one cylinder or multiple
        if len(problem_cylinders) == 1:
            diagnosis = self._diagnose_single_cylinder_misfire(worst_cyl, worst_count)
        else:
            diagnosis = self._diagnose_multiple_cylinder_misfire(problem_cylinders)

        self.issues.append({
            'severity': severity,
            'category': 'Ignition/Fuel System',
            'issue': diagnosis['issue'],
            'details': diagnosis['details'],
            'recommendation': diagnosis['recommendation'],
            'source': f"VIN: {vin}"
        })

    def _diagnose_single_cylinder_misfire(self, cylinder, count):
        """Diagnose issues with a single cylinder misfiring"""
        return {
            'issue': f'Cylinder {cylinder} Misfire',
            'details': f'Cylinder {cylinder} has {count} misfires (isolated to one cylinder)',
            'recommendation': f'Cylinder {cylinder} specific issue - Check in this order:\n' +
                            f'  1. Spark plug #{cylinder}\n' +
                            f'  2. Ignition coil #{cylinder}\n' +
                            f'  3. Fuel injector #{cylinder}\n' +
                            f'  4. Compression test on cylinder #{cylinder}\n' +
                            f'  5. Valve issues (burnt valve, bent valve)'
        }

    def _diagnose_multiple_cylinder_misfire(self, cylinders):
        """Diagnose issues with multiple cylinders misfiring"""
        cyl_nums = [c[0] for c in cylinders]
        total_misfires = sum(c[1] for c in cylinders)

        # Check if cylinders are on same bank
        if len(cyl_nums) >= 2:
            return {
                'issue': f'Multiple Cylinder Misfire (Cylinders: {", ".join(map(str, cyl_nums))})',
                'details': f'{len(cylinders)} cylinders affected, {total_misfires} total misfires',
                'recommendation': 'Multiple cylinders affected - Check:\n' +
                                '  1. Fuel pressure (low pressure affects all cylinders)\n' +
                                '  2. Air intake system (vacuum leaks, MAF sensor)\n' +
                                '  3. Engine timing (timing chain/belt)\n' +
                                '  4. Compression test on all cylinders\n' +
                                '  5. Fuel quality (water in fuel, bad gas)'
            }

        return {
            'issue': 'Multiple Cylinder Misfire',
            'details': f'{len(cylinders)} cylinders misfiring',
            'recommendation': 'Check common systems affecting multiple cylinders'
        }

    def _generate_report(self):
        """Generate diagnostic report"""
        if not self.issues:
            print("\n✓ No significant issues detected")
            return

        print(f"\n{len(self.issues)} issues detected:\n")

        # Sort by severity
        severity_order = {'CRITICAL': 0, 'WARNING': 1, 'INFO': 2}
        sorted_issues = sorted(self.issues, key=lambda x: severity_order.get(x['severity'], 3))

        for i, issue in enumerate(sorted_issues, 1):
            severity_icon = {
                'CRITICAL': '🔴',
                'WARNING': '⚠️',
                'INFO': 'ℹ️'
            }.get(issue['severity'], '•')

            print(f"{severity_icon} [{issue['severity']}] {issue['issue']}")
            print(f"   Category: {issue['category']}")
            print(f"   Details: {issue['details']}")
            print(f"   Recommendation: {issue['recommendation']}")
            print()

    def export_report(self, output_path):
        """Export diagnostic report to CSV"""
        if not self.issues:
            print("No issues to export")
            return

        df = pd.DataFrame(self.issues)
        df.to_csv(output_path, index=False)
        print(f"Diagnostic report exported to: {output_path}")


def run_diagnostics(csv_data, pdf_data):
    """
    Main entry point for diagnostic analysis

    Args:
        csv_data: DataFrame with time-series sensor data
        pdf_data: DataFrame with PDF snapshot data
    """
    engine = DiagnosticEngine(csv_data, pdf_data)
    issues = engine.analyze()

    # Export report
    from src import config
    output_path = config.PROCESSED_DIR / 'diagnostic_report.csv'
    engine.export_report(output_path)

    return issues
