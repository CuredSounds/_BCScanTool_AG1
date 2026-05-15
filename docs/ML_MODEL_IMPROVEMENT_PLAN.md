# ML Model Improvement & Validation Plan
**BCScanTool v2.0 - Iterative Model Training Protocol**

## 🎯 Objective
Systematically improve ML model accuracy through controlled fault injection, proper labeling, and consistent data collection to enable predictive maintenance and reliable anomaly detection.

---

## Phase 1: Controlled Fault Injection Testing 🧪
**Goal:** Generate high-quality labeled "fault" data for model training

### Safety Precautions ⚠️
- Perform tests in safe, controlled environment (driveway/garage, not on road)
- Engine running at idle or parked for most tests
- Have tools ready to quickly reconnect sensors
- Monitor engine conditions - don't let it run too lean/rich for extended periods
- Keep scan sessions brief (2-5 minutes per fault condition)

### Test 1: MAF Sensor Disconnect
**Objective:** Capture air flow sensor fault signature

```
Procedure:
1. Baseline scan - Run 3-minute scan with all systems normal
   - Save as: TOYOTA_[DATE]_baseline_before_maf_test.csv

2. Disconnect MAF sensor
   - Locate MAF sensor (between air filter and throttle body)
   - Unplug electrical connector

3. Start engine and let stabilize (30 seconds)

4. Capture fault scan (2-3 minutes)
   - Use same scan profile as baseline
   - Save as: TOYOTA_[DATE]_maf_disconnected.csv
   - Note symptoms: rough idle, check engine light, etc.

5. Reconnect MAF sensor

6. Clear codes and run verification scan
   - Save as: TOYOTA_[DATE]_maf_reconnected_cleared.csv

Label: maf_fault
Expected: High anomaly detection, fuel trim deviations, lean codes
```

### Test 2: O2 Sensor Disconnect
**Objective:** Capture oxygen sensor fault signature

```
Procedure:
1. Baseline scan (3 minutes, normal operation)
   - Save as: TOYOTA_[DATE]_baseline_before_o2_test.csv

2. Disconnect Bank 1 Sensor 1 O2 sensor
   - Front O2 sensor (before catalytic converter)
   - Unplug electrical connector

3. Engine running, capture scan (2-3 minutes)
   - Save as: TOYOTA_[DATE]_o2_b1s1_disconnected.csv
   - Note: Check engine light, may run rich

4. Reconnect O2 sensor

5. Clear codes and verify
   - Save as: TOYOTA_[DATE]_o2_reconnected_cleared.csv

Label: o2_fault_b1s1
Expected: Fixed voltage readings, fuel trim compensation
```

### Test 3: Vacuum Leak Simulation
**Objective:** Capture intake air leak condition

```
Procedure:
1. Baseline scan (3 minutes)
   - Save as: TOYOTA_[DATE]_baseline_before_vacuum_test.csv

2. Induce controlled vacuum leak
   - Option A: Disconnect PCV valve hose
   - Option B: Disconnect brake booster vacuum line
   - DO NOT create massive leak - small controlled leak only

3. Capture scan (2-3 minutes)
   - Save as: TOYOTA_[DATE]_vacuum_leak.csv
   - Note: High idle, rough running, lean condition

4. Reconnect vacuum line

5. Verify restoration
   - Save as: TOYOTA_[DATE]_vacuum_restored.csv

Label: vacuum_leak
Expected: High fuel trims (positive LTFT), lean codes, unstable idle
```

### Test 4: Misfire Simulation
**Objective:** Capture cylinder misfire signature

```
Procedure:
1. Baseline scan (3 minutes)
   - Save as: TOYOTA_[DATE]_baseline_before_misfire_test.csv

2. Induce misfire (CHOOSE ONE):
   - Option A: Disconnect single ignition coil connector (Cylinder 1)
   - Option B: Disconnect single fuel injector (Cylinder 1)
   - DO NOT run for extended period - brief test only

3. Capture scan (1-2 minutes MAX)
   - Save as: TOYOTA_[DATE]_misfire_cyl1.csv
   - Note: Rough idle, flashing CEL, power loss

4. Immediately reconnect component

5. Verify restoration
   - Save as: TOYOTA_[DATE]_misfire_cleared.csv

Label: misfire_cyl1
Expected: Misfire counter increments, rough running, P030X codes
```

### Data Organization After Each Test:
```bash
# Move to organized fault data directory
mkdir -p data/raw/controlled_faults/maf_fault/
mkdir -p data/raw/controlled_faults/o2_fault/
mkdir -p data/raw/controlled_faults/vacuum_leak/
mkdir -p data/raw/controlled_faults/misfire/

# Copy files to appropriate directories with proper labels
```

---

## Phase 2: CAN Bus Testing 🔌
**Goal:** Validate model with CAN bus fault injection

### Equipment Needed:
- CAN bus interface (ELM327, CANable, Kvaser, etc.)
- Python-CAN or similar library
- Vehicle CAN bus pinout (OBD-II pins 6 & 14)

### Test 1: Known Fault Code Injection
```python
# Example: Inject P0101 (MAF range/performance)
# This tests if model detects the fault signature

Procedure:
1. Baseline scan
2. Use CAN tool to inject fault code
3. Capture scan showing injected fault
4. Compare model prediction vs. actual fault
5. Clear and verify

Label: can_injected_p0101
```

### Test 2: CAN Message Fuzzing
```python
# Randomly corrupt CAN messages
# Tests model robustness to data corruption

Procedure:
1. Monitor normal CAN traffic
2. Inject corrupted frames (bit flips, invalid data)
3. Capture diagnostic response
4. Validate model anomaly detection

Label: can_fuzz_test
```

### Test 3: Sensor Spoofing
```python
# Send fake sensor values via CAN
# Example: Report 300°F coolant temp (obviously wrong)

Procedure:
1. Identify CAN ID for coolant temp
2. Transmit fake high value
3. Capture scan showing spoofed data
4. Validate model flags anomaly

Label: can_spoof_coolant
```

---

## Phase 3: Session Labeling 📝
**Goal:** Categorize existing 99 unlabeled Toyota sessions

### Labeling Strategy:
Review each unlabeled session and categorize by:

1. **Driving Condition:**
   - `idle_warm` - Engine at operating temp, parked
   - `idle_cold` - Cold start, warming up
   - `highway_cruise` - Steady speed, light load
   - `city_driving` - Stop-and-go, variable load
   - `acceleration` - Full throttle, high load
   - `deceleration` - Engine braking, overrun

2. **Known Issues at Time:**
   - `good` - No known issues, baseline
   - `brake_issue` - Brake system diagnostic
   - `ac_issue` - A/C not working properly
   - `noise_investigation` - Strange sounds
   - `check_engine_light` - CEL on, investigating

3. **System Focus:**
   - `engine_focus` - Primary engine parameters
   - `transmission_focus` - ATF temp, shift patterns
   - `emissions_focus` - Catalyst, O2 sensors
   - `full_system` - All systems scanned

### Labeling Tool:
```bash
# Use filename dates and your memory/notes to assign labels
# Update CSV filenames with labels:
# TOYOTA_20251103_idle_warm_good.csv
# TOYOTA_20251127_highway_cruise_good.csv
```

---

## Phase 4: Standardized Health Checks 📊
**Goal:** Establish consistent baseline for trend detection

### Weekly Health Check Protocol:

**Standardized Scan Profile:**
1. **Pre-conditions:**
   - Engine at full operating temperature (195-210°F)
   - All accessories OFF (A/C, radio, lights)
   - Transmission in Park
   - Level surface

2. **Scan Duration:** 5 minutes minimum

3. **Scan Phases:**
   - Minutes 0-2: Idle
   - Minutes 2-3: Rev to 2000 RPM, hold steady
   - Minutes 3-4: Return to idle
   - Minutes 4-5: Idle with A/C ON

4. **Parameters to Monitor:**
   - All fuel trims (STFT & LTFT, both banks)
   - Coolant temp
   - Intake air temp
   - MAF sensor readings
   - O2 sensor voltages
   - Misfire counters (all cylinders)
   - Throttle position
   - Engine load
   - RPM
   - Battery voltage

5. **Save As:**
   ```
   TOYOTA_[DATE]_weekly_health_check.csv
   VOLVO_[DATE]_weekly_health_check.csv
   ```

6. **Label:** `weekly_baseline`

### Monthly Deep Scan:
- Full system scan (all modules)
- Clear all codes first
- Run scan, then check for any stored codes
- Save as: `TOYOTA_[DATE]_monthly_deep_scan.csv`

---

## Phase 5: Baseline Condition Library 📚
**Goal:** Create comprehensive baseline database

### Conditions to Capture:

1. **Cold Start Sequence**
   ```
   - Engine off overnight (cold)
   - Start engine, capture first 5 minutes
   - Monitor warmup behavior
   Label: cold_start_baseline
   ```

2. **Highway Cruise**
   ```
   - Steady 65 mph for 5+ minutes
   - Light load, stable conditions
   Label: highway_cruise_baseline
   ```

3. **City Driving**
   ```
   - Stop-and-go traffic
   - Multiple acceleration/deceleration cycles
   Label: city_driving_baseline
   ```

4. **Full Load Acceleration**
   ```
   - Safe location (on-ramp, empty road)
   - Full throttle acceleration 0-60
   - Capture high load conditions
   Label: full_load_baseline
   ```

5. **Engine Braking**
   ```
   - Downhill with throttle closed
   - Deceleration fuel cutoff active
   Label: decel_baseline
   ```

6. **A/C Load**
   ```
   - A/C on max, compressor running
   - Capture electrical load impact
   Label: ac_load_baseline
   ```

---

## Phase 6: Model Retraining 🔄
**Goal:** Iteratively improve model accuracy

### Retraining Workflow:

1. **After Each Fault Test:**
   ```bash
   # Add new labeled data
   cp data/raw/controlled_faults/*/*.csv data/raw/labeled/

   # Retrain model
   python python/deep_vehicle_analysis.py

   # Generate new reports
   python python/generate_vehicle_reports.py

   # Compare before/after accuracy
   ```

2. **Validation:**
   ```python
   # Test model on known faults
   # Calculate detection rate:
   # - True Positives: Correctly identified faults
   # - False Positives: Normal conditions flagged as faults
   # - False Negatives: Missed actual faults
   # - True Negatives: Correctly identified normal

   # Target: >95% detection rate, <5% false positive rate
   ```

3. **Model Versioning:**
   ```bash
   # Save model versions
   models/
   ├── toyota_anomaly_model_v1.joblib  # Initial
   ├── toyota_anomaly_model_v2.joblib  # After fault tests
   ├── toyota_anomaly_model_v3.joblib  # After CAN tests
   └── toyota_anomaly_model_final.joblib
   ```

---

## Phase 7: Time-Series Trend Analysis 📈
**Goal:** Detect parameter drift before failure

### Analysis Methods:

1. **Track Fuel Trim Drift:**
   ```python
   # Plot LTFT over weeks/months
   # Increasing positive LTFT → vacuum leak developing
   # Increasing negative LTFT → rich condition, possible bad MAF
   ```

2. **Misfire Counter Trends:**
   ```python
   # Zero misfires → healthy
   # Gradual increase → deteriorating ignition/injector
   # Sudden spike → immediate failure
   ```

3. **Coolant Temp Patterns:**
   ```python
   # Consistent warmup curve → healthy
   # Slow warmup → thermostat issue
   # Overheating trends → cooling system problem
   ```

4. **O2 Sensor Response:**
   ```python
   # Fast switching (0.1-0.9V) → healthy sensor
   # Lazy response → aging sensor
   # Fixed voltage → dead sensor
   ```

### Trend Dashboard:
Create automated trend plots from weekly health checks:
```bash
python python/generate_trend_dashboard.py
# Outputs: data/reports/trend_dashboard.html
```

---

## Success Metrics 🎯

### Short-term (1-2 weeks):
- ✅ Complete all 4 controlled fault injection tests
- ✅ Label at least 50% of unlabeled sessions
- ✅ Establish standardized scan profile
- ✅ Collect first 2 weekly baselines

### Medium-term (1 month):
- ✅ Complete CAN bus testing suite
- ✅ Label 100% of unlabeled sessions
- ✅ Collect all baseline condition types
- ✅ Retrain model with 10+ fault conditions
- ✅ Achieve >90% fault detection rate

### Long-term (3 months):
- ✅ 12+ weekly health check scans collected
- ✅ Trend analysis operational
- ✅ Predictive maintenance alerts functional
- ✅ Model can detect faults before CEL illuminates
- ✅ Research paper/thesis draft complete

---

## Data Management 📁

### Directory Structure:
```
data/
├── raw/
│   ├── controlled_faults/
│   │   ├── maf_fault/
│   │   ├── o2_fault/
│   │   ├── vacuum_leak/
│   │   └── misfire/
│   ├── baseline_conditions/
│   │   ├── cold_start/
│   │   ├── highway_cruise/
│   │   ├── city_driving/
│   │   └── full_load/
│   ├── weekly_health_checks/
│   │   ├── 2026-01-13_toyota.csv
│   │   ├── 2026-01-20_toyota.csv
│   │   └── ...
│   └── can_bus_tests/
├── processed/
│   └── models/
│       ├── v1/
│       ├── v2/
│       └── v3/
└── reports/
    ├── weekly_trends/
    └── fault_detection_performance/
```

### Backup Strategy:
```bash
# Weekly backup
rsync -av data/ ~/Backups/BCScanTool_$(date +%Y%m%d)/

# Git commits after each major test
git add data/raw/controlled_faults/
git commit -m "Add MAF fault test data - 2026-01-13"
```

---

## Next Immediate Actions ⚡

**This Week:**
1. ☐ Read through safety precautions
2. ☐ Gather tools for sensor disconnect tests
3. ☐ Perform Test 1 (MAF disconnect)
4. ☐ Retrain model with new data
5. ☐ Validate detection capability

**Start here:**
```bash
# Create fault data directories
mkdir -p data/raw/controlled_faults/{maf_fault,o2_fault,vacuum_leak,misfire}

# Prepare scan profile
# Open Launch X431, configure scan for all engine parameters

# Ready to begin Test 1!
```

---

**Pro Tips:**
- 📸 **Document everything:** Take photos/videos of each test setup
- 📝 **Keep log:** Note exact time, conditions, observations
- 🔍 **Start small:** Do one test well rather than rush through all
- 🛡️ **Safety first:** Never compromise vehicle safety for data
- 📊 **Immediate analysis:** Review scan data right after each test

**Remember:** The goal is **quality labeled data**, not quantity. One perfect fault signature is worth 100 ambiguous scans.

---

*Ready to build the most robust automotive ML model possible!* 🚀
