import pandas as pd
import numpy as np
import joblib
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

class DataIngestor:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def load_data(self):
        """Loads all CSVs and assigns labels based on filename."""
        all_csvs = list(self.data_dir.rglob("*.csv"))
        all_dfs = []
        
        for csv_file in all_csvs:
            try:
                df = pd.read_csv(csv_file, low_memory=False)
                filename = csv_file.stem.lower()
                
                # Assign labels dynamically based on filename keywords
                if 'good' in filename or 'baseline' in filename:
                    df['condition'] = 'good'
                elif 'brake' in filename or 'issue' in filename:
                    df['condition'] = 'issue'
                else:
                    df['condition'] = 'unknown'
                    
                all_dfs.append(df)
            except Exception as e:
                print(f"Failed to load {csv_file.name}: {e}")
                
        if not all_dfs:
            return pd.DataFrame()
            
        master_df = pd.concat(all_dfs, ignore_index=True)
        
        # Convert everything except target column to numeric
        for col in master_df.columns:
            if col != 'condition':
                master_df[col] = pd.to_numeric(master_df[col], errors='coerce')
                
        return master_df

class SupervisedModelPipeline:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.label_encoder = LabelEncoder()
        
        # We use a pipeline to prevent data leakage during imputation
        self.pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('classifier', RandomForestClassifier(n_estimators=100, class_weight='balanced', random_state=42, n_jobs=-1))
        ])
        
    def train(self, df: pd.DataFrame):
        labeled_df = df[df['condition'] != 'unknown'].copy()
        
        # Drop columns that are 100% NaN to prevent imputation warnings
        labeled_df = labeled_df.dropna(axis=1, how='all')
        
        if len(labeled_df) < 10:
            print("Not enough labeled data to train supervised model.")
            return False
            
        y = self.label_encoder.fit_transform(labeled_df['condition'])
        X = labeled_df.select_dtypes(include=np.number)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
        
        print("Training Supervised RandomForest Pipeline...")
        self.pipeline.fit(X_train, y_train)
        
        y_pred = self.pipeline.predict(X_test)
        print("\\nModel Performance:")
        print(classification_report(y_test, y_pred, target_names=self.label_encoder.classes_))
        
        # Save payload
        payload = {
            'pipeline': self.pipeline,
            'label_encoder': self.label_encoder,
            'features': X.columns.tolist()
        }
        joblib.dump(payload, self.model_dir / "supervised_pipeline.joblib")
        return True

class AnomalyDetectorPipeline:
    def __init__(self, model_dir: Path):
        self.model_dir = model_dir
        self.model_dir.mkdir(parents=True, exist_ok=True)
        
        self.pipeline = Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler()),
            ('detector', IsolationForest(contamination=0.05, random_state=42, n_jobs=-1))
        ])
        
    def train(self, df: pd.DataFrame):
        # We can train unsupervised model on ALL data (mostly healthy)
        # Filter for known 'good' data to establish a baseline
        healthy_df = df[df['condition'] == 'good'].copy()
        if healthy_df.empty:
            healthy_df = df # Fallback to all data if no explicit 'good' labels
            
        # Drop columns that are 100% NaN
        healthy_df = healthy_df.dropna(axis=1, how='all')
            
        X = healthy_df.select_dtypes(include=np.number)
        
        if len(X) < 50:
            print("Not enough data to establish healthy baseline for anomalies.")
            return False
            
        print("Training Unsupervised IsolationForest Pipeline...")
        self.pipeline.fit(X)
        
        payload = {
            'pipeline': self.pipeline,
            'features': X.columns.tolist()
        }
        joblib.dump(payload, self.model_dir / "anomaly_pipeline.joblib")
        return True
