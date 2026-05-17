#!/usr/bin/env python3
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import pandas as pd
import numpy as np
import tensorflow as tf

# Disable Apple Silicon Metal GPU to prevent XLA compile hangs
try:
    tf.config.set_visible_devices([], 'GPU')
except:
    pass

from pathlib import Path

def main():
    print("="*60)
    print("   🧠 BCScanTool - Python Deep Learning LSTM Trainer 🧠")
    print("="*60)
    
    # Paths
    project_root = Path(__file__).resolve().parents[2]
    csv_file = project_root / 'data' / 'processed' / 'diagnostic_reports.csv'
    model_dir = project_root / 'models'
    model_path = model_dir / 'vehicle_lstm_model.keras'
    
    if not csv_file.exists():
        print(f"Error: Processed data not found at {csv_file}")
        print("Please run database seeding/reset first!")
        return
        
    print(f"1. Loading Training Data from CSV: {csv_file.name}")
    df = pd.read_csv(csv_file)
    
    # 21 numeric features (exactly mirroring MATLAB's train_lstm_export_onnx.m)
    numeric_cols = [
        'year', 'engine_speed_rpm', 'coolant_temp_f', 
        'misfire_current_cyl1', 'misfire_current_cyl2', 'misfire_current_cyl3', 'misfire_current_cyl4', 
        'misfire_current_cyl5', 'misfire_current_cyl6', 'misfire_current_cyl7', 'misfire_current_cyl8', 
        'misfire_history_cyl1', 'misfire_history_cyl2', 'misfire_history_cyl3', 'misfire_history_cyl4', 
        'misfire_history_cyl5', 'misfire_history_cyl6', 'misfire_history_cyl7', 'misfire_history_cyl8', 
        'total_misfire', 'misfire_cycles'
    ]
    
    # Align features (fill missing columns with 0.0)
    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0.0
            
    sensor_data = df[numeric_cols].fillna(0).values.astype(np.float32)
    
    # Target variable (predict total_misfire, same as MATLAB)
    y_data = df['total_misfire'].fillna(0).values.astype(np.float32)
    
    print("\n2. Windowing Data & Defining LSTM Architecture...")
    # LSTMs cannot unroll 255,000 steps at once without crashing memory. We window it!
    SEQUENCE_LENGTH = 10
    num_samples = len(sensor_data) - SEQUENCE_LENGTH
    
    # We will take a smaller subset of the data (5,000 samples) to make training snappy for the prototype
    max_samples = min(num_samples, 5000)
    
    X_train = np.zeros((max_samples, SEQUENCE_LENGTH, len(numeric_cols)), dtype=np.float32)
    y_train = np.zeros((max_samples, SEQUENCE_LENGTH, 1), dtype=np.float32)
    
    for i in range(max_samples):
        X_train[i] = sensor_data[i : i + SEQUENCE_LENGTH]
        y_train[i] = np.expand_dims(y_data[i : i + SEQUENCE_LENGTH], axis=-1)
        
    print(f"   Generated {max_samples} sequences of length {SEQUENCE_LENGTH}.")
    print(f"   Input features: {len(numeric_cols)}")
    print("   LSTM Hidden Units: 50")
    print("   Output layer: Dense (1 output, sequence-to-sequence mode)")
    
    # Replicate MATLAB layers: SequenceInput -> LSTM -> FullyConnected -> Regression
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(None, len(numeric_cols)), name="input"),
        tf.keras.layers.LSTM(50, return_sequences=True, unroll=True, name="lstm"),
        tf.keras.layers.Dense(1, name="fc")
    ])
    
    model.compile(optimizer='adam', loss='mse', run_eagerly=True)
    
    print("\n3. Training Network using Keras Deep Learning Engine (Verbose disabled to prevent macOS terminal deadlocks)...")
    # Set verbose=0 to prevent the Keras progress bar from deadlocking zsh
    model.fit(X_train, y_train, epochs=15, batch_size=256, verbose=0, use_multiprocessing=False, workers=1)
    print("   => Training Complete!")
    
    # Save the model
    model_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(model_path))
    
    print("\n" + "="*60)
    print(f"SUCCESS! Keras LSTM model saved to: {model_path}")
    print("Your FastAPI server will now automatically load it alongside the ONNX model!")
    print("="*60)

if __name__ == "__main__":
    main()
