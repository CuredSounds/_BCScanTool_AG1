# Project Reorganization Plan

## New Folder Structure

```
_BCScanTool-v1/
├── src/                          # Main source code
│   ├── core/                     # Core analysis modules
│   │   ├── __init__.py
│   │   ├── obd2_analyzer.py      # Main orchestrator (renamed from obd2.py)
│   │   ├── diagnostic_engine.py
│   │   ├── predictive_analytics.py
│   │   └── pid_analyzer.py
│   │
│   ├── ml_models/                # Machine learning models
│   │   ├── __init__.py
│   │   ├── lstm_predictor.py
│   │   ├── autoencoder_anomaly.py
│   │   └── vehicle_baselines.py
│   │
│   ├── utils/                    # Utilities and helpers
│   │   ├── __init__.py
│   │   ├── repair_cost_estimator.py
│   │   └── x431_converter.py     # From x431-to-csv
│   │
│   └── gui/                      # GUI application
│       ├── __init__.py
│       ├── dashboard.py          # Main GUI dashboard
│       └── widgets.py            # Custom widgets
│
├── scripts/                      # Executable scripts
│   ├── launch.py                 # Main launch script
│   ├── analyze_vehicle.py        # Quick analysis script
│   └── export_data.py            # Data export utilities
│
├── data/                         # Data storage
│   ├── raw/                      # Raw scan files
│   ├── processed/                # Processed data
│   ├── models/                   # Saved ML models
│   └── exports/                  # Exported reports
│
├── docs/                         # Documentation
│   ├── README.md
│   ├── USER_GUIDE.md
│   ├── API_REFERENCE.md
│   ├── RESEARCH_FINDINGS.md
│   ├── PHASE_3_ROADMAP.md
│   └── archived/                 # Old documentation
│
├── tests/                        # Unit tests (future)
│   └── __init__.py
│
├── _archive_old_files/           # Obsolete/duplicate files
│   ├── old_scripts/
│   ├── duplicate_docs/
│   └── deprecated/
│
├── requirements.txt              # Python dependencies
├── launch.sh                     # Shell launch script
├── README.md                     # Main README
└── .gitignore

```

## Files to Move

### TO: src/core/
- obd2.py → src/core/obd2_analyzer.py
- diagnostic_engine.py → src/core/diagnostic_engine.py
- predictive_analytics.py → src/core/predictive_analytics.py
- pid_analyzer.py → src/core/pid_analyzer.py

### TO: src/ml_models/
- lstm_predictor.py → src/ml_models/lstm_predictor.py
- autoencoder_anomaly.py → src/ml_models/autoencoder_anomaly.py
- vehicle_baselines.py → src/ml_models/vehicle_baselines.py

### TO: src/utils/
- repair_cost_estimator.py → src/utils/repair_cost_estimator.py
- x431-to-csv/* → src/utils/x431_converter/

### TO: _archive_old_files/
- _BCScanTool.py (old version)
- python/*.py (duplicate scripts)
- tacoma_diagnostics/*.py (duplicate)
- Equipment Inventory*.md
- chat history.md

### TO: docs/
- RESEARCH_FINDINGS.md
- PHASE_3_ROADMAP.md
- IMPLEMENTATION_COMPLETE.md
- ANALYSIS_SUMMARY.md

### TO: docs/archived/
- README_DATA.md
- docs/FIELD_TEST_CHECKLIST.md (if not current)
- docs/MATLAB_INTEGRATION_GUIDE.md (if not current)
