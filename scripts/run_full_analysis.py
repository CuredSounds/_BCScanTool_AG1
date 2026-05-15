#!/usr/bin/env python3
"""
BCScanTool - Complete Analysis Pipeline
Run this single script to analyze all your diagnostic data.
"""
import pandas as pd
from pathlib import Path
import re
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.preprocessing import LabelEncoder
import numpy as np

print("="*60)
print("  BCScanTool v2.0 - Complete Diagnostic Analysis")
print("="*60)
print("\nStep 1: Loading all diagnostic data...")

project_root = Path(__file__).resolve().parents[1]
raw_data_path = project_root / "data" / "raw"
november_path = project_root / "November scan"

# Find all CSV files (we'll skip .x431 for simplicity)
all_csvs = list(raw_data_path.rglob("*.csv"))
print(f"✓ Found {len(all_csvs)} CSV files in raw data")

# Load and combine all data
print("\nStep 2: Processing files...")
all_dfs = []
for csv_file in all_csvs:
    try:
        df = pd.read_csv(csv_file, low_memory=False)
        
        # Label based on filename
        filename = csv_file.stem.lower()
        df['vehicle'] = 'volvo' if 'volvo' in filename else 'toyota'
        
        if 'good' in filename:
            df['condition'] = 'good'
        elif 'brake' in filename:
            df['condition'] = 'brake_issue'
        else:
            df['condition'] = 'unknown'
            
        all_dfs.append(df)
        print(f"  ✓ {csv_file.name}: {len(df)} rows")
    except Exception as e:
        print(f"  ✗ {csv_file.name}: {e}")

master_df = pd.concat(all_dfs, ignore_index=True)
print(f"\n✓ Combined dataset: {len(master_df):,} total rows")

# Convert to numeric
print("\nStep 3: Converting to numeric data...")
for col in master_df.columns:
    if col not in ['vehicle', 'condition']:
        master_df[col] = pd.to_numeric(master_df[col], errors='coerce')

print("✓ Data types standardized")

# Train model
print("\nStep 4: Training ML model...")
labeled_df = master_df[master_df['condition'] != 'unknown'].copy()
print(f"✓ Using {len(labeled_df)} labeled samples")

if len(labeled_df) > 10:
    label_encoder = LabelEncoder()
    labeled_df['condition_encoded'] = label_encoder.fit_transform(labeled_df['condition'])
    
    features = labeled_df.select_dtypes(include=np.number).drop(columns=['condition_encoded'])
    features = features.fillna(features.median())
    
    X = features
    y = labeled_df['condition_encoded']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1)
    clf.fit(X_train, y_train)
    
    y_pred = clf.predict(X_test)
    
    print("\n" + "="*60)
    print("  Model Performance:")
    print("="*60)
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))
    
    # Save model
    models_path = project_root / "models"
    models_path.mkdir(exist_ok=True)
    
    model_payload = {
        'classifier': clf,
        'label_encoder': label_encoder,
        'feature_columns': features.columns
    }
    
    model_file = models_path / "diagnostic_classifier.joblib"
    joblib.dump(model_payload, model_file)
    print(f"✓ Model saved to: {model_file}")
    
    # Analyze November data if it exists
    if november_path.exists():
        print("\n" + "="*60)
        print("  Analyzing November 2025 Data")
        print("="*60)
        
        nov_csvs = list(november_path.rglob("*.csv"))
        print(f"✓ Found {len(nov_csvs)} November files")
        
        nov_dfs = []
        for csv_file in nov_csvs:
            try:
                df = pd.read_csv(csv_file, low_memory=False)
                for col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                nov_dfs.append(df)
            except:
                pass
        
        if nov_dfs:
            november_df = pd.concat(nov_dfs, ignore_index=True)
            
            # Prepare for prediction
            nov_features = november_df.copy()
            for col in features.columns:
                if col not in nov_features.columns:
                    nov_features[col] = 0
            
            nov_X = nov_features[features.columns].fillna(0)
            predictions = clf.predict(nov_X)
            predictions_decoded = label_encoder.inverse_transform(predictions)
            
            prediction_counts = pd.Series(predictions_decoded).value_counts()
            
            print("\nNovember Prediction Summary:")
            for condition, count in prediction_counts.items():
                pct = (count / len(predictions)) * 100
                print(f"  • {condition}: {count:,} samples ({pct:.1f}%)")
            
            if (predictions_decoded != 'good').any():
                print("\n⚠️  ISSUES DETECTED in November data!")
            else:
                print("\n✅ ALL NOVEMBER DATA LOOKS GOOD!")
else:
    print("\n⚠️  Not enough labeled data to train model")

print("\n" + "="*60)
print("  Analysis Complete!")
print("="*60)

