# BCScanTool — Organized Dataset Capture Plan

## 2011 Toyota Tacoma 4.0L V6 (VIN: 5TFUU4EN2BX005907)

**Purpose:** Build a production-quality labeled dataset for training fault-detection ML models.  
**Status:** \~110 organic scans captured (unlabeled). Zero controlled fault tests executed.  
**Scanner:** Launch X431 PRO3 V+ Elite (\~200 parameters per DataStream capture)

---

## The Core Problem with Your Current Data

You have \~110 scans but your ML pipeline can't use them effectively because:

1. **No labels.** Your `training_pipeline.py` infers labels from filenames (`'good' in filename`). Only one file has "good" in the name, one has "brake". Everything else is `unknown`.  
2. **No operating condition metadata.** You don't know if a scan was cold start, idle, highway, or under load. The same RPM reading means very different things at each.  
3. **Inconsistent parameter coverage.** The X431 progressively fills columns as the ECU streams them. Early rows in each CSV are mostly zeros while sensors initialize. Row 1 is useless; row 200 is gold.  
4. **No triplet structure.** ML anomaly detection needs baseline → fault → cleared triplets to learn what "deviation from normal" looks like.

This plan fixes all four.

---

## Part 1: Retroactive Labeling (Do First — 2 Hours)

Before capturing anything new, label what you already have. Create a single metadata file.

### File: `data/scan_manifest.csv`

| filename | date | condition | operating\_mode | engine\_temp | notes |
| :---- | :---- | :---- | :---- | :---- | :---- |
| ...20251024151339good\_clean.csv | 2024-10-24 | healthy | idle | warm | Labeled "good" by filename |
| ...20251022200941brake\_clean.csv | 2024-10-22 | unknown | idle | warm | Brake test? Clarify |
| ...20251025160401 alternation noise\_clean.csv | 2024-10-25 | fault\_alternator | idle | warm | Real alternator issue |
| ...20251103172406 ac\_clean.csv | 2024-11-03 | healthy\_ac\_on | idle\_ac | warm | AC load test |
| ...20260107134353 startup\_clean.csv | 2026-01-07 | healthy | cold\_start | cold | Startup capture |

**For every existing CSV**, fill in:

- **condition**: `healthy`, `fault_alternator`, `fault_unknown`, `unknown`, `post_repair`  
- **operating\_mode**: `cold_start`, `idle_warm`, `idle_cold`, `drive_city`, `drive_highway`, `idle_ac`, `rev_hold_2k`, `rev_hold_3k`  
- **engine\_temp**: `cold` (\<160°F), `warming` (160-190°F), `warm` (190-210°F), `hot` (\>210°F)  
- **notes**: Anything you remember about that day

This is tedious but it instantly turns 110 unlabeled scans into a usable dataset. You already know which scans were during the alternator issue. Label them.

---

## Part 2: Baseline Capture Protocol (The Foundation)

Your existing methodology says "3-minute baseline." That's too short and too narrow. A proper baseline needs to cover the **operating envelope** of the vehicle — the full range of normal behavior across different conditions.

### The 7-Condition Baseline Matrix

Capture one scan for each. Do them all on the same day if possible (weather and conditions consistent).

| \# | Condition | How | Duration | Target Rows | Key Parameters to Watch |
| :---- | :---- | :---- | :---- | :---- | :---- |
| B1 | Cold idle | Start engine cold. Don't touch anything. | 5 min | \~600 rows | Coolant temp ramp, STFT swing, O2 sensor warmup, VVT initialization |
| B2 | Warm idle | Engine fully warm (\>195°F). No AC. No loads. | 5 min | \~600 rows | Stable RPM, converged fuel trims, O2 switching |
| B3 | Warm idle \+ AC | AC on max. All else off. | 3 min | \~360 rows | RPM compensation, electrical load, IAC response |
| B4 | Warm idle \+ electrical load | Headlights, blower, rear defrost all on. | 3 min | \~360 rows | Battery voltage, alternator response, RPM stability |
| B5 | 2000 RPM hold | Hold throttle at steady 2000 RPM in park. | 3 min | \~360 rows | MAF at load, fuel trims under load, spark advance |
| B6 | Drive — city (20-40 mph) | Normal suburban driving. | 5 min | \~600 rows | Throttle response, transmission shifts, speed/load correlation |
| B7 | Drive — highway (55-70 mph) | Steady highway cruise. | 5 min | \~600 rows | High MAF, cruise fuel trims, catalyst temps, VVT at cruise |

### Naming Convention

TACOMA\_YYYYMMDD\_HHMMSS\_B1\_cold\_idle\_baseline.csv

TACOMA\_YYYYMMDD\_HHMMSS\_B2\_warm\_idle\_baseline.csv

TACOMA\_YYYYMMDD\_HHMMSS\_B3\_warm\_idle\_ac\_baseline.csv

...

### Why 7 Conditions Matter

A cold-start scan shows fuel trims at \+25% and O2 sensors reading 0V — that's normal for open-loop warmup but looks identical to a dead O2 sensor if your model only trained on warm idle. Your model needs to learn: "these parameters are normal *for this condition*."

### Repeat Schedule

Capture the full B1–B7 matrix:

- **Once now** (initial baseline)  
- **Once per month** (track seasonal drift — summer vs. winter ambient temps change everything)  
- **After any repair** (new baseline post-intervention)

---

## Part 3: Controlled Fault Capture Protocol

Your methodology doc has 35+ tests defined. Here's how to prioritize and structure the actual execution.

### Tier 1: High-Value, Low-Risk (Do These First)

These give you the most ML training value with the least risk to the truck.

| Priority | Test | Risk | ML Value | Why First |
| :---- | :---- | :---- | :---- | :---- |
| 1 | MAF disconnect | 🟢 | VERY HIGH | Easiest test, clearest signature, most common real-world failure |
| 2 | O2 B1S1 disconnect | 🟢 | VERY HIGH | Affects closed-loop fuel control — massive parameter shift |
| 3 | PCV hose disconnect (vacuum leak) | 🟢 | VERY HIGH | Most common real-world issue, affects 10+ parameters |
| 4 | Coolant temp sensor disconnect | 🟢 | HIGH | Changes entire fuel/timing strategy |
| 5 | IAT sensor disconnect | 🟢 | MODERATE | Quick, safe, clean signature |
| 6 | O2 B2S1 disconnect | 🟢 | HIGH | Compare bank-to-bank fault patterns |

### Tier 2: Medium-Value, Medium-Risk (Do After Tier 1 Validates Pipeline)

| Priority | Test | Risk | ML Value |
| :---- | :---- | :---- | :---- |
| 7 | TPS disconnect | 🟡 | HIGH |
| 8 | Single coil disconnect (cyl 1\) | 🔴 | VERY HIGH |
| 9 | Single injector disconnect (cyl 1\) | 🔴 | VERY HIGH |
| 10 | Fuel pressure regulator vacuum disconnect | 🟢 | MODERATE |
| 11 | VVT solenoid disconnect | 🟢 | MODERATE |
| 12 | EGR valve disconnect | 🟢 | MODERATE |

### Tier 3: Multi-Fault (Do Only After Single-Fault Models Work)

| Priority | Test | Risk | ML Value |
| :---- | :---- | :---- | :---- |
| 13 | MAF \+ O2 together | 🟡 | VERY HIGH |
| 14 | Vacuum leak \+ coil disconnect | 🔴 | VERY HIGH |
| 15 | O2 B1S1 \+ O2 B2S1 together | 🟢 | HIGH |

### The Triplet Protocol (For Every Single Test)

Each fault test produces **exactly 3 files** plus a metadata record:

Phase 1: BASELINE     → 3-5 min, engine warm, no faults

         File: TACOMA\_YYYYMMDD\_HHMMSS\_T01\_maf\_disconnect\_baseline.csv

Phase 2: FAULT        → Introduce fault, wait 30s to stabilize, then capture 2-3 min

         File: TACOMA\_YYYYMMDD\_HHMMSS\_T01\_maf\_disconnect\_fault.csv

Phase 3: CLEARED      → Reconnect, clear DTCs, capture 2 min recovery

         File: TACOMA\_YYYYMMDD\_HHMMSS\_T01\_maf\_disconnect\_cleared.csv

**Critical rule:** The baseline for each test should be captured *immediately before* the fault, on the same session, same engine temperature. Don't use yesterday's baseline for today's fault — ambient temp, engine condition, and fuel trim adaptations all change.

### Per-Test Metadata Record

After every test, add a row to `data/test_executions.csv`:

| test\_id | date | time | ambient\_temp\_f | engine\_temp\_f | mileage | duration\_fault\_s | dtcs\_triggered | symptoms\_observed | baseline\_file | fault\_file | cleared\_file | operator\_notes |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| T01 | 2026-05-20 | 14:30 | 78 | 198 | 142350 | 150 | P0101,P0102 | High idle, rough, CEL | ...baseline.csv | ...fault.csv | ...cleared.csv | Clean disconnect, immediate response |

---

## Part 4: What to Capture (Parameter Strategy)

You have \~200 parameters available. Not all are useful for ML.

### Parameter Tiers

**Tier A — Always capture, core ML features (25 parameters):** These are the parameters that actually change during faults and carry diagnostic signal.

Engine Speed \[rpm\]

Calculate Load \[%\]

Coolant Temp \[degree C\]

Intake Air \[degree C\]

MAF \[gm/s\]

Atmosphere Pressure \[kPa\]

AF Lambda (Bank1 Sensor1)

AF Lambda (Bank2 Sensor1)

AFS Current (Bank1 Sensor1) \[mA\]

AFS Current (Bank2 Sensor1) \[mA\]

O2S B1S2 \[V\]

O2S B2S2 \[V\]

Short FT (Bank1 Sensor1) \[%\]

Short FT (Bank2 Sensor1) \[%\]

Long FT (Bank1 Sensor1) \[%\]

Long FT (Bank2 Sensor1) \[%\]

IGN Advance \[deg\]

All Cylinders Misfire Count

Cylinder Count1-6 Misfire Count

Vehicle Speed \[km/h\]

Throttle Sensor Position \[%\]

Accelerator Position \[%\]

Battery Voltage \[V\]

Engine Run Time \[s\]

**Tier B — Capture when available, secondary features (20 parameters):**

Catalyst Temp (Bank1/2 Sensor1) \[degree C\]

VVT Change Angle Count1/2 \[degree FR\]

VVT OCV Duty Count1/2 \[%\]

Knock Feedback Value \[degree CA\]

Knock Correct Learn Value \[degree CA\]

Injector(Port) \[us\]

Injection Volum (Cylinder1) \[ml\]

EVAP (Purge) VSV \[%\]

FC TAU

Fuel Cut Condition

Throttle Motor Current \[A\]

Throttle Motor DUTY \[%\]

MISFIRE LOAD \[g/rev\]

MISFIRE RPM \[rpm\]

SPD (NT) \[rpm\]

A/T Oil Temperature 1/2 \[degree C\]

**Tier C — Metadata only, don't feed to ML:**

Monitor status flags (Compl/Unable/Not Avl)

MIL status

Count Codes

Distance from DTC Cleared

Model Code, Engine Type, Destination (static)

### Why This Matters

Your autoencoder is currently fed "the first 10 numeric columns" — which might include Row number, monitor completion flags, and static metadata. That's pure noise. Define an explicit feature list and stick to it.

---

## Part 5: Data Quality Gates

Before any scan enters the training pipeline, it must pass these checks.

### Gate 1: Minimum Row Count

- Baseline scans: ≥300 rows (about 2.5 minutes at 2 Hz)  
- Fault scans: ≥120 rows (about 1 minute)  
- Reject anything shorter

### Gate 2: Sensor Initialization

- **Drop the first 30 rows of every scan.** The X431 progressively fills parameters as ECUs respond. Early rows are mostly zeros — not real data, just "haven't heard back yet." Your current pipeline treats these zeros as real sensor readings.

### Gate 3: Engine Running Verification

- RPM \> 0 for engine-running tests  
- RPM \= 0 for key-on-engine-off tests (if you do those)  
- Reject scans where RPM drops to zero mid-capture (engine stalled \= corrupted data)

### Gate 4: Steady-State Window

- For idle baselines: discard the first 60 seconds of warm-up ramp  
- For fault captures: discard the first 30 seconds after fault introduction (transient response)  
- The ML model should learn the *settled* fault signature, not the transition

### Gate 5: Metadata Complete

- Every file in `scan_manifest.csv` or `test_executions.csv`  
- No orphaned files

---

## Part 6: Dataset Directory Structure

Reorganize your data directory to separate concerns:

data/

├── raw/                          \# Untouched scanner output (.x431, .pdf)

│   └── Toyota/Tacoma/

├── csv/                          \# Converted CSVs (all scans, converted from .x431)

│   └── Toyota/Tacoma/

├── labeled/                      \# The ML-ready dataset

│   ├── baselines/                \# B1-B7 baseline captures

│   │   ├── TACOMA\_20260520\_B1\_cold\_idle.csv

│   │   ├── TACOMA\_20260520\_B2\_warm\_idle.csv

│   │   └── ...

│   ├── faults/                   \# Controlled fault captures (triplets)

│   │   ├── T01\_maf\_disconnect/

│   │   │   ├── baseline.csv

│   │   │   ├── fault.csv

│   │   │   └── cleared.csv

│   │   ├── T02\_o2\_b1s1\_disconnect/

│   │   │   ├── baseline.csv

│   │   │   ├── fault.csv

│   │   │   └── cleared.csv

│   │   └── ...

│   ├── organic/                  \# Your existing 110 scans, labeled retroactively

│   │   ├── healthy/

│   │   ├── fault\_alternator/

│   │   └── unknown/

│   └── multi\_fault/              \# Combined fault scenarios

│       └── T13\_maf\_plus\_o2/

├── metadata/

│   ├── scan\_manifest.csv         \# Retroactive labels for organic data

│   ├── test\_executions.csv       \# Controlled test metadata

│   └── parameter\_tiers.json      \# Which columns are Tier A/B/C

└── processed/                    \# Pipeline output (features, predictions)

---

## Part 7: Execution Timeline

### Week 1: Foundation

- [ ] Create `scan_manifest.csv` — label all 110 existing scans  
- [ ] Create `parameter_tiers.json` — define Tier A/B/C columns  
- [ ] Update `training_pipeline.py` to read labels from manifest instead of filenames  
- [ ] Implement Gate 1-5 preprocessing in the pipeline

### Week 2: Baseline Matrix

- [ ] Capture B1 through B7 (one session, \~35 min total scan time)  
- [ ] Verify all 7 files pass quality gates  
- [ ] Retrain ML models on labeled organic \+ baseline data  
- [ ] Record baseline model performance as your benchmark

### Week 3: First Fault Tests (Tier 1, tests 1-3)

- [ ] T01: MAF disconnect (triplet)  
- [ ] T02: O2 B1S1 disconnect (triplet)  
- [ ] T03: PCV vacuum leak (triplet)  
- [ ] Retrain after each test, measure detection accuracy

### Week 4: Remaining Tier 1 (tests 4-6)

- [ ] T04: Coolant temp sensor disconnect  
- [ ] T05: IAT sensor disconnect  
- [ ] T06: O2 B2S1 disconnect  
- [ ] Full model retrain, cross-validate on all fault types

### Month 2: Tier 2 \+ Repetition

- [ ] Execute Tier 2 tests (T07-T12)  
- [ ] Repeat Tier 1 tests at different engine temps (cold vs. warm)  
- [ ] Repeat B1-B7 baseline matrix (second month)

### Month 3: Multi-Fault \+ Validation

- [ ] Tier 3 combined fault tests  
- [ ] Hold-out validation set: re-run 3 random faults, don't train on them, use as blind test  
- [ ] Publish results in model performance table

---

## Part 8: Sample Size Targets

For supervised learning to work with your Random Forest, you need:

| Class | Minimum Samples | Target Samples | Current |
| :---- | :---- | :---- | :---- |
| healthy (various modes) | 30 | 100+ | \~5 (labeled) |
| fault\_maf | 5 | 15 | 0 |
| fault\_o2 | 5 | 15 | 0 |
| fault\_vacuum | 5 | 15 | 0 |
| fault\_ect | 5 | 15 | 0 |
| fault\_misfire | 5 | 15 | 0 |
| fault\_alternator | 3 | 10 | \~3 (unlabeled) |
| multi\_fault | 3 | 10 | 0 |

**How to get 15 samples per fault type without doing the test 15 times:**

1. **Window slicing.** A 3-minute fault scan at 2 Hz \= 360 rows. Slice it into non-overlapping 60-row windows → 6 samples per scan.  
2. **Condition variation.** Do the same fault at cold idle, warm idle, and 2000 RPM → 3 scans × 6 windows \= 18 samples.  
3. **Temporal repetition.** Repeat the same test a month later → another 18 samples with natural variation.

This gets you to 30+ samples per fault type from just 6 actual test sessions per fault.

---

## Part 9: What This Enables in Your ML Pipeline

Once you have this structured data, your pipeline changes from:

\# CURRENT: guess labels from filenames

if 'good' in filename:

    df\['condition'\] \= 'good'

To:

\# FUTURE: read from manifest

manifest \= pd.read\_csv('data/metadata/scan\_manifest.csv')

for \_, row in manifest.iterrows():

    df \= pd.read\_csv(row\['filepath'\])

    df \= df.iloc\[30:\]  \# Gate 2: drop initialization rows

    df \= df\[TIER\_A\_COLUMNS\]  \# Only ML-relevant features

    df\['condition'\] \= row\['condition'\]

    df\['operating\_mode'\] \= row\['operating\_mode'\]

    all\_dfs.append(df)

And your LSTM gets multivariate input instead of single-sensor:

\# FUTURE: train on Tier A features as multivariate time series

features \= df\[TIER\_A\_COLUMNS\].values  \# shape: (timesteps, 25\)

\# Instead of training separate models per sensor

---

## Quick-Reference: Test Day Checklist

□ Scanner charged, cable connected

□ Clear all existing DTCs before starting

□ Note ambient temperature and mileage

□ Engine at target temperature for test type

□ Phone camera ready for documentation

For each test:

  □ Start X431 DataStream recording (ALL parameters)

  □ Capture BASELINE (3-5 min)

  □ Save file with correct naming convention

  □ Introduce fault

  □ Wait 30s for stabilization

  □ Capture FAULT (2-3 min)

  □ Save file

  □ Restore component

  □ Clear DTCs

  □ Capture CLEARED (2 min)

  □ Save file

  □ Fill in test\_executions.csv row

  □ Take photo of connector/component tested

After all tests:

  □ Verify all files saved correctly

  □ Transfer to MacBook

  □ Run quality gate checks

  □ Commit to git with test ID in commit message  
