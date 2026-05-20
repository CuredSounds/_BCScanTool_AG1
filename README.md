# BCScanTool (AG1)

Advanced vehicle diagnostic platform for ingesting, analyzing, and visualizing Launch X431 scan tool data.

## Features

- **Data Ingestion**: Support for `.x431` and `.csv` exports.
- **Predictive Analytics**: Trend-based degradation detection and failure forecasting.
- **Machine Learning**: 
  - Supervised Random Forest for condition classification.
  - Unsupervised Isolation Forest for anomaly detection.
  - LSTM (Deep Learning) for time-series sensor forecasting.
  - Autoencoder for multivariate signal anomaly detection.
- **FastAPI Backend**: Secure RESTful API for diagnostic processing.
- **Streamlit Dashboard**: Premium visualization of vehicle health and topology.
- **Cloud Backup**: Automated sync to Google Drive.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -e .
   ```

2. **Configure environment**:
   Create a `.env` file or set environment variables:
   - `BCSCAN_API_KEY`: Secret key for API authentication (default provided).
   - `BCSCAN_LOG_LEVEL`: Logging level (INFO/DEBUG).

3. **Start the API**:
   ```bash
   python src/api/main.py
   ```

4. **Start the Dashboard**:
   ```bash
   streamlit run src/gui/streamlit_app.py
   ```

## Architecture

- `src/api`: FastAPI endpoints and model serving.
- `src/core`: Core diagnostic engine and data processing logic.
- `src/ml_models`: Training pipelines and inference models.
- `src/gui`: Streamlit dashboard.

## Security

The API is secured via `X-API-Key` header. All uploaded files and chat inputs are sanitized.
