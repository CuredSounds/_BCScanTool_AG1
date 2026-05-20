"""
Autoencoder-based Anomaly Detection
Unsupervised learning to detect unusual vehicle behavior patterns
"""

import numpy as np
import pandas as pd
import logging
from typing import Tuple, List
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger("BCScanTool.Autoencoder")

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

        # Threshold: mean + 3*std of reconstruction error (statistical outlier boundary)
        # This is more principled than a fixed percentile which always flags 5% as anomalous
        self.threshold = np.mean(reconstruction_errors) + 3 * np.std(reconstruction_errors)
        self.train_error_mean = float(np.mean(reconstruction_errors))
        self.train_error_std = float(np.std(reconstruction_errors))

        self.is_trained = True
        logger.info(f"Autoencoder trained. Threshold: {self.threshold:.6f} "
                     f"(mean={self.train_error_mean:.6f}, std={self.train_error_std:.6f})")
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
    Run autoencoder anomaly detection on vehicle data.
    Uses parameter tiers for feature selection instead of arbitrary column picking.
    """
    if not KERAS_AVAILABLE:
        logger.warning("TensorFlow not installed. Skipping autoencoder analysis.")
        return None

    logger.info("=" * 70)
    logger.info("AUTOENCODER ANOMALY DETECTION")

    # Use parameter tiers for feature selection
    from src import config
    tiers = config.load_parameter_tiers()
    tier_a_cols = tiers.get("tier_a", [])

    if tier_a_cols:
        # Use Tier A columns that exist in the dataframe
        sensor_cols = [c for c in tier_a_cols if c in dataframe.columns]
        if len(sensor_cols) < 3:
            # Fallback: try matching by substring
            sensor_cols = []
            for tier_col in tier_a_cols:
                for df_col in dataframe.columns:
                    if tier_col.lower() in df_col.lower():
                        sensor_cols.append(df_col)
                        break
    else:
        # Legacy fallback: pick numeric columns, avoid metadata
        numeric_cols = dataframe.select_dtypes(include=[np.number]).columns
        sensor_cols = [c for c in numeric_cols
                       if 'Row' not in c and 'Unnamed' not in c
                       and 'distance' not in c.lower() and 'time' not in c.lower()]

    if len(sensor_cols) < 3:
        logger.warning(f"Not enough sensor columns for autoencoder: {len(sensor_cols)}")
        return None

    data = dataframe[sensor_cols].dropna()
    if len(data) < 100:
        logger.warning(f"Not enough samples: {len(data)} (need at least 100)")
        return None

    logger.info(f"Training on {len(sensor_cols)} sensors, {len(data)} samples")

    detector = AutoencoderAnomalyDetector(encoding_dim=min(8, len(sensor_cols)))
    success = detector.train(data.values, epochs=30, verbose=0)
    if not success:
        return None

    errors, anomalies = detector.detect_anomalies(data.values)
    anomaly_count = int(np.sum(anomalies))
    anomaly_pct = (anomaly_count / len(data)) * 100

    logger.info(f"Analysis complete: {anomaly_count} anomalies ({anomaly_pct:.1f}%)")
    logger.info(f"Threshold: {detector.threshold:.6f}")
    if anomaly_pct > 15:
        logger.warning("High anomaly rate indicates unusual sensor patterns")

    return {
        'detector': detector,
        'anomaly_count': anomaly_count,
        'anomaly_percentage': anomaly_pct,
        'anomaly_indices': np.where(anomalies)[0].tolist(),
        'features_used': sensor_cols,
    }
