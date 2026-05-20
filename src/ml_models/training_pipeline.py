"""
ML Training Pipeline for BCScanTool
Uses manifest-based labeling, cross-validation, and feature importance tracking.
"""

import pandas as pd
import numpy as np
import joblib
import logging
from pathlib import Path
from datetime import datetime
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report

from src import config
from src.core.data_quality import load_labeled_dataset

logger = logging.getLogger("BCScanTool.TrainingPipeline")


class DataIngestor:
    """Loads and labels data using the scan manifest instead of filename guessing."""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def load_data(self) -> pd.DataFrame:
        """Load data using manifest labels. Falls back to filename heuristic if no manifest."""
        # Try manifest-based loading first
        manifest_df = load_labeled_dataset(self.data_dir)
        if manifest_df is not None and not manifest_df.empty:
            logger.info(f"Loaded {len(manifest_df)} rows from manifest-labeled data")
            return manifest_df

        # Fallback: legacy filename-based labeling (with warning)
        logger.warning("No manifest found — falling back to filename-based labeling")
        return self._load_legacy(self.data_dir)

    def _load_legacy(self, data_dir: Path) -> pd.DataFrame:
        """Legacy loader: infers labels from filenames. Use manifest instead."""
        all_csvs = list(data_dir.rglob("*.csv"))
        all_dfs = []
        for csv_file in all_csvs:
            try:
                df = pd.read_csv(csv_file, low_memory=False)
                filename = csv_file.stem.lower()
                if 'good' in filename or 'baseline' in filename:
                    df['condition'] = 'healthy'
                elif 'fault' in filename or 'issue' in filename:
                    df['condition'] = 'fault'
                else:
                    df['condition'] = 'unknown'
                all_dfs.append(df)
            except Exception as e:
                logger.warning(f"Failed to load {csv_file.name}: {e}")
        if not all_dfs:
            return pd.DataFrame()
        master_df = pd.concat(all_dfs, ignore_index=True)
        for col in master_df.columns:
            if col != 'condition':
                master_df[col] = pd.to_numeric(master_df[col], errors='coerce')
        return master_df


class SupervisedModelPipeline:
    """Random Forest classifier with cross-validation and feature importance tracking."""

    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.label_encoder = LabelEncoder()
        self.pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', RandomForestClassifier(
                n_estimators=100, class_weight='balanced',
                random_state=42, n_jobs=-1
            ))
        ])
        self.feature_importances_ = None

    def train(self, df: pd.DataFrame) -> bool:
        # Filter to labeled data only (exclude 'unknown')
        labeled_df = df[~df['condition'].isin(['unknown'])].copy()
        labeled_df = labeled_df.dropna(axis=1, how='all')

        if len(labeled_df) < 10:
            logger.warning("Not enough labeled data to train supervised model.")
            return False

        y = self.label_encoder.fit_transform(labeled_df['condition'])
        X = labeled_df.select_dtypes(include=np.number)
        feature_names = X.columns.tolist()

        # Log class distribution
        unique, counts = np.unique(y, return_counts=True)
        class_dist = {self.label_encoder.inverse_transform([u])[0]: int(c) for u, c in zip(unique, counts)}
        logger.info(f"Class distribution: {class_dist}")

        if len(unique) < 2:
            logger.warning(f"Need at least 2 classes, got {len(unique)}: {class_dist}")
            return False

        # Cross-validation instead of single split
        n_splits = min(5, min(counts))
        if n_splits < 2:
            logger.warning(f"Smallest class has {min(counts)} samples — using train/test split")
            from sklearn.model_selection import train_test_split
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.3, random_state=42, stratify=y)
            self.pipeline.fit(X_train, y_train)
            y_pred = self.pipeline.predict(X_test)
            report = classification_report(y_test, y_pred,
                                           target_names=self.label_encoder.classes_,
                                           output_dict=True)
            logger.info(f"\n{classification_report(y_test, y_pred, target_names=self.label_encoder.classes_)}")
        else:
            logger.info(f"Running {n_splits}-fold stratified cross-validation...")
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            scores = cross_val_score(self.pipeline, X, y, cv=cv, scoring='f1_weighted')
            logger.info(f"CV F1 scores: {scores}")
            logger.info(f"CV F1 mean: {scores.mean():.3f} ± {scores.std():.3f}")

            # Train final model on all data
            self.pipeline.fit(X, y)
            report = {"cv_f1_mean": float(scores.mean()), "cv_f1_std": float(scores.std())}

        # Extract feature importances
        clf = self.pipeline.named_steps['classifier']
        importances = clf.feature_importances_
        feat_imp = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
        self.feature_importances_ = feat_imp

        logger.info("Top 10 features by importance:")
        for name, imp in feat_imp[:10]:
            logger.info(f"  {imp:.4f}  {name}")

        # Save model with versioning
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"supervised_pipeline_{timestamp}"
        payload = {
            'pipeline': self.pipeline,
            'label_encoder': self.label_encoder,
            'features': feature_names,
            'feature_importances': feat_imp[:20],
        }
        joblib.dump(payload, self.model_dir / f"{model_name}.joblib")

        # Also save as "latest" for the API to load
        joblib.dump(payload, self.model_dir / "supervised_pipeline.joblib")

        # Save metadata
        config.save_model_metadata(model_name, {
            "type": "supervised",
            "algorithm": "RandomForestClassifier",
            "n_samples": len(labeled_df),
            "n_features": len(feature_names),
            "classes": class_dist,
            "performance": report,
            "top_features": [(n, float(i)) for n, i in feat_imp[:10]],
        })
        return True


class AnomalyDetectorPipeline:
    """Isolation Forest trained on confirmed healthy data for anomaly detection."""

    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('detector', IsolationForest(contamination=0.05, random_state=42, n_jobs=-1))
        ])

    def train(self, df: pd.DataFrame) -> bool:
        # Prefer explicitly healthy data for baseline
        healthy_df = df[df['condition'] == 'healthy'].copy()
        if healthy_df.empty:
            logger.warning("No 'healthy' labeled data — using all data as baseline (less reliable)")
            healthy_df = df.copy()

        healthy_df = healthy_df.dropna(axis=1, how='all')
        X = healthy_df.select_dtypes(include=np.number)

        if len(X) < 50:
            logger.warning(f"Not enough data for anomaly baseline: {len(X)} rows (need 50+)")
            return False

        feature_names = X.columns.tolist()
        logger.info(f"Training IsolationForest on {len(X)} healthy samples, {len(feature_names)} features")
        self.pipeline.fit(X)

        # Save with versioning
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_name = f"anomaly_pipeline_{timestamp}"
        payload = {
            'pipeline': self.pipeline,
            'features': feature_names,
        }
        joblib.dump(payload, self.model_dir / f"{model_name}.joblib")
        joblib.dump(payload, self.model_dir / "anomaly_pipeline.joblib")

        config.save_model_metadata(model_name, {
            "type": "unsupervised",
            "algorithm": "IsolationForest",
            "contamination": 0.05,
            "n_samples": len(X),
            "n_features": len(feature_names),
            "features": feature_names,
            "baseline_source": "healthy-labeled" if not healthy_df.equals(df) else "all-data-fallback",
        })
        return True
