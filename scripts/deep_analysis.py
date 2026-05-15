#!/usr/bin/env python3
"""
BCScanTool v2.0 - Deep Vehicle Analysis Pipeline
Comprehensive ML-powered diagnostic analysis with per-vehicle deep insights
"""
import pandas as pd
import numpy as np
from pathlib import Path
import re
from datetime import datetime
from collections import defaultdict
import json
import joblib
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import warnings
warnings.filterwarnings('ignore')

class VehicleDiagnosticAnalyzer:
    """Deep diagnostic analysis for individual vehicles"""

    def __init__(self, vehicle_name, vehicle_type):
        self.vehicle_name = vehicle_name
        self.vehicle_type = vehicle_type  # 'toyota' or 'volvo'
        self.sessions = []
        self.master_df = None
        self.labeled_data = defaultdict(list)
        self.unlabeled_data = []
        self.anomaly_detector = None
        self.scaler = StandardScaler()

    def load_csv_data(self, csv_files):
        """Load all CSV files for this vehicle"""
        print(f"\n{'='*70}")
        print(f"  Loading {self.vehicle_name} Data")
        print(f"{'='*70}")

        for csv_file in csv_files:
            try:
                df = pd.read_csv(csv_file, low_memory=False)

                # Extract metadata from filename
                filename = Path(csv_file).stem
                date_match = re.search(r'(\d{8})', filename)
                time_match = re.search(r'(\d{6})', filename)

                session_info = {
                    'filename': filename,
                    'path': csv_file,
                    'date': date_match.group(1) if date_match else 'unknown',
                    'time': time_match.group(1) if time_match else 'unknown',
                    'rows': len(df),
                    'columns': len(df.columns)
                }

                # Determine label from filename
                label = self._extract_label(filename)
                session_info['label'] = label

                # Convert to numeric where possible
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Add session metadata to dataframe
                df['session_id'] = filename
                df['session_label'] = label
                df['timestamp_seq'] = range(len(df))

                session_info['data'] = df
                self.sessions.append(session_info)

                # Store in labeled/unlabeled buckets
                if label != 'unlabeled':
                    self.labeled_data[label].append(df)
                else:
                    self.unlabeled_data.append(df)

                print(f"  ✓ {filename[:50]}... [{len(df)} rows, label: {label}]")

            except Exception as e:
                print(f"  ✗ {Path(csv_file).name}: {str(e)[:50]}")

        # Combine all data
        all_dfs = [s['data'] for s in self.sessions]
        if all_dfs:
            self.master_df = pd.concat(all_dfs, ignore_index=True)
            print(f"\n✓ Total: {len(self.master_df):,} rows from {len(self.sessions)} sessions")
            print(f"  Labeled sessions: {len([s for s in self.sessions if s['label'] != 'unlabeled'])}")
            print(f"  Unlabeled sessions: {len([s for s in self.sessions if s['label'] == 'unlabeled'])}")

    def _extract_label(self, filename):
        """Extract condition label from filename"""
        filename_lower = filename.lower()

        if 'good' in filename_lower:
            return 'good'
        elif 'brake' in filename_lower:
            return 'brake_issue'
        elif 'alternation' in filename_lower or 'alternator' in filename_lower:
            return 'alternator_issue'
        elif ' ac' in filename_lower or '_ac' in filename_lower:
            return 'ac_related'
        elif 'startup' in filename_lower:
            return 'startup'
        else:
            return 'unlabeled'

    def perform_statistical_analysis(self):
        """Deep statistical analysis of all parameters"""
        print(f"\n{'='*70}")
        print(f"  Statistical Analysis: {self.vehicle_name}")
        print(f"{'='*70}")

        if self.master_df is None or len(self.master_df) == 0:
            print("  ✗ No data available")
            return None

        # Get numeric columns only
        numeric_cols = self.master_df.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols if col not in ['session_id', 'timestamp_seq']]

        stats_summary = {}

        for col in numeric_cols:
            data = self.master_df[col].dropna()
            if len(data) > 0:
                stats_summary[col] = {
                    'mean': float(data.mean()),
                    'std': float(data.std()),
                    'min': float(data.min()),
                    'max': float(data.max()),
                    'median': float(data.median()),
                    'q25': float(data.quantile(0.25)),
                    'q75': float(data.quantile(0.75)),
                    'missing_pct': float((self.master_df[col].isna().sum() / len(self.master_df)) * 100)
                }

        # Show top varying parameters
        variations = {k: v['std'] / (v['mean'] + 1e-6) for k, v in stats_summary.items()
                     if v['mean'] != 0}
        top_varying = sorted(variations.items(), key=lambda x: abs(x[1]), reverse=True)[:10]

        print(f"\nTop 10 Most Variable Parameters:")
        for param, coeff_var in top_varying:
            print(f"  • {param[:50]}: CV={coeff_var:.3f}")

        return stats_summary

    def train_anomaly_detector(self):
        """Train unsupervised anomaly detection model"""
        print(f"\n{'='*70}")
        print(f"  Training Anomaly Detector: {self.vehicle_name}")
        print(f"{'='*70}")

        if self.master_df is None:
            print("  ✗ No data available")
            return None

        # Use only labeled 'good' data to train anomaly detector
        good_data = []
        for label, dfs in self.labeled_data.items():
            if label == 'good':
                good_data.extend(dfs)

        if not good_data:
            print("  ⚠️  No 'good' labeled data - using all data")
            training_df = self.master_df
        else:
            training_df = pd.concat(good_data, ignore_index=True)
            print(f"  ✓ Using {len(training_df):,} 'good' samples for training")

        # Select numeric features
        numeric_cols = training_df.select_dtypes(include=[np.number]).columns
        feature_cols = [col for col in numeric_cols
                       if col not in ['session_id', 'timestamp_seq', 'session_label']]

        X = training_df[feature_cols].fillna(0)

        # Remove zero-variance features
        variances = X.var()
        X = X.loc[:, variances > 1e-6]

        print(f"  ✓ Using {len(X.columns)} features")

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        self.anomaly_detector = IsolationForest(
            n_estimators=200,
            contamination=0.1,
            random_state=42,
            n_jobs=-1
        )
        self.anomaly_detector.fit(X_scaled)

        # Store feature columns for later use
        self.trained_feature_cols = list(X.columns)

        print(f"  ✓ Anomaly detector trained on {len(X):,} samples")

        return {
            'model': self.anomaly_detector,
            'scaler': self.scaler,
            'feature_columns': list(X.columns)
        }

    def detect_anomalies_in_session(self, session_info):
        """Detect anomalies in a specific session"""
        if self.anomaly_detector is None:
            return None

        df = session_info['data']

        # Get the feature columns used during training
        if hasattr(self, 'trained_feature_cols'):
            feature_cols = self.trained_feature_cols
        else:
            # Fallback to numeric columns
            feature_cols = df.select_dtypes(include=[np.number]).columns

        # Check feature overlap
        available_features = [col for col in feature_cols if col in df.columns]
        feature_overlap_pct = (len(available_features) / len(feature_cols)) * 100 if len(feature_cols) > 0 else 0

        # Skip if less than 50% feature overlap
        if feature_overlap_pct < 50:
            return {
                'session': session_info['filename'],
                'label': session_info['label'],
                'skipped': True,
                'reason': f'Low feature overlap ({feature_overlap_pct:.1f}%)',
                'feature_overlap_pct': feature_overlap_pct
            }

        # Align features with training set
        X = pd.DataFrame()
        for col in feature_cols:
            if col in df.columns:
                X[col] = df[col]
            else:
                X[col] = 0  # Missing features filled with 0

        X = X.fillna(0)

        # Skip if no data rows
        if len(X) == 0:
            return {
                'session': session_info['filename'],
                'label': session_info['label'],
                'skipped': True,
                'reason': 'No data rows after alignment'
            }

        # Transform and predict
        try:
            X_scaled = self.scaler.transform(X)
            predictions = self.anomaly_detector.predict(X_scaled)
            anomaly_scores = self.anomaly_detector.score_samples(X_scaled)

            anomaly_count = (predictions == -1).sum()
            anomaly_pct = (anomaly_count / len(predictions)) * 100

            return {
                'session': session_info['filename'],
                'label': session_info['label'],
                'total_samples': len(predictions),
                'anomaly_count': int(anomaly_count),
                'anomaly_pct': float(anomaly_pct),
                'avg_anomaly_score': float(anomaly_scores.mean()),
                'feature_overlap_pct': feature_overlap_pct,
                'predictions': predictions,
                'scores': anomaly_scores
            }
        except Exception as e:
            return {
                'session': session_info['filename'],
                'label': session_info['label'],
                'error': str(e)[:200]
            }

    def analyze_labeled_vs_unlabeled(self):
        """Compare labeled issues vs unlabeled data"""
        print(f"\n{'='*70}")
        print(f"  Labeled vs Unlabeled Analysis: {self.vehicle_name}")
        print(f"{'='*70}")

        results = {}

        # Analyze each labeled condition
        for label, dfs in self.labeled_data.items():
            if label == 'good':
                continue

            combined = pd.concat(dfs, ignore_index=True)
            print(f"\n{label.upper().replace('_', ' ')}:")
            print(f"  Sessions: {len(dfs)}")
            print(f"  Samples: {len(combined):,}")

            # Find key differentiating parameters
            # TODO: Add feature importance analysis

            results[label] = {
                'session_count': len(dfs),
                'sample_count': len(combined)
            }

        return results

    def generate_session_summary(self):
        """Generate summary of all sessions"""
        summary = {
            'vehicle': self.vehicle_name,
            'vehicle_type': self.vehicle_type,
            'total_sessions': len(self.sessions),
            'total_samples': len(self.master_df) if self.master_df is not None else 0,
            'sessions': []
        }

        for session in self.sessions:
            summary['sessions'].append({
                'filename': session['filename'],
                'date': session['date'],
                'label': session['label'],
                'rows': session['rows'],
                'columns': session['columns']
            })

        return summary


class MultiVehicleMLPipeline:
    """ML pipeline for training models across multiple vehicles"""

    def __init__(self):
        self.models = {}
        self.toyota_analyzer = None
        self.volvo_analyzer = None
        self.gmc_analyzer = None

    def load_and_analyze_all_data(self, raw_data_path):
        """Load and analyze all vehicle data"""
        print("="*70)
        print("  BCScanTool v2.0 - Deep Vehicle Analysis Pipeline")
        print("="*70)

        raw_path = Path(raw_data_path)

        # Find all CSV files
        all_csvs = list(raw_path.rglob("*.csv"))

        # Separate by vehicle
        toyota_csvs = [str(f) for f in all_csvs if 'TOYOTA' in f.name.upper()]
        volvo_csvs = [str(f) for f in all_csvs if 'VOLVO' in f.name.upper()]
        gmc_csvs = [str(f) for f in all_csvs if 'GM_' in f.name.upper() or 'GMC' in f.name.upper()]

        print(f"\nFound {len(all_csvs)} total CSV files:")
        print(f"  Toyota: {len(toyota_csvs)}")
        print(f"  Volvo: {len(volvo_csvs)}")
        print(f"  GMC: {len(gmc_csvs)}")

        # Create analyzers
        self.toyota_analyzer = VehicleDiagnosticAnalyzer("2011 Toyota Tacoma SR5 4.0L V6", "toyota")
        self.volvo_analyzer = VehicleDiagnosticAnalyzer("Volvo", "volvo")
        self.gmc_analyzer = VehicleDiagnosticAnalyzer("GMC Yukon", "gmc")

        # Load data
        if toyota_csvs:
            self.toyota_analyzer.load_csv_data(toyota_csvs)
            self.toyota_analyzer.perform_statistical_analysis()
            self.toyota_analyzer.train_anomaly_detector()
            self.toyota_analyzer.analyze_labeled_vs_unlabeled()

        if volvo_csvs:
            self.volvo_analyzer.load_csv_data(volvo_csvs)
            self.volvo_analyzer.perform_statistical_analysis()
            self.volvo_analyzer.train_anomaly_detector()
            self.volvo_analyzer.analyze_labeled_vs_unlabeled()

        if gmc_csvs:
            self.gmc_analyzer.load_csv_data(gmc_csvs)
            self.gmc_analyzer.perform_statistical_analysis()
            self.gmc_analyzer.train_anomaly_detector()
            self.gmc_analyzer.analyze_labeled_vs_unlabeled()

    def scan_all_sessions_for_anomalies(self):
        """Run anomaly detection on all sessions"""
        print(f"\n{'='*70}")
        print(f"  Anomaly Detection - All Sessions")
        print(f"{'='*70}")

        results = {'toyota': [], 'volvo': [], 'gmc': []}

        # Toyota
        if self.toyota_analyzer and self.toyota_analyzer.anomaly_detector:
            print(f"\nTOYOTA TACOMA:")
            for session in self.toyota_analyzer.sessions:
                anomaly_result = self.toyota_analyzer.detect_anomalies_in_session(session)
                if anomaly_result:
                    results['toyota'].append(anomaly_result)

                    if 'error' in anomaly_result:
                        print(f"  ✗ {session['filename'][:50]}")
                        print(f"     Error: {anomaly_result['error'][:60]}")
                    elif 'skipped' in anomaly_result:
                        print(f"  ⊘ {session['filename'][:50]}")
                        print(f"     Skipped: {anomaly_result['reason']}")
                    else:
                        status = "✓" if anomaly_result['anomaly_pct'] < 5 else "⚠️" if anomaly_result['anomaly_pct'] < 15 else "🔴"
                        print(f"  {status} {session['filename'][:50]}")
                        print(f"     Label: {session['label']}, Anomalies: {anomaly_result['anomaly_pct']:.1f}%, Features: {anomaly_result['feature_overlap_pct']:.0f}%")

        # Volvo
        if self.volvo_analyzer and self.volvo_analyzer.anomaly_detector:
            print(f"\nVOLVO:")
            for session in self.volvo_analyzer.sessions:
                anomaly_result = self.volvo_analyzer.detect_anomalies_in_session(session)
                if anomaly_result:
                    results['volvo'].append(anomaly_result)

                    if 'error' in anomaly_result:
                        print(f"  ✗ {session['filename'][:50]}")
                        print(f"     Error: {anomaly_result['error'][:60]}")
                    elif 'skipped' in anomaly_result:
                        print(f"  ⊘ {session['filename'][:50]}")
                        print(f"     Skipped: {anomaly_result['reason']}")
                    else:
                        status = "✓" if anomaly_result['anomaly_pct'] < 5 else "⚠️" if anomaly_result['anomaly_pct'] < 15 else "🔴"
                        print(f"  {status} {session['filename'][:50]}")
                        print(f"     Label: {session['label']}, Anomalies: {anomaly_result['anomaly_pct']:.1f}%, Features: {anomaly_result['feature_overlap_pct']:.0f}%")

        # GMC
        if self.gmc_analyzer and self.gmc_analyzer.anomaly_detector:
            print(f"\nGMC YUKON:")
            for session in self.gmc_analyzer.sessions:
                anomaly_result = self.gmc_analyzer.detect_anomalies_in_session(session)
                if anomaly_result:
                    results['gmc'].append(anomaly_result)

                    if 'error' in anomaly_result:
                        print(f"  ✗ {session['filename'][:50]}")
                        print(f"     Error: {anomaly_result['error'][:60]}")
                    elif 'skipped' in anomaly_result:
                        print(f"  ⊘ {session['filename'][:50]}")
                        print(f"     Skipped: {anomaly_result['reason']}")
                    else:
                        status = "✓" if anomaly_result['anomaly_pct'] < 5 else "⚠️" if anomaly_result['anomaly_pct'] < 15 else "🔴"
                        print(f"  {status} {session['filename'][:50]}")
                        print(f"     Label: {session['label']}, Anomalies: {anomaly_result['anomaly_pct']:.1f}%, Features: {anomaly_result['feature_overlap_pct']:.0f}%")

        return results

    def save_results(self, output_dir):
        """Save all analysis results"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"  Saving Results")
        print(f"{'='*70}")

        # Save Toyota data
        if self.toyota_analyzer:
            toyota_summary = self.toyota_analyzer.generate_session_summary()
            toyota_file = output_path / "toyota_analysis_summary.json"
            with open(toyota_file, 'w') as f:
                json.dump(toyota_summary, f, indent=2)
            print(f"  ✓ {toyota_file}")

            # Save Toyota model
            if self.toyota_analyzer.anomaly_detector:
                model_file = output_path / "toyota_anomaly_model.joblib"
                joblib.dump({
                    'model': self.toyota_analyzer.anomaly_detector,
                    'scaler': self.toyota_analyzer.scaler,
                    'feature_columns': list(self.toyota_analyzer.anomaly_detector.feature_names_in_) if hasattr(self.toyota_analyzer.anomaly_detector, 'feature_names_in_') else []
                }, model_file)
                print(f"  ✓ {model_file}")

        # Save Volvo data
        if self.volvo_analyzer:
            volvo_summary = self.volvo_analyzer.generate_session_summary()
            volvo_file = output_path / "volvo_analysis_summary.json"
            with open(volvo_file, 'w') as f:
                json.dump(volvo_summary, f, indent=2)
            print(f"  ✓ {volvo_file}")

            # Save Volvo model
            if self.volvo_analyzer.anomaly_detector:
                model_file = output_path / "volvo_anomaly_model.joblib"
                joblib.dump({
                    'model': self.volvo_analyzer.anomaly_detector,
                    'scaler': self.volvo_analyzer.scaler,
                    'feature_columns': list(self.volvo_analyzer.anomaly_detector.feature_names_in_) if hasattr(self.volvo_analyzer.anomaly_detector, 'feature_names_in_') else []
                }, model_file)
                print(f"  ✓ {model_file}")

        # Save GMC data
        if self.gmc_analyzer:
            gmc_summary = self.gmc_analyzer.generate_session_summary()
            gmc_file = output_path / "gmc_analysis_summary.json"
            with open(gmc_file, 'w') as f:
                json.dump(gmc_summary, f, indent=2)
            print(f"  ✓ {gmc_file}")

            # Save GMC model
            if self.gmc_analyzer.anomaly_detector:
                model_file = output_path / "gmc_anomaly_model.joblib"
                joblib.dump({
                    'model': self.gmc_analyzer.anomaly_detector,
                    'scaler': self.gmc_analyzer.scaler,
                    'feature_columns': list(self.gmc_analyzer.anomaly_detector.feature_names_in_) if hasattr(self.gmc_analyzer.anomaly_detector, 'feature_names_in_') else []
                }, model_file)
                print(f"  ✓ {model_file}")


def main():
    """Main execution function"""
    project_root = Path(__file__).resolve().parents[1]
    raw_data_path = project_root / "data" / "raw"
    output_path = project_root / "data" / "processed"

    # Create pipeline
    pipeline = MultiVehicleMLPipeline()

    # Load and analyze all data
    pipeline.load_and_analyze_all_data(raw_data_path)

    # Run anomaly detection
    anomaly_results = pipeline.scan_all_sessions_for_anomalies()

    # Save results
    pipeline.save_results(output_path)

    print(f"\n{'='*70}")
    print(f"  Analysis Complete!")
    print(f"{'='*70}")
    print(f"\nNext steps:")
    print(f"  1. Review anomaly detection results")
    print(f"  2. Induce test errors to validate model")
    print(f"  3. Refine labeling based on findings")
    print(f"  4. Generate detailed reports")


if __name__ == "__main__":
    main()
