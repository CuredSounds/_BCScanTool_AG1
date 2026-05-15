#!/usr/bin/env python3
"""
BCScanTool - Complete Analysis Pipeline
Run this single script to analyze all your diagnostic data.
"""
import sys
from pathlib import Path

# Add project root to Python path so 'src' can be imported
sys.path.append(str(Path(__file__).resolve().parents[1]))

import pandas as pd
from src.ml_models.training_pipeline import DataIngestor, SupervisedModelPipeline, AnomalyDetectorPipeline

def main():
    print("="*60)
    print("  BCScanTool v3.0 - ML Training Pipeline")
    print("="*60)
    
    project_root = Path(__file__).resolve().parents[1]
    raw_data_path = project_root / "data" / "raw"
    models_path = project_root / "models"
    
    print("\n[1/3] Ingesting & Formatting Data...")
    ingestor = DataIngestor(raw_data_path)
    df = ingestor.load_data()
    
    if df.empty:
        print("No data found! Please add CSVs to data/raw.")
        return
        
    print(f"✓ Loaded {len(df):,} total rows of diagnostic data.")
    
    print("\n[2/3] Training Supervised Model...")
    supervised = SupervisedModelPipeline(models_path)
    supervised.train(df)
    
    print("\n[3/3] Training Unsupervised Anomaly Detector...")
    anomaly = AnomalyDetectorPipeline(models_path)
    anomaly.train(df)
    
    print("\n" + "="*60)
    print("  Pipeline Execution Complete! Models Saved to /models")
    print("="*60)

if __name__ == "__main__":
    main()
