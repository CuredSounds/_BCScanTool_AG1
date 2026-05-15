"""
LSTM Time-Series Forecasting for Vehicle Diagnostics
Predicts future sensor values and detects anomalies
"""

import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Dict, Any
import warnings
import logging
from src.core.pid_analyzer import PIDAnalyzer

warnings.filterwarnings('ignore')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LSTMPredictor")

try:
    from sklearn.preprocessing import MinMaxScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("Scikit-learn not installed. Scaling features will be disabled.")
    SKLEARN_AVAILABLE = False

try:
    import tensorflow as tf
    from tensorflow.keras.models import Sequential, load_model
    from tensorflow.keras.layers import LSTM, Dense, Dropout
    from tensorflow.keras.optimizers import Adam
    KERAS_AVAILABLE = True
except ImportError:
    logger.warning("TensorFlow/Keras not installed. LSTM features will be limited.")
    KERAS_AVAILABLE = False


class LSTMPredictor:
    """
    LSTM-based time-series prediction for vehicle sensors
    """

    def __init__(self, sequence_length: int = 20, hidden_layers: List[int] = [64, 32], 
                 dropout_rate: float = 0.2, learning_rate: float = 0.001):
        """
        Initialize LSTM predictor

        Args:
            sequence_length: Number of time steps to use for prediction
            hidden_layers: List of units for LSTM layers
            dropout_rate: Dropout rate for regularization
            learning_rate: Learning rate for Adam optimizer
        """
        self.sequence_length = sequence_length
        self.hidden_layers = hidden_layers
        self.dropout_rate = dropout_rate
        self.learning_rate = learning_rate
        
        self.model = None
        self.scaler = MinMaxScaler() if SKLEARN_AVAILABLE else None
        self.is_trained = False

    def prepare_sequences(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare time-series sequences for LSTM using sliding window

        Args:
            data: 1D array of sensor values

        Returns:
            X, y: Input sequences and target values
        """
        if len(data) <= self.sequence_length:
            return np.array([]), np.array([])
            
        # Use sliding window to create sequences
        # X: [samples, sequence_length], y: [samples]
        shape = (data.size - self.sequence_length, self.sequence_length)
        strides = data.strides + data.strides
        X = np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)
        y = data[self.sequence_length:]
        
        return X.copy(), y.copy()

    def build_model(self, input_shape: Tuple[int, int]):
        """
        Build LSTM model architecture based on configuration

        Args:
            input_shape: Shape of input sequences (time_steps, features)
        """
        if not KERAS_AVAILABLE:
            logger.error("Cannot build model: TensorFlow not installed")
            return

        layers = []
        # Add LSTM layers
        for i, units in enumerate(self.hidden_layers):
            return_sequences = i < len(self.hidden_layers) - 1
            if i == 0:
                layers.append(LSTM(units, return_sequences=return_sequences, input_shape=input_shape))
            else:
                layers.append(LSTM(units, return_sequences=return_sequences))
            
            if self.dropout_rate > 0:
                layers.append(Dropout(self.dropout_rate))

        # Add Dense layers
        layers.append(Dense(16, activation='relu'))
        layers.append(Dense(1, activation='linear'))

        self.model = Sequential(layers)
        self.model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        logger.info(f"LSTM model built with input shape {input_shape}")

    def train(self, data: pd.Series, epochs: int = 50, batch_size: int = 32, verbose: int = 0) -> bool:
        """
        Train LSTM model on time-series data

        Args:
            data: Pandas Series with sensor values
            epochs: Number of training epochs
            batch_size: Training batch size
            verbose: Training verbosity
        """
        if not KERAS_AVAILABLE:
            logger.error("Cannot train: TensorFlow not installed")
            return False

        # Clean data
        data_clean = data.dropna().values.reshape(-1, 1)

        if len(data_clean) < self.sequence_length + 10:
            logger.warning(f"Not enough data points: {len(data_clean)} (need at least {self.sequence_length + 10})")
            return False

        # Normalize
        if self.scaler:
            data_scaled = self.scaler.fit_transform(data_clean)
        else:
            data_scaled = data_clean

        # Prepare sequences
        X, y = self.prepare_sequences(data_scaled.flatten())

        if len(X) == 0:
            logger.warning("No sequences generated")
            return False

        # Reshape for LSTM [samples, time steps, features]
        X = X.reshape((X.shape[0], X.shape[1], 1))

        # Build model if not already built or shape changed
        if self.model is None:
            self.build_model((X.shape[1], 1))

        # Train
        self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            verbose=verbose
        )

        self.is_trained = True
        logger.info("LSTM model training completed")
        return True

    def predict_next(self, recent_data: np.ndarray) -> Optional[float]:
        """
        Predict next value in sequence

        Args:
            recent_data: Recent sensor values (length >= sequence_length)

        Returns:
            Predicted next value
        """
        if not self.is_trained or self.model is None:
            return None

        # Take only the last sequence_length points
        seq = recent_data[-self.sequence_length:].reshape(-1, 1)
        
        # Prepare input
        if self.scaler:
            data_scaled = self.scaler.transform(seq)
        else:
            data_scaled = seq
            
        X = data_scaled.reshape(1, self.sequence_length, 1)

        # Predict
        prediction_scaled = self.model.predict(X, verbose=0)

        # Inverse transform
        if self.scaler:
            prediction = self.scaler.inverse_transform(prediction_scaled)
        else:
            prediction = prediction_scaled

        return float(prediction[0, 0])

    def detect_anomalies(self, data: pd.Series, threshold: float = 2.0) -> List[int]:
        """
        Detect anomalies by comparing predictions to actual values using batch prediction

        Args:
            data: Time-series data
            threshold: Standard deviations for anomaly threshold

        Returns:
            List of anomaly indices
        """
        if not self.is_trained or self.model is None:
            logger.warning("Model not trained yet")
            return []

        data_clean = data.dropna().values
        if len(data_clean) < self.sequence_length + 1:
            return []

        # Scale data
        if self.scaler:
            data_scaled = self.scaler.transform(data_clean.reshape(-1, 1)).flatten()
        else:
            data_scaled = data_clean

        # Prepare all sequences for batch prediction
        X_batch, y_actual_scaled = self.prepare_sequences(data_scaled)
        
        if len(X_batch) == 0:
            return []
            
        # Reshape for LSTM [samples, time steps, features]
        X_batch = X_batch.reshape((X_batch.shape[0], X_batch.shape[1], 1))

        # Batch prediction
        predictions_scaled = self.model.predict(X_batch, verbose=0)
        
        # Inverse transform
        if self.scaler:
            predictions = self.scaler.inverse_transform(predictions_scaled).flatten()
            actuals = data_clean[self.sequence_length:]
        else:
            predictions = predictions_scaled.flatten()
            actuals = data_clean[self.sequence_length:]

        # Calculate errors
        errors = np.abs(actuals - predictions)

        # Detect anomalies (errors > threshold * std)
        mean_error = np.mean(errors)
        std_error = np.std(errors)
        anomaly_threshold = mean_error + (threshold * std_error)

        anomalies = []
        for i, error in enumerate(errors):
            if error > anomaly_threshold:
                # Anomaly is at the point being predicted
                anomalies.append(self.sequence_length + i)

        logger.info(f"Detected {len(anomalies)} anomalies in {len(data_clean)} points")
        return anomalies

    def save_model(self, filepath: str):
        """Save trained model"""
        if self.is_trained and self.model:
            self.model.save(filepath)
            logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str) -> bool:
        """Load trained model"""
        if not KERAS_AVAILABLE:
            return False

        try:
            self.model = load_model(filepath)
            self.is_trained = True
            logger.info(f"Model loaded from {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False


class VehicleLSTMAnalyzer:
    """
    High-level analyzer using LSTM for vehicle diagnostics
    """

    def __init__(self, dataframe: pd.DataFrame):
        """
        Initialize with vehicle data

        Args:
            dataframe: Pandas DataFrame with sensor data
        """
        self.df = dataframe
        self.predictors = {}
        self.results = {}
        # Initialize PID Analyzer for robust column mapping
        self.pid_analyzer = PIDAnalyzer(dataframe)

    def _run_generic_analysis(self, pid_name: str, label: str, seq_len: int = 10, 
                             epochs: int = 30, threshold: float = 2.0) -> Optional[Dict[str, Any]]:
        """Generic method to run LSTM analysis on a PID"""
        logger.info(f"Analyzing {label} with LSTM...")
        
        data = self.pid_analyzer.get_pid_data(pid_name)
        if data.empty:
            logger.warning(f"No {label} data found")
            return None
            
        data = data[data > 0] # Filter valid data
        if len(data) < 50:
            logger.warning(f"Not enough data for {label} analysis")
            return None
            
        predictor = LSTMPredictor(sequence_length=seq_len)
        if predictor.train(data, epochs=epochs, verbose=0):
            anomalies = predictor.detect_anomalies(data, threshold=threshold)
            
            result = {
                'anomaly_count': len(anomalies),
                'anomaly_percentage': (len(anomalies) / len(data)) * 100,
                'anomaly_indices': anomalies,
                'current_value': data.iloc[-1]
            }
            
            # Predict next value
            recent = data.tail(seq_len).values
            next_val = predictor.predict_next(recent)
            if next_val is not None:
                result['predicted_next'] = next_val
                result['trend'] = 'rising' if next_val > data.iloc[-1] else 'stable/falling'
            
            self.predictors[pid_name] = predictor
            self.results[pid_name] = result
            logger.info(f"✓ {label} Analysis Complete. Anomalies: {len(anomalies)}")
            return result
        return None

    def analyze_rpm_stability(self):
        """Analyze and predict RPM stability"""
        self._run_generic_analysis('engine_speed', 'RPM', seq_len=10, threshold=2.5)

    def analyze_temperature_trends(self):
        """Predict temperature trends"""
        self._run_generic_analysis('coolant_temp', 'Temperature', seq_len=15, threshold=2.0)

    def analyze_misfire_patterns(self):
        """Predict misfire patterns"""
        data = self.pid_analyzer.get_pid_data('misfire_count')
        if data.empty:
            logger.info("No misfire data found")
            return
            
        data = data.fillna(0)
        if data.sum() > 0:
            self._run_generic_analysis('misfire_count', 'Misfires', seq_len=10, threshold=1.5)
        else:
            logger.info("No misfires detected in data")

    def generate_report(self):
        """Generate LSTM analysis report"""
        if not self.results:
            logger.info("No LSTM analysis results available")
            return

        print("\n" + "="*70)
        print("LSTM PREDICTIVE ANALYSIS SUMMARY")
        print("="*70)

        for metric, result in self.results.items():
            print(f"\n{metric.upper()}:")
            for key, value in result.items():
                if key != 'anomaly_indices':
                    if isinstance(value, float):
                        print(f"  {key}: {value:.2f}")
                    else:
                        print(f"  {key}: {value}")


def run_lstm_analysis(dataframe: pd.DataFrame):
    """
    Main entry point for LSTM analysis

    Args:
        dataframe: Vehicle sensor data
    """
    if not KERAS_AVAILABLE:
        print("\n" + "="*70)
        print("LSTM ANALYSIS - TENSORFLOW REQUIRED")
        print("="*70)
        print("\nTensorFlow is not installed. Skipping LSTM analysis...")
        return None

    analyzer = VehicleLSTMAnalyzer(dataframe)

    # Run analyses
    analyzer.analyze_rpm_stability()
    analyzer.analyze_temperature_trends()
    analyzer.analyze_misfire_patterns()

    # Generate report
    analyzer.generate_report()

    return analyzer
