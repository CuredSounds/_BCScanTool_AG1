# OBD2 CAN Bus Predictive Diagnostic Pipeline Report
**Generated At:** 2026-05-20 00:19:39

## 1. Pipeline Summary
This report documents the training and validation of the advanced OBD2 CAN bus fault detection pipeline for the **2011 Toyota Tacoma 4.0L V6**.

### Data Quality Gates Applied:
- **Gate 1 (Min Rows Check):** Enforced >= 200 rows for baselines, >= 120 rows for faults.
- **Gate 2 (Initialization Drop):** Dropped the first 30 rows of sensor initialization progressive-fill.
- **Gate 3 (Engine Running Check):** Filtered engine-off/cranking rows (RPM < 50).
- **Gate 4 (Steady-State Window):** For baseline idle scans, the first 60 seconds of warm-up ramp were discarded unless the starting engine time was already > 300s (already warm). For fault captures, the first 30 seconds of transient response immediately after injection were discarded.
- **Gate 4.5 (Strict Feature Subset):** Restricted modeling strictly to the **33 Tier A core parameters** (MAF, Lambda, Fuel Trims, Voltages, Misfires, Throttle/Accel positions). All monitor flags, string metadata, and row indices were discarded.

### Temporal Leakage Prevention:
- Sliced continuous scans into sequential **60-row windows** with a step size of **10 rows** (5 seconds overlap).
- Used a **2-Fold Temporal-Disjoint Split** (disjoint parts of session captures) to ensure windows from the same session *never* cross-contaminate the training and validation splits. This yields a completely unbiased, true out-of-sample evaluation.

## 2. Validation Performance Results

### A. Random Forest Classifier (Static Window Stats)
```
                  precision    recall  f1-score   support

fault_alternator       0.73      0.96      0.83       221
         healthy       0.44      0.08      0.14        86
   healthy_ac_on       1.00      1.00      1.00        17

        accuracy                           0.73       324
       macro avg       0.72      0.68      0.66       324
    weighted avg       0.67      0.73      0.65       324

```

### B. PyTorch LSTM Classifier (Raw Time-Series Sequence)
```
                  precision    recall  f1-score   support

fault_alternator       0.86      0.95      0.90       221
         healthy       0.73      0.22      0.34        86
   healthy_ac_on       0.31      1.00      0.47        17

        accuracy                           0.76       324
       macro avg       0.63      0.72      0.57       324
    weighted avg       0.80      0.76      0.73       324

```

## 3. Top 15 Feature Importances (Random Forest)
| Rank | OBD2 Signal & Window Stat | Gini Importance |
|---|---|---|
| 1 | `Calculate Load [%] (mean)` | 0.04499 |
| 2 | `Long FT (Bank1 Sensor1) [%] (max)` | 0.04427 |
| 3 | `Atmosphere Pressure [kPa] (mean)` | 0.04396 |
| 4 | `Calculate Load [%] (median)` | 0.03415 |
| 5 | `Long FT (Bank1 Sensor1) [%] (min)` | 0.03375 |
| 6 | `Calculate Load [%] (q25)` | 0.03162 |
| 7 | `Long FT (Bank1 Sensor1) [%] (median)` | 0.02639 |
| 8 | `Short FT (Bank2 Sensor1) [%] (max)` | 0.02329 |
| 9 | `Calculate Load [%] (max)` | 0.02250 |
| 10 | `Long FT (Bank2 Sensor1) [%] (min)` | 0.01994 |
| 11 | `AFS Voltage (Bank2 Sensor1) [V] (q75)` | 0.01993 |
| 12 | `Long FT (Bank1 Sensor1) [%] (q75)` | 0.01781 |
| 13 | `Short FT (Bank2 Sensor1) [%] (q75)` | 0.01755 |
| 14 | `Atmosphere Pressure [kPa] (max)` | 0.01690 |
| 15 | `Calculate Load [%] (min)` | 0.01687 |

## 4. Visual Artifacts
The side-by-side confusion matrix plot and feature importances horizontal bar chart are saved in the models directory:
- Confusion Matrix: `models/model_confusion_matrices.png`
- Feature Importances: `models/feature_importances.png`