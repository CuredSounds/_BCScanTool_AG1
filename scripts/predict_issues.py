#!/usr/bin/env python3
"""
BCScanTool - Predict Issues on Unlabeled Data

This script loads the pre-trained classifier and the master dataset,
runs predictions on all "unknown" data, and reports the findings.
"""
import pandas as pd
from pathlib import Path
import joblib
import numpy as np

def load_model(models_path: Path):
    """Loads the trained classifier, label encoder, and feature columns."""
    model_path = models_path / "diagnostic_classifier.joblib"
    print(f"--> Loading model from: {model_path}")
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found at {model_path}. Please run train_classifier.py first.")
    
    model_payload = joblib.load(model_path)
    print("    [✓] Model loaded successfully.")
    return model_payload['classifier'], model_payload['label_encoder'], model_payload['feature_columns']

def load_unlabeled_data(processed_data_path: Path) -> pd.DataFrame:
    """Loads the master dataset and filters for 'unknown' conditions."""
    dataset_path = processed_data_path / "master_dataset.parquet"
    print(f"--> Loading dataset from: {dataset_path}")
    if not dataset_path.exists():
        raise FileNotFoundError(f"Master dataset not found. Please run build_dataset.py first.")
    
    df = pd.read_parquet(dataset_path)
    unlabeled_df = df[df['condition'] == 'unknown'].copy()
    print(f"    [✓] Found {len(unlabeled_df):,} unlabeled rows to predict.")
    return unlabeled_df

def prepare_prediction_data(df: pd.DataFrame, feature_columns: list) -> pd.DataFrame:
    """Prepares the unlabeled data for prediction, ensuring columns match the model."""
    print("--> Preparing data for prediction...")
    
    # Ensure all required feature columns are present, fill missing with NaN
    for col in feature_columns:
        if col not in df.columns:
            df[col] = np.nan
            
    # Reorder columns to match the order during training
    df = df[feature_columns]
    
    # Fill any NaN values with the column median (same strategy as training)
    df = df.fillna(df.median())
    
    print(f"    [✓] Data prepared with {df.shape[1]} features.")
    return df

def main():
    """Main function to run prediction and report results."""
    project_root = Path(__file__).resolve().parents[1]
    processed_data_path = project_root / "data" / "processed"
    models_path = project_root / "models"
    
    try:
        # Load model and data
        classifier, label_encoder, feature_columns = load_model(models_path)
        unlabeled_df = load_unlabeled_data(processed_data_path)

        if unlabeled_df.empty:
            print("\nNo unlabeled data to predict. Exiting.")
            return
            
        # Prepare data for prediction
        X_predict = prepare_prediction_data(unlabeled_df, feature_columns)
        
        print("\n--> Running predictions...")
        predictions_encoded = classifier.predict(X_predict)
        predictions_decoded = label_encoder.inverse_transform(predictions_encoded)
        print("    [✓] Prediction complete.")
        
        # Add predictions to the dataframe for analysis
        unlabeled_df['predicted_condition'] = predictions_decoded
        
        # --- Report Findings ---
        print("\n" + "="*50)
        print("          Diagnostic Prediction Report")
        print("="*50)
        
        prediction_counts = unlabeled_df['predicted_condition'].value_counts()
        print("\nPrediction Summary:")
        print(prediction_counts)
        
        # Show details of any data flagged with an issue
        flagged_issues = prediction_counts[prediction_counts.index != 'good']
        if not flagged_issues.empty:
            print("\n[!] Potential Issues Detected!")
            for issue_type, count in flagged_issues.items():
                print(f"\n--- Found {count} rows predicted as '{issue_type}' ---")
                issue_df = unlabeled_df[unlabeled_df['predicted_condition'] == issue_type]
                
                # Show which original files these issues came from
                print("Source Files:")
                print(issue_df['session_file'].value_counts().to_string())
                
                # Show a sample of the flagged data
                print("\nSample of flagged data:")
                print(issue_df[['session_file', 'predicted_condition'] + list(feature_columns[:3])].head())
        else:
            print("\n[✓] No issues detected in the unlabeled data.")
            
    except FileNotFoundError as e:
        print(f"\n[ERROR] {e}")
    except Exception as e:
        print(f"\n[UNEXPECTED ERROR] An error occurred: {e}")

if __name__ == "__main__":
    main()

