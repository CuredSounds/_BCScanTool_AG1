"""
Autoencoder-based Anomaly Detection
Unsupervised learning to detect unusual vehicle behavior patterns
"""

import numpy as np
import pandas as pd
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')

try:
    from tensorflow import keras
    from keras.models import Model, load_model
    from keras.layers import Input, Dense
    from keras.optimizers import Adam
    from sklearn.preprocessing import StandardScaler
    KERAS_AVAILABLE = True
except ImportError:
    KERAS_AVAILABLE = False


class AutoencoderAnomalyDetector:
    """
    Autoencoder for detecting anomalous vehicle sensor patterns
    """

    def __init__(self, encoding_dim=8):
        """
        Initialize autoencoder

        Args:
            encoding_dim: Size of compressed representation
        """
        self.encoding_dim = encoding_dim
        self.model = None
        self.scaler = StandardScaler()
        self.threshold = None
        self.is_trained = False

    def build_model(self, input_dim):
        """
        Build autoencoder architecture

        Args:
            input_dim: Number of input features
        """
        if not KERAS_AVAILABLE:
            return

        # Input layer
        input_layer = Input(shape=(input_dim,))

        # Encoder
        encoded = Dense(32, activation='relu')(input_layer)
        encoded = Dense(16, activation='relu')(encoded)
        encoded = Dense(self.encoding_dim, activation='relu')(encoded)

        # Decoder
        decoded = Dense(16, activation='relu')(encoded)
        decoded = Dense(32, activation='relu')(decoded)
        decoded = Dense(input_dim, activation='linear')(decoded)

        # Autoencoder model
        self.model = Model(inputs=input_layer, outputs=decoded)

        self.model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='mse'
        )

    def train(self, data, epochs=50, verbose=0):
        """
        Train autoencoder on normal data

        Args:
            data: Training data (normal behavior only)
            epochs: Training epochs
            verbose: Verbosity
        """
        if not KERAS_AVAILABLE:
            print("Cannot train: TensorFlow not installed")
            return False

        # Normalize
        data_scaled = self.scaler.fit_transform(data)

        # Build model
        self.build_model(data_scaled.shape[1])

        # Train
        self.model.fit(
            data_scaled, data_scaled,
            epochs=epochs,
            batch_size=32,
            validation_split=0.1,
            verbose=verbose,
            shuffle=True
        )

        # Calculate reconstruction errors on training data
        reconstructions = self.model.predict(data_scaled, verbose=0)
        reconstruction_errors = np.mean(np.square(data_scaled - reconstructions), axis=1)

        # Set threshold at 95th percentile
        self.threshold = np.percentile(reconstruction_errors, 95)

        self.is_trained = True
        return True

    def detect_anomalies(self, data):
        """
        Detect anomalies in new data

        Args:
            data: Data to check for anomalies

        Returns:
            anomaly_scores, is_anomaly
        """
        if not self.is_trained:
            return None, None

        # Normalize
        data_scaled = self.scaler.transform(data)

        # Reconstruct
        reconstructions = self.model.predict(data_scaled, verbose=0)

        # Calculate errors
        reconstruction_errors = np.mean(np.square(data_scaled - reconstructions), axis=1)

        # Determine anomalies
        is_anomaly = reconstruction_errors > self.threshold

        return reconstruction_errors, is_anomaly


def run_autoencoder_analysis(dataframe):
    """
    Run autoencoder anomaly detection on vehicle data

    Args:
        dataframe: Vehicle sensor data
    """
    if not KERAS_AVAILABLE:
        print("\n" + "="*70)
        print("AUTOENCODER ANOMALY DETECTION - TENSORFLOW REQUIRED")
        print("="*70)
        print("\nTensorFlow not installed. Skipping autoencoder analysis...")
        return None

    print("\n" + "="*70)
    print("AUTOENCODER ANOMALY DETECTION")
    print("="*70)

    # Select numeric columns
    numeric_cols = dataframe.select_dtypes(include=[np.number]).columns
    # Filter relevant columns (avoid IDs and metadata)
    sensor_cols = [c for c in numeric_cols if 'Row' not in c and 'Unnamed' not in c][:10]  # Limit to 10 features

    if len(sensor_cols) < 3:
        print("Not enough sensor data for autoencoder")
        return None

    # Prepare data
    data = dataframe[sensor_cols].dropna()

    if len(data) < 100:
        print(f"Not enough samples: {len(data)} (need at least 100)")
        return None

    print(f"Training on {len(sensor_cols)} sensors, {len(data)} samples")

    # Train autoencoder
    detector = AutoencoderAnomalyDetector(encoding_dim=min(8, len(sensor_cols)))
    success = detector.train(data.values, epochs=30, verbose=0)

    if not success:
        return None

    # Detect anomalies
    errors, anomalies = detector.detect_anomalies(data.values)

    anomaly_count = np.sum(anomalies)
    anomaly_pct = (anomaly_count / len(data)) * 100

    print(f"\n✓ Analysis complete")
    print(f"  Anomalies detected: {anomaly_count} ({anomaly_pct:.1f}%)")
    print(f"  Threshold: {detector.threshold:.4f}")

    if anomaly_pct > 15:
        print(f"  ⚠️  High anomaly rate indicates unusual sensor patterns")

    return {
        'detector': detector,
        'anomaly_count': anomaly_count,
        'anomaly_percentage': anomaly_pct,
        'anomaly_indices': np.where(anomalies)[0].tolist()
    }
