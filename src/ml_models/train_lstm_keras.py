import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
# Direct Matplotlib to a writable temporary directory to prevent Fontconfig cache deadlocks
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"

# Force single-threading in C++ backend libraries to prevent OpenMP/GIL deadlocks on Apple Silicon
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import numpy as np
import tensorflow as tf

# Keep GPU disabled to ensure robust CPU-only training on Macs
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
    import csv
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        
    # 21 numeric features (exactly mirroring MATLAB's train_lstm_export_onnx.m)
    numeric_cols = [
        'year', 'engine_speed_rpm', 'coolant_temp_f', 
        'misfire_current_cyl1', 'misfire_current_cyl2', 'misfire_current_cyl3', 'misfire_current_cyl4', 
        'misfire_current_cyl5', 'misfire_current_cyl6', 'misfire_current_cyl7', 'misfire_current_cyl8', 
        'misfire_history_cyl1', 'misfire_history_cyl2', 'misfire_history_cyl3', 'misfire_history_cyl4', 
        'misfire_history_cyl5', 'misfire_history_cyl6', 'misfire_history_cyl7', 'misfire_history_cyl8', 
        'total_misfire', 'misfire_cycles'
    ]
    
    sensor_list = []
    y_list = []
    for row in rows:
        x_row = []
        for col in numeric_cols:
            val = row.get(col, '0.0')
            x_row.append(float(val) if val else 0.0)
        sensor_list.append(x_row)
        
        y_val = row.get('total_misfire', '0.0')
        y_list.append(float(y_val) if y_val else 0.0)
        
    sensor_data = np.array(sensor_list, dtype=np.float32)
    y_data = np.array(y_list, dtype=np.float32)
    
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
    
    # Replicate MATLAB layers: SequenceInput -> GRU -> FullyConnected -> Regression
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(SEQUENCE_LENGTH, len(numeric_cols)), name="input"),
        tf.keras.layers.GRU(50, return_sequences=True, name="gru"),
        tf.keras.layers.Dense(1, name="fc")
    ])
    
    model.compile(optimizer='adam', loss='mse')
    
    print("\n3. Training Network using Keras Deep Learning Engine...")
    # Using verbose=2 (one line per epoch) to prevent progress bar terminal TTY deadlocks in subprocesses
    model.fit(X_train, y_train, epochs=15, batch_size=256, verbose=2)
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
