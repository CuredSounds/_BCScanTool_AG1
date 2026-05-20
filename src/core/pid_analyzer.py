"""
Critical PID Parameter Analysis Module
Extracts and analyzes essential OBD2 PIDs for comprehensive diagnostics
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Tuple

from src import config

logger = logging.getLogger("BCScanTool.PIDAnalyzer")


class PIDAnalyzer:
    """
    Analyzes critical OBD2 PIDs for comprehensive vehicle diagnostics
    """

    # Standard OBD2 PID definitions
    CRITICAL_PIDS = {
        # Engine Performance
        'engine_speed': ['Engine Speed', 'RPM', 'Av Engine Speed', 'Eng Speed'],
        'coolant_temp': ['Coolant Temperature', 'Engine Coolant Temperature', 'ECT', 'Coolant Temp'],
        'calculated_load': ['Calculate Load', 'Calculated Load', 'Engine Load', 'Load'],

        # Fuel System
        'stft_bank1': ['Short Term Fuel Trim', 'STFT', 'Short Fuel Trim Bank 1', 'STFT1', 'STFT 1'],
        'ltft_bank1': ['Long Term Fuel Trim', 'LTFT', 'Long Fuel Trim Bank 1', 'LTFT1', 'LTFT 1'],
        'stft_bank2': ['Short Fuel Trim Bank 2', 'STFT2', 'STFT 2'],
        'ltft_bank2': ['Long Fuel Trim Bank 2', 'LTFT2', 'LTFT 2'],
        'fuel_pressure': ['Fuel Pressure', 'Fuel Rail Pressure', 'FRP'],

        # Air Intake
        'maf': ['MAF', 'Mass Air Flow', 'Air Flow', 'Mass Airflow', 'Intake Air Flow'],
        'map': ['MAP', 'Intake Manifold Pressure', 'Manifold Absolute Pressure'],
        'iat': ['Intake Air Temperature', 'IAT', 'Intake Air Temp'],

        # Throttle & Load
        'throttle_position': ['Throttle Position', 'TP', 'TPS', 'Throttle Pos'],
        'accelerator_position': ['Accelerator Position', 'APP', 'Accel Pos'],

        # Oxygen Sensors
        'o2_bank1_sensor1': ['O2 Sensor', 'Oxygen Sensor', 'O2 B1S1', 'AF Lambda (Bank1 Sensor1)', 'O2S11'],
        'o2_bank1_sensor2': ['O2 B1S2', 'AF Lambda (Bank1 Sensor2)', 'O2S12'],
        'o2_bank2_sensor1': ['O2 B2S1', 'AF Lambda (Bank2 Sensor1)', 'O2S21'],
        'o2_bank2_sensor2': ['O2 B2S2', 'AF Lambda (Bank2 Sensor2)', 'O2S22'],

        # Ignition
        'spark_advance': ['Spark', 'Spark Advance', 'Ignition Timing', 'Timing Advance'],

        # Vehicle
        'vehicle_speed': ['Vehicle Speed', 'Speed', 'VSS'],

        # Misfires
        'misfire_count': ['Misfire', 'All Cylinders Misfire Count', 'Misfire Count', 'Misfires'],

        # Emissions
        'catalyst_temp_b1': ['Catalyst Temperature', 'TWC Temperature Bank 1', 'Cat Temp 1'],
        'catalyst_temp_b2': ['TWC Temperature Bank 2', 'Cat Temp 2'],
    }

    def __init__(self, dataframe):
        """
        Initialize PID analyzer with vehicle data

        Args:
            dataframe: Pandas DataFrame with vehicle sensor data
        """
        self.df = dataframe
        self.mapped_pids = {}
        self.available_pids = []
        self._map_available_pids()

    def _map_available_pids(self):
        """Map available columns to standard PID names using specificity scoring.
        Exact matches win over substring matches. Longer substring matches win over shorter ones.
        This prevents ambiguous mapping (e.g. 'Short Fuel Trim' matching both bank1 and bank2)."""
        logger.info("Mapping available PIDs...")

        # Find all possible matches for all columns
        col_matches = {}  # col -> list of (pid_name, score)
        
        for col in self.df.columns:
            col_lower = str(col).lower()
            col_matches[col] = []
            
            for pid_name, possible_names in self.CRITICAL_PIDS.items():
                best_pid_score = -1
                for possible_name in possible_names:
                    pn_lower = possible_name.lower()

                    # Exact match (case-insensitive) gets highest score
                    if col_lower == pn_lower:
                        score = 10000
                    # Full column name starts with the PID name
                    elif col_lower.startswith(pn_lower):
                        score = len(pn_lower) * 2
                    # Substring match — score by length of match (longer = more specific)
                    elif pn_lower in col_lower:
                        score = len(pn_lower)
                    else:
                        continue
                    
                    if score > best_pid_score:
                        best_pid_score = score
                
                if best_pid_score > -1:
                    col_matches[col].append((pid_name, best_pid_score))

        # Sort columns by their best match score descending to process most certain ones first
        # But we need to ensure each PID gets the BEST column for it.
        
        pid_to_best_col = {} # pid_name -> (col, score)
        
        for col, matches in col_matches.items():
            for pid_name, score in matches:
                if pid_name not in pid_to_best_col or score > pid_to_best_col[pid_name][1]:
                    pid_to_best_col[pid_name] = (col, score)
        
        # Now populate mapped_pids
        for pid_name, (col, score) in pid_to_best_col.items():
            self.mapped_pids[pid_name] = col
            self.available_pids.append(pid_name)
            logger.debug(f"  ✓ {pid_name}: {col} (score={score})")

        # Report missing critical PIDs
        missing = set(self.CRITICAL_PIDS.keys()) - set(self.available_pids)
        if missing:
            logger.info(f"Missing {len(missing)} PIDs: {sorted(missing)}")

    def get_pid_data(self, pid_name: str) -> pd.Series:
        """
        Get data for a specific PID

        Args:
            pid_name: Standard PID name

        Returns:
            Pandas Series with PID data
        """
        if pid_name not in self.mapped_pids:
            return pd.Series(dtype=float)

        col = self.mapped_pids[pid_name]
        return pd.to_numeric(self.df[col], errors='coerce')

    def get_all_pid_data(self, pid_name: str) -> List[pd.Series]:
        """
        Get data for all columns matching a PID

        Args:
            pid_name: Standard PID name

        Returns:
            List of Pandas Series
        """
        if pid_name not in self.CRITICAL_PIDS:
            return []

        possible_names = self.CRITICAL_PIDS[pid_name]
        data_list = []

        for col in self.df.columns:
            match = False
            for possible_name in possible_names:
                if possible_name.lower() in str(col).lower():
                    match = True
                    break
            if match:
                data_list.append(pd.to_numeric(self.df[col], errors='coerce'))

        return data_list

    def analyze_fuel_system(self) -> Dict:
        """Analyze fuel system health"""
        analysis = {
            'status': 'UNKNOWN',
            'issues': [],
            'metrics': {}
        }

        # Short Term Fuel Trim
        stft = self.get_pid_data('stft_bank1')
        if not stft.empty:
            stft_mean = stft.mean()
            analysis['metrics']['stft_mean'] = stft_mean

            if abs(stft_mean) > 15:
                analysis['issues'].append({
                    'severity': 'WARNING',
                    'issue': 'High STFT',
                    'details': f'STFT: {stft_mean:.1f}% (normal: -10 to +10%)',
                    'cause': 'Rich condition' if stft_mean < -15 else 'Lean condition'
                })

        # Long Term Fuel Trim
        ltft = self.get_pid_data('ltft_bank1')
        if not ltft.empty:
            ltft_mean = ltft.mean()
            analysis['metrics']['ltft_mean'] = ltft_mean

            if abs(ltft_mean) > 15:
                analysis['issues'].append({
                    'severity': 'CRITICAL',
                    'issue': 'High LTFT',
                    'details': f'LTFT: {ltft_mean:.1f}% (normal: -10 to +10%)',
                    'cause': 'Persistent rich condition' if ltft_mean < -15 else 'Persistent lean condition'
                })

        # Determine overall status
        if len(analysis['issues']) == 0:
            analysis['status'] = 'HEALTHY'
        elif any(i['severity'] == 'CRITICAL' for i in analysis['issues']):
            analysis['status'] = 'CRITICAL'
        else:
            analysis['status'] = 'WARNING'

        return analysis

    def analyze_air_intake(self) -> Dict:
        """Analyze air intake system"""
        analysis = {
            'status': 'UNKNOWN',
            'issues': [],
            'metrics': {}
        }

        # MAF Analysis
        maf = self.get_pid_data('maf')
        if not maf.empty:
            maf_mean = maf[maf > 0].mean()  # Filter out zeros
            analysis['metrics']['maf_mean'] = maf_mean

            # Typical idle MAF: 2-4 g/s for most vehicles
            # At cruise: 5-15 g/s
            if maf_mean < 1 and len(maf[maf > 0]) > 10:
                analysis['issues'].append({
                    'severity': 'WARNING',
                    'issue': 'Low MAF Reading',
                    'details': f'Average MAF: {maf_mean:.2f} g/s',
                    'cause': 'Dirty MAF sensor or vacuum leak'
                })

        # MAP Analysis
        map_data = self.get_pid_data('map')
        if not map_data.empty:
            map_mean = map_data.mean()
            analysis['metrics']['map_mean'] = map_mean

            # Typical idle MAP: 10-14 psi (depending on altitude)
            # Wide open throttle: close to atmospheric (14.7 psi at sea level)

        # IAT Analysis
        iat = self.get_pid_data('iat')
        if not iat.empty:
            iat_mean = iat.mean()
            analysis['metrics']['iat_mean'] = iat_mean

            # Use config-driven thresholds
            iat_threshold = 60 if config.TEMP_UNIT == "celsius" else 140
            unit = "°C" if config.TEMP_UNIT == "celsius" else "°F"

            if iat_mean > iat_threshold:
                analysis['issues'].append({
                    'severity': 'WARNING',
                    'issue': 'High Intake Air Temperature',
                    'details': f'IAT: {iat_mean:.0f}{unit} (should be near ambient)',
                    'cause': 'Heat soak or cooling issue'
                })

        # Determine overall status
        if len(analysis['issues']) == 0:
            analysis['status'] = 'HEALTHY'
        else:
            analysis['status'] = 'WARNING'

        return analysis

    def analyze_oxygen_sensors(self) -> Dict:
        """Analyze oxygen sensor performance"""
        analysis = {
            'status': 'UNKNOWN',
            'issues': [],
            'metrics': {},
            'sensors': {}
        }

        sensors = ['o2_bank1_sensor1', 'o2_bank1_sensor2', 'o2_bank2_sensor1', 'o2_bank2_sensor2']

        for sensor in sensors:
            o2_data = self.get_pid_data(sensor)
            if not o2_data.empty:
                o2_mean = o2_data.mean()
                o2_std = o2_data.std()

                analysis['sensors'][sensor] = {
                    'mean': o2_mean,
                    'std': o2_std,
                    'switching': o2_std > 0.1  # Active sensors switch between rich/lean
                }

                # Lambda sensors should be around 1.0 (stoichiometric)
                # Voltage sensors switch between 0.1-0.9V

                if o2_std < 0.05:  # Sensor not switching
                    analysis['issues'].append({
                        'severity': 'WARNING',
                        'issue': f'{sensor.upper()} Not Switching',
                        'details': f'O2 sensor stuck at {o2_mean:.2f}',
                        'cause': 'Failed O2 sensor or rich/lean lock'
                    })

        if len(analysis['issues']) == 0:
            analysis['status'] = 'HEALTHY'
        else:
            analysis['status'] = 'WARNING'

        return analysis

    def analyze_ignition_timing(self) -> Dict:
        """Analyze ignition timing"""
        analysis = {
            'status': 'UNKNOWN',
            'issues': [],
            'metrics': {}
        }

        spark = self.get_pid_data('spark_advance')
        if not spark.empty:
            spark_mean = spark.mean()
            spark_std = spark.std()

            analysis['metrics']['spark_advance_mean'] = spark_mean
            analysis['metrics']['spark_advance_std'] = spark_std

            # Typical idle timing: 10-20° BTDC
            # Cruise: 25-40° BTDC

            if spark_mean < 5:
                analysis['issues'].append({
                    'severity': 'WARNING',
                    'issue': 'Retarded Ignition Timing',
                    'details': f'Spark advance: {spark_mean:.1f}° (low)',
                    'cause': 'Knock sensor detection or ECU timing pullback'
                })

        if len(analysis['issues']) == 0:
            analysis['status'] = 'HEALTHY'
        else:
            analysis['status'] = 'WARNING'

        return analysis

    def comprehensive_analysis(self) -> Dict:
        """Run comprehensive PID analysis"""
        print("\n" + "="*70)
        print("COMPREHENSIVE PID ANALYSIS")
        print("="*70)

        results = {
            'fuel_system': self.analyze_fuel_system(),
            'air_intake': self.analyze_air_intake(),
            'oxygen_sensors': self.analyze_oxygen_sensors(),
            'ignition': self.analyze_ignition_timing(),
        }

        # Display results
        for system, analysis in results.items():
            status_icon = {
                'HEALTHY': '✅',
                'WARNING': '⚠️',
                'CRITICAL': '🔴',
                'UNKNOWN': '❓'
            }.get(analysis['status'], '•')

            print(f"\n{status_icon} {system.upper().replace('_', ' ')}: {analysis['status']}")

            if analysis['issues']:
                for issue in analysis['issues']:
                    print(f"  [{issue['severity']}] {issue['issue']}")
                    print(f"    {issue['details']}")
                    print(f"    Likely cause: {issue['cause']}")

        return results

    def get_data_quality_report(self) -> Dict:
        """Generate data quality report"""
        report = {
            'total_pids_defined': len(self.CRITICAL_PIDS),
            'pids_available': len(self.available_pids),
            'pids_missing': len(set(self.CRITICAL_PIDS.keys()) - set(self.available_pids)),
            'coverage_percentage': (len(self.available_pids) / len(self.CRITICAL_PIDS)) * 100,
            'available_pids': self.available_pids,
            'missing_pids': list(set(self.CRITICAL_PIDS.keys()) - set(self.available_pids))
        }

        print("\n" + "="*70)
        print("DATA QUALITY REPORT")
        print("="*70)
        print(f"PID Coverage: {report['coverage_percentage']:.1f}%")
        print(f"Available: {report['pids_available']}/{report['total_pids_defined']}")
        print(f"Missing: {report['pids_missing']}")

        return report


def analyze_pids(dataframe):
    """
    Main entry point for PID analysis

    Args:
        dataframe: Vehicle sensor data
    """
    analyzer = PIDAnalyzer(dataframe)

    # Run comprehensive analysis
    results = analyzer.comprehensive_analysis()

    # Get data quality report
    quality = analyzer.get_data_quality_report()

    return analyzer, results, quality
