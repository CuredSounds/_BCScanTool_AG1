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
        Prepare time-series sequences for LSTM using sliding window.
        Supports multivariate data.

        Args:
            data: 2D array of sensor values [samples, features]

        Returns:
            X, y: Input sequences and target values
        """
        if len(data) <= self.sequence_length:
            return np.array([]), np.array([])
            
        X, y = [], []
        for i in range(len(data) - self.sequence_length):
            X.append(data[i:(i + self.sequence_length), :])
            y.append(data[i + self.sequence_length, :])
            
        return np.array(X), np.array(y)

    def build_model(self, input_shape: Tuple[int, int]):
        """
        Build LSTM model architecture based on configuration

        Args:
            input_shape: Shape of input sequences (time_steps, features)
        """
        if not KERAS_AVAILABLE:
            logger.error("Cannot build model: TensorFlow not installed")
            return

        n_features = input_shape[1]
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
        layers.append(Dense(n_features, activation='linear')) # Output all features

        self.model = Sequential(layers)
        self.model.compile(
            optimizer=Adam(learning_rate=self.learning_rate),
            loss='mse',
            metrics=['mae']
        )
        logger.info(f"LSTM model built with input shape {input_shape}")

    def train(self, data: pd.DataFrame, epochs: int = 50, batch_size: int = 32, verbose: int = 0) -> bool:
        """
        Train LSTM model on multivariate time-series data

        Args:
            data: Pandas DataFrame with sensor values
            epochs: Number of training epochs
            batch_size: Training batch size
            verbose: Training verbosity
        """
        if not KERAS_AVAILABLE:
            logger.error("Cannot train: TensorFlow not installed")
            return False

        # Clean data
        data_clean = data.dropna().values

        if len(data_clean) < self.sequence_length + 10:
            logger.warning(f"Not enough data points: {len(data_clean)} (need at least {self.sequence_length + 10})")
            return False

        # Normalize
        if self.scaler:
            data_scaled = self.scaler.fit_transform(data_clean)
        else:
            data_scaled = data_clean

        # Prepare sequences
        X, y = self.prepare_sequences(data_scaled)

        if len(X) == 0:
            logger.warning("No sequences generated")
            return False

        # Build model if not already built or shape changed
        if self.model is None:
            self.build_model((X.shape[1], X.shape[2]))

        # Train
        self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=0.2,
            verbose=verbose
        )

        self.is_trained = True
        logger.info(f"Multivariate LSTM model training completed on {X.shape[2]} features")
        return True

    def predict_next(self, recent_data: np.ndarray) -> Optional[np.ndarray]:
        """
        Predict next value in sequence for all features

        Args:
            recent_data: Recent sensor values (length >= sequence_length, features=N)

        Returns:
            Predicted next values array
        """
        if not self.is_trained or self.model is None:
            return None

        # Take only the last sequence_length points
        seq = recent_data[-self.sequence_length:]
        
        # Prepare input
        if self.scaler:
            data_scaled = self.scaler.transform(seq)
        else:
            data_scaled = seq
            
        X = data_scaled.reshape(1, self.sequence_length, -1)

        # Predict
        prediction_scaled = self.model.predict(X, verbose=0)

        # Inverse transform
        if self.scaler:
            prediction = self.scaler.inverse_transform(prediction_scaled)
        else:
            prediction = prediction_scaled

        return prediction[0]

    def detect_anomalies(self, data: pd.DataFrame, threshold: float = 3.0) -> List[int]:
        """
        Detect anomalies by comparing predictions to actual values across all sensors

        Args:
            data: Multivariate time-series data
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
            data_scaled = self.scaler.transform(data_clean)
        else:
            data_scaled = data_clean

        # Prepare all sequences for batch prediction
        X_batch, y_actual_scaled = self.prepare_sequences(data_scaled)
        
        if len(X_batch) == 0:
            return []

        # Batch prediction
        predictions_scaled = self.model.predict(X_batch, verbose=0)
        
        # Calculate reconstruction error (MSE across all sensors)
        mse = np.mean(np.square(y_actual_scaled - predictions_scaled), axis=1)

        # Detect anomalies (mse > mean + threshold * std)
        mean_mse = np.mean(mse)
        std_mse = np.std(mse)
        anomaly_threshold = mean_mse + (threshold * std_mse)

        anomalies = []
        for i, error in enumerate(mse):
            if error > anomaly_threshold:
                anomalies.append(self.sequence_length + i)

        logger.info(f"Detected {len(anomalies)} multivariate anomalies in {len(data_clean)} points")
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
        """Generic method to run LSTM analysis on a PID.
        Falls back to statistical anomaly detection when data is too small for LSTM."""
        logger.info(f"Analyzing {label}...")
        
        data = self.pid_analyzer.get_pid_data(pid_name)
        if data.empty:
            logger.warning(f"No {label} data found")
            return None
            
        data = data[data > 0]
        if len(data) < 30:
            logger.warning(f"Not enough data for {label} analysis ({len(data)} points)")
            return None

        # For small datasets (<200 points), use statistical detection instead of LSTM
        # LSTM needs hundreds of samples to learn meaningful patterns; with <200 points
        # it memorizes rather than generalizes
        if len(data) < 200:
            logger.info(f"Using statistical fallback for {label} ({len(data)} points < 200 LSTM minimum)")
            return self._statistical_anomaly_detection(data, pid_name, label, threshold)

        predictor = LSTMPredictor(sequence_length=seq_len)
        if predictor.train(data, epochs=epochs, verbose=0):
            anomalies = predictor.detect_anomalies(data, threshold=threshold)
            
            result = {
                'method': 'lstm',
                'anomaly_count': len(anomalies),
                'anomaly_percentage': (len(anomalies) / len(data)) * 100,
                'anomaly_indices': anomalies,
                'current_value': float(data.iloc[-1]),
            }
            
            recent = data.tail(seq_len).values
            next_val = predictor.predict_next(recent)
            if next_val is not None:
                result['predicted_next'] = next_val
                result['trend'] = 'rising' if next_val > data.iloc[-1] else 'stable/falling'
            
            self.predictors[pid_name] = predictor
            self.results[pid_name] = result
            logger.info(f"✓ {label} LSTM Analysis: {len(anomalies)} anomalies")
            return result
        return None

    def _statistical_anomaly_detection(self, data: pd.Series, pid_name: str,
                                        label: str, threshold: float) -> Optional[Dict[str, Any]]:
        """Z-score based anomaly detection for small datasets where LSTM would overfit."""
        values = data.values
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return None
            
        z_scores = np.abs((values - mean) / std)
        anomaly_indices = list(np.where(z_scores > threshold)[0])
        
        # Simple trend: linear regression slope
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0] if len(values) > 2 else 0
        
        result = {
            'method': 'statistical_zscore',
            'anomaly_count': len(anomaly_indices),
            'anomaly_percentage': (len(anomaly_indices) / len(data)) * 100,
            'anomaly_indices': anomaly_indices,
            'current_value': float(data.iloc[-1]),
            'mean': float(mean),
            'std': float(std),
            'trend': 'rising' if slope > 0.1 else 'falling' if slope < -0.1 else 'stable',
        }
        
        self.results[pid_name] = result
        logger.info(f"✓ {label} Statistical Analysis: {len(anomaly_indices)} anomalies (z>{threshold})")
        return result

    def analyze_multivariate(self, sensors: List[str] = ['engine_speed', 'coolant_temp', 'calculated_load'], 
                            seq_len: int = 20, epochs: int = 50, threshold: float = 3.0):
        """Train a single multivariate LSTM across multiple sensors."""
        logger.info(f"Running multivariate analysis on {sensors}...")
        
        # Gather data for all requested sensors
        sensor_dfs = []
        valid_sensors = []
        for pid in sensors:
            data = self.pid_analyzer.get_pid_data(pid)
            if not data.empty and len(data) > 50:
                sensor_dfs.append(data.rename(pid))
                valid_sensors.append(pid)
        
        if not sensor_dfs:
            logger.warning("No sufficient sensor data for multivariate analysis")
            return
            
        # Align all sensors by joining
        multivariate_df = pd.concat(sensor_dfs, axis=1).dropna()
        
        if len(multivariate_df) < 200:
            logger.info("Insufficient aligned data for multivariate LSTM, falling back to univariate statistical analysis")
            for pid in valid_sensors:
                self._run_generic_analysis(pid, pid.upper(), seq_len=seq_len, threshold=threshold)
            return

        predictor = LSTMPredictor(sequence_length=seq_len)
        if predictor.train(multivariate_df, epochs=epochs, verbose=0):
            anomalies = predictor.detect_anomalies(multivariate_df, threshold=threshold)
            
            result = {
                'method': 'multivariate_lstm',
                'sensors': valid_sensors,
                'anomaly_count': len(anomalies),
                'anomaly_percentage': (len(anomalies) / len(multivariate_df)) * 100,
                'anomaly_indices': anomalies,
            }
            
            # Predict next values
            recent = multivariate_df.tail(seq_len).values
            next_vals = predictor.predict_next(recent)
            if next_vals is not None:
                result['predicted_next'] = dict(zip(valid_sensors, next_vals.tolist()))
            
            self.predictors['multivariate'] = predictor
            self.results['multivariate'] = result
            logger.info(f"✓ Multivariate LSTM Analysis: {len(anomalies)} anomalies detected")

    def analyze_misfire_patterns(self):
        """Predict misfire patterns"""
        data = self.pid_analyzer.get_pid_data('misfire_count')
        if data.empty:
            logger.info("No misfire data found")
            return
            
        data = data.fillna(0)
        if data.sum() > 0:
            # For misfires, we usually have very sparse data, so statistical is often better
            # but we'll try univariate LSTM if enough points
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

    # Run multivariate analysis as prioritized in review
    analyzer.analyze_multivariate()
    
    # Also run misfire patterns specifically as it's critical
    analyzer.analyze_misfire_patterns()

    # Generate report
    analyzer.generate_report()

    return analyzer
