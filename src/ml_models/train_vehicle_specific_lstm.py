import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# Redirect Matplotlib cache to a temporary directory to resolve Fontconfig permission errors
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

# Force single-threading in C++ backend libraries to prevent OpenMP/GIL deadlocks on Apple Silicon
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import glob
import json
import argparse
import numpy as np
import tensorflow as tf

# Keep GPU disabled to ensure robust CPU-only training on Macs
try:
    tf.config.set_visible_devices([], 'GPU')
except:
    pass

from pathlib import Path

def build_lstm_autoencoder(num_features, sequence_length=10):
    """
    Builds a GRU Autoencoder (using GRUs to prevent Apple Silicon CPU deadlocks). 
    An Autoencoder learns to compress and reconstruct the datastream.
    A high reconstruction error indicates an anomaly (a broken pattern in the 200+ sensors).
    """
    model = tf.keras.Sequential([
        # Encoder
        tf.keras.layers.Input(shape=(sequence_length, num_features), name="sensor_input"),
        tf.keras.layers.GRU(64, return_sequences=True, name="encoder_gru_1"),
        tf.keras.layers.GRU(32, return_sequences=False, name="encoder_gru_2"),
        
        # Bottleneck (Latent Representation of the Vehicle's State)
        tf.keras.layers.RepeatVector(sequence_length, name="bottleneck_repeat"),
        
        # Decoder
        tf.keras.layers.GRU(32, return_sequences=True, name="decoder_gru_1"),
        tf.keras.layers.GRU(64, return_sequences=True, name="decoder_gru_2"),
        tf.keras.layers.TimeDistributed(tf.keras.layers.Dense(num_features), name="reconstruction_output")
    ])
    
    model.compile(optimizer='adam', loss='mse')
    return model

def main():
    print("="*60)
    print(" 🏎️ BCScanTool - Vehicle-Specific Deep Learning Trainer 🏎️")
    print("="*60)
    
    parser = argparse.ArgumentParser(description="Train a Vehicle-Specific LSTM Autoencoder")
    parser.add_argument("--make", type=str, default="Toyota", help="Vehicle Make (e.g., Toyota)")
    parser.add_argument("--model", type=str, default="Tacoma", help="Vehicle Model (e.g., Tacoma)")
    args = parser.parse_args()
    
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / 'data' / 'csv' / 'Vehicle_make_model' / args.make / args.model
    model_dir = project_root / 'models'
    
    model_path = model_dir / f'vehicle_specific_lstm_{args.make}_{args.model}.keras'
    features_path = model_dir / f'vehicle_features_{args.make}_{args.model}.json'
    
    if not data_dir.exists():
        print(f"Error: Data directory not found at {data_dir}")
        return
        
    print(f"1. Scanning for raw datastream CSVs in {data_dir.relative_to(project_root)}...")
    csv_files = list(data_dir.glob("*_clean.csv"))
    
    if not csv_files:
        print(f"No _clean.csv files found for {args.make} {args.model}.")
        return
        
    print(f"Found {len(csv_files)} datastream files. Loading and concatenating...")
    
    import csv
    all_rows = []
    headers = set()
    column_types = {}
    
    for f in csv_files:
        try:
            with open(f, 'r') as fh:
                reader = csv.DictReader(fh)
                header = reader.fieldnames
                if not header:
                    continue
                headers.update(header)
                for row in reader:
                    all_rows.append(row)
                    for col in header:
                        val = row[col]
                        if not val:
                            continue
                        if col not in column_types:
                            column_types[col] = True
                        if column_types[col]:
                            try:
                                float(val)
                            except ValueError:
                                column_types[col] = False
        except Exception as e:
            print(f"Skipping {f.name} due to error: {e}")
            
    print("2. Discovering Vehicle-Specific Features...")
    # Extract all numeric columns
    numeric_cols = [col for col in sorted(list(headers)) if column_types.get(col, False)]
    
    # Remove irrelevant metadata columns if they exist
    if 'Row' in numeric_cols:
        numeric_cols.remove('Row')
        
    num_features = len(numeric_cols)
    print(f"   => Discovered {num_features} unique sensors/parameters for this {args.model}!")
    
    # Save the feature map so the API knows exactly which columns to map during live inference
    model_dir.mkdir(parents=True, exist_ok=True)
    with open(features_path, 'w') as f:
        json.dump(numeric_cols, f)
    print(f"   => Feature map saved to {features_path.name}")
    
    print("\n3. Preprocessing Data (Normalization)...")
    # Parse rows into float matrix
    sensor_list = []
    for row in all_rows:
        x_row = []
        for col in numeric_cols:
            val = row.get(col, '0.0')
            x_row.append(float(val) if val else 0.0)
        sensor_list.append(x_row)
        
    sensor_data = np.array(sensor_list, dtype=np.float32)
    
    # For an Autoencoder, we want to normalize data to 0-1 or standardize.
    # We will use simple MinMax scaling per feature to prevent massive variables (like RPM) from dominating.
    col_mins = np.min(sensor_data, axis=0)
    col_maxs = np.max(sensor_data, axis=0)
    # Avoid division by zero for constant columns
    col_ranges = np.where((col_maxs - col_mins) == 0, 1.0, col_maxs - col_mins)
    
    normalized_data = (sensor_data - col_mins) / col_ranges
    
    # Save scaling parameters for live inference
    scaling_params = {
        "mins": col_mins.tolist(),
        "ranges": col_ranges.tolist()
    }
    with open(model_dir / f'vehicle_scaling_{args.make}_{args.model}.json', 'w') as f:
        json.dump(scaling_params, f)
        
    # Shape for Keras LSTM: [BatchSize, SequenceLength, Features]
    # We split the data into sequence windows of 10 steps (for temporal learning)
    SEQUENCE_LENGTH = 10
    
    print(f"   => Windowing data into {SEQUENCE_LENGTH}-step sequences...")
    num_samples = len(normalized_data) - SEQUENCE_LENGTH
    
    # Take a smaller subset (e.g. 5,000 samples) to make the prototype training snappy
    max_samples = min(num_samples, 5000)
    
    if max_samples <= 0:
        print("Not enough data to create sequences.")
        return
        
    X_train = np.zeros((max_samples, SEQUENCE_LENGTH, num_features), dtype=np.float32)
    for i in range(max_samples):
        X_train[i] = normalized_data[i : i + SEQUENCE_LENGTH]
        
    # In an autoencoder, the target is the input itself!
    Y_train = X_train 
    
    print(f"\n4. Building Custom LSTM Autoencoder for {args.make} {args.model}...")
    model = build_lstm_autoencoder(num_features)
    model.summary()
    
    print("\n5. Training Unsupervised LSTM Anomaly Detector...")
    # Using verbose=2 (one line per epoch) to prevent progress bar terminal TTY deadlocks in subprocesses
    model.fit(X_train, Y_train, epochs=5, batch_size=256, validation_split=0.1, verbose=2)
    print("   => Training Complete!")
    
    model.save(str(model_path))
    print("\n" + "="*60)
    print(f"SUCCESS! Vehicle-Specific LSTM saved to: {model_path.name}")
    print(f"This model now understands the deep correlation between all {num_features} sensors.")
    print("="*60)

if __name__ == "__main__":
    main()
