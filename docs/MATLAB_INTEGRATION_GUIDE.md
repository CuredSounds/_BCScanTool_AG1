# MATLAB Integration Guide
**BCScanTool v2.0 - Advanced Signal Processing and Analysis**

---

## Table of Contents
1. [Overview](#overview)
2. [Setup and Installation](#setup-and-installation)
3. [Data Export from Python](#data-export-from-python)
4. [MATLAB Analysis Functions](#matlab-analysis-functions)
5. [Advanced Signal Processing](#advanced-signal-processing)
6. [Example Workflows](#example-workflows)
7. [Tips and Best Practices](#tips-and-best-practices)

---

## 1. Overview

### Why MATLAB Integration?

MATLAB offers powerful capabilities for automotive diagnostic data analysis that complement the Python ML pipeline:

**Signal Processing:**
- FFT (Fast Fourier Transform) for frequency analysis
- Wavelet transforms for transient detection
- Filtering (Kalman, butterworth, etc.)
- Spectral analysis

**Advanced Analytics:**
- System identification
- State-space modeling
- Transfer function analysis
- Vibration analysis

**Visualization:**
- High-quality publication plots
- Interactive data exploration
- 3D time-frequency analysis
- Custom dashboards

**Integration with Simulink:**
- Model-based diagnostics
- Real-time simulation
- Hardware-in-the-loop testing

### Architecture

```
Python (Data Collection & ML) <---> MATLAB (Advanced Analysis)
         |                              |
   OBD-II Scanner                  Signal Processing
   ML Training                     Frequency Analysis
   Database (SQLite) <------------> Visualization
                                  System Modeling
```

### 1.1 Database-Centric Workflow (Recommended for v2.0)

Instead of passing individual CSV or .mat files, v2.0 supports a unified SQLite database (`data/diagnostics.db`).

**Benefits:**
- **Shared Classifiers:** Ground truth labels (e.g., "maf_fault") are stored with the data.
- **Vehicle Filtering:** Easily query all data for a specific vehicle type.
- **Direct Access:** MATLAB can query the database directly using `sqlite()` command.
- **Scalability:** Handles 200+ categories across hundreds of sessions efficiently.

---

## 2. Setup and Installation

### 2.1 Required MATLAB Toolboxes

**Essential:**
- Signal Processing Toolbox
- Statistics and Machine Learning Toolbox

**Recommended:**
- Wavelet Toolbox
- Control System Toolbox (for transfer functions)
- Simulink (for modeling)

**Check installed toolboxes:**
```matlab
ver
```

### 2.2 Python Requirements

Ensure you have scipy installed for .mat file export:

```bash
pip install scipy
```

### 2.3 Directory Structure

```
_BCScanTool-v1/
├── python/
│   └── matlab/
│       └── export_to_matlab.py    # Export script
├── matlab/
│   ├── analyze_diagnostic_data.m  # Main analysis
│   ├── data/                      # Exported .mat files
│   └── examples/                  # Example scripts
└── data/
    └── raw/                       # Source CSV files
```

---

## 3. Data Export from Python

### 3.1 Export Single Session

**Python:**
```python
from matlab.export_to_matlab import export_session_to_mat

# Export single CSV to .mat
export_session_to_mat(
    'data/raw/TOYOTA_20260115_baseline.csv',
    'matlab/data/baseline.mat'
)
```

**What gets exported:**
- `data`: Full numeric array (samples × parameters)
- `column_names`: Parameter names
- `num_samples`: Number of data points
- `num_parameters`: Number of monitored parameters
- Individual parameter arrays (for easy access)

### 3.2 Export All Sessions

```python
from matlab.export_to_matlab import export_all_sessions

# Export entire directory
export_all_sessions(
    input_dir='data/raw',
    output_dir='matlab/data'
)
```

### 3.3 Export Test Triplet

For fault injection tests with baseline/fault/cleared:

```python
from matlab.export_to_matlab import export_test_triplet

export_test_triplet(
    baseline_path='data/raw/controlled_faults/maf_fault/baseline.csv',
    fault_path='data/raw/controlled_faults/maf_fault/fault.csv',
    cleared_path='data/raw/controlled_faults/maf_fault/cleared.csv',
    output_dir='matlab/data/triplets'
)
```

Creates a single .mat file with all three conditions for comparison.

### 3.4 Export ML Model Metadata

```python
from matlab.export_to_matlab import export_ml_model_data

export_ml_model_data(
    'data/processed/toyota_anomaly_model.joblib',
    'matlab/data/model_metadata.mat'
)
```

Exports:
- Feature names
- Scaler parameters (mean, std)
- Model type and configuration

---

## 4. MATLAB Analysis Functions

### 4.1 Load and Visualize Data

**Basic usage:**
```matlab
% Load diagnostic data
analyze_diagnostic_data('matlab/data/TOYOTA_20260115_baseline.mat');
```

**What it does:**
1. Loads .mat file
2. Extracts key parameters (RPM, coolant temp, MAF, load)
3. Creates comprehensive dashboard
4. Performs FFT frequency analysis
5. Wavelet analysis for transients
6. Statistical summary

### 4.2 Manual Data Access

```matlab
% Load file
data = load('matlab/data/TOYOTA_20260115_baseline.mat');

% Access data
rpm = data.Engine_Speed_rpm_;  % Individual parameter
all_data = data.data;  % Full matrix
params = data.column_names;  % Parameter names

% Time vector (assuming 1 Hz sampling)
t = (1:data.num_samples)' / data.sampling_rate;  % if rate provided

% Plot specific parameter
plot(rpm);
xlabel('Sample');
ylabel('RPM');
title('Engine Speed');
```

### 4.3 Advanced Filtering

**Low-pass filter to remove noise:**
```matlab
% Load data
data = load('matlab/data/your_file.mat');
maf = data.MAF_g_s_;

% Design low-pass Butterworth filter
fc = 0.1;  % Cutoff frequency (Hz)
fs = 1;    % Sampling frequency (Hz)
[b, a] = butter(4, fc/(fs/2));  % 4th order

% Apply filter
maf_filtered = filtfilt(b, a, maf);

% Compare
figure;
plot(maf, 'b'); hold on;
plot(maf_filtered, 'r', 'LineWidth', 2);
legend('Raw', 'Filtered');
title('MAF Sensor - Raw vs Filtered');
```

### 4.4 Kalman Filter for Sensor Fusion

```matlab
% Example: Fuse MAF and calculated airflow
% (Requires Control System Toolbox)

% State-space model (simplified)
A = 1;  % State transition
B = 0;  % Control input (none)
C = 1;  % Observation model
D = 0;

% Noise covariances
Q = 0.01;  % Process noise
R = 1;     % Measurement noise

% Create Kalman filter
sys = ss(A, B, C, D, -1);  % Discrete-time
[kalmf, L] = kalman(sys, Q, R);

% Apply to data
maf_kalman = ltitr(kalmf.A, kalmf.B, maf);
```

---

## 5. Advanced Signal Processing

### 5.1 FFT Frequency Analysis

**Identify periodic patterns:**
```matlab
% Load RPM data
data = load('matlab/data/idle_test.mat');
rpm = data.Engine_Speed_rpm_;

% Remove mean
rpm_centered = rpm - mean(rpm);

% FFT
N = length(rpm_centered);
Fs = 1;  % 1 Hz sampling
Y = fft(rpm_centered);
P2 = abs(Y/N);
P1 = P2(1:N/2+1);
P1(2:end-1) = 2*P1(2:end-1);
f = Fs*(0:(N/2))/N;

% Plot
figure;
subplot(2,1,1);
plot(rpm);
title('RPM - Time Domain');

subplot(2,1,2);
plot(f, P1);
title('RPM - Frequency Domain');
xlabel('Frequency (Hz)');
ylabel('Amplitude');

% Find dominant frequency
[~, idx] = max(P1(2:end));  % Skip DC component
fprintf('Dominant frequency: %.3f Hz\n', f(idx+1));
```

**Interpretation:**
- **Idle vibration:** ~20-30 Hz (engine firing frequency)
- **Misfire:** Irregular frequency components
- **Sensor noise:** High-frequency components

### 5.2 Continuous Wavelet Transform

**Detect transient events:**
```matlab
% Load data
data = load('matlab/data/acceleration_test.mat');
throttle = data.Throttle_Position_pct_;

% Continuous Wavelet Transform
[cfs, f] = cwt(throttle, 'morse', 1);  % 1 Hz sampling

% Plot scalogram
figure;
subplot(2,1,1);
plot(throttle);
title('Throttle Position');

subplot(2,1,2);
surface(1:length(throttle), f, abs(cfs));
axis tight;
shading interp;
xlabel('Sample');
ylabel('Frequency (Hz)');
title('Wavelet Scalogram');
colorbar;
view(0, 90);
```

**Use cases:**
- Detect rapid throttle changes
- Identify gear shifts
- Find sensor glitches
- Locate fault onset

### 5.3 Power Spectral Density

**Analyze signal power distribution:**
```matlab
% Load vibration data (if available from accelerometer)
data = load('matlab/data/vibration_test.mat');
vibration = data.vibration_signal;

% Compute PSD using Welch's method
Fs = 100;  % Sampling frequency (adjust)
[pxx, f] = pwelch(vibration, [], [], [], Fs);

% Plot
figure;
plot(f, 10*log10(pxx));
xlabel('Frequency (Hz)');
ylabel('Power/Frequency (dB/Hz)');
title('Power Spectral Density');
grid on;

% Identify peaks (resonances, vibrations)
[peaks, locs] = findpeaks(10*log10(pxx), 'SortStr', 'descend', 'NPeaks', 5);
fprintf('\nTop 5 Resonant Frequencies:\n');
for i = 1:length(peaks)
    fprintf('  %.2f Hz: %.2f dB\n', f(locs(i)), peaks(i));
end
```

### 5.4 Cross-Correlation Analysis

**Find relationships between parameters:**
```matlab
% Load data
data = load('matlab/data/test_session.mat');
rpm = data.Engine_Speed_rpm_;
maf = data.MAF_g_s_;

% Cross-correlation
[r, lag] = xcorr(rpm, maf, 'normalized');

% Plot
figure;
plot(lag, r);
xlabel('Lag (samples)');
ylabel('Correlation');
title('Cross-Correlation: RPM vs MAF');
grid on;

% Find max correlation and lag
[max_corr, idx] = max(abs(r));
time_lag = lag(idx);
fprintf('Max correlation: %.3f at lag %d samples\n', max_corr, time_lag);
```

**Interpretation:**
- **High correlation, zero lag:** Parameters change together
- **High correlation, non-zero lag:** One parameter leads the other
- **Low correlation:** Parameters independent

---

## 6. Example Workflows

### 6.1 Analyze MAF Fault Test

**Complete workflow from test to analysis:**

**Step 1: Export data (Python)**
```python
from matlab.export_to_matlab import export_test_triplet

export_test_triplet(
    'data/raw/controlled_faults/maf_fault/baseline.csv',
    'data/raw/controlled_faults/maf_fault/fault.csv',
    'data/raw/controlled_faults/maf_fault/cleared.csv',
    'matlab/data/'
)
```

**Step 2: Analyze in MATLAB**
```matlab
% Load triplet
data = load('matlab/data/baseline_triplet.mat');

% Extract MAF readings
baseline_maf = data.baseline.data(:, find_param_index(data, 'MAF'));
fault_maf = data.fault.data(:, find_param_index(data, 'MAF'));
cleared_maf = data.cleared.data(:, find_param_index(data, 'MAF'));

% Plot comparison
figure;
subplot(3,1,1);
plot(baseline_maf, 'b', 'LineWidth', 1.5);
title('Baseline - Normal MAF Operation');
ylabel('MAF (g/s)');

subplot(3,1,2);
plot(fault_maf, 'r', 'LineWidth', 1.5);
title('Fault - MAF Disconnected');
ylabel('MAF (g/s)');

subplot(3,1,3);
plot(cleared_maf, 'g', 'LineWidth', 1.5);
title('Cleared - MAF Reconnected');
ylabel('MAF (g/s)');
xlabel('Sample');

% Statistical comparison
fprintf('\nMAF Statistics:\n');
fprintf('Baseline: Mean=%.2f, Std=%.2f\n', mean(baseline_maf), std(baseline_maf));
fprintf('Fault:    Mean=%.2f, Std=%.2f\n', mean(fault_maf), std(fault_maf));
fprintf('Cleared:  Mean=%.2f, Std=%.2f\n', mean(cleared_maf), std(cleared_maf));

% Detection metric
fault_deviation = abs(mean(fault_maf) - mean(baseline_maf));
fprintf('\nFault Deviation: %.2f g/s\n', fault_deviation);
```

### 6.2 Time-Series Trend Analysis

**Track parameter changes over weeks:**

```matlab
% Load multiple weekly health checks
week1 = load('matlab/data/2026-01-15_weekly_health.mat');
week2 = load('matlab/data/2026-01-22_weekly_health.mat');
week3 = load('matlab/data/2026-01-29_weekly_health.mat');
week4 = load('matlab/data/2026-02-05_weekly_health.mat');

% Extract long-term fuel trim (LTFT)
ltft_week1 = mean(week1.LTFT_Bank1_pct_);
ltft_week2 = mean(week2.LTFT_Bank1_pct_);
ltft_week3 = mean(week3.LTFT_Bank1_pct_);
ltft_week4 = mean(week4.LTFT_Bank1_pct_);

% Plot trend
weeks = 1:4;
ltft_trend = [ltft_week1, ltft_week2, ltft_week3, ltft_week4];

figure;
plot(weeks, ltft_trend, '-o', 'LineWidth', 2, 'MarkerSize', 10);
xlabel('Week');
ylabel('Long-Term Fuel Trim (%)');
title('LTFT Trend Over Time');
grid on;

% Add normal range
hold on;
yline(10, '--r', 'Upper Limit');
yline(-10, '--r', 'Lower Limit');
hold off;

% Linear regression to detect drift
p = polyfit(weeks, ltft_trend, 1);
slope = p(1);
fprintf('LTFT trend: %.3f%%/week\n', slope);

if abs(slope) > 2
    fprintf('⚠️  WARNING: Significant fuel trim drift detected!\n');
else
    fprintf('✓ Fuel trims stable\n');
end
```

### 6.3 Vibration Analysis (If Accelerometer Data Available)

```matlab
% If you have accelerometer data from phone/sensor
% placed on engine during diagnostic scan

data = load('matlab/data/vibration_scan.mat');
accel_x = data.accelerometer_x;
accel_y = data.accelerometer_y;
accel_z = data.accelerometer_z;

% Sampling rate (adjust based on your sensor)
Fs = 100;  % Hz

% Compute magnitude
accel_mag = sqrt(accel_x.^2 + accel_y.^2 + accel_z.^2);

% Spectrogram (time-frequency analysis)
figure;
spectrogram(accel_mag, 256, 250, 256, Fs, 'yaxis');
title('Engine Vibration Spectrogram');
colorbar;

% Expected patterns:
% - Idle: ~20-30 Hz (4-cyl) or ~30-45 Hz (6-cyl)
% - Misfire: Irregular/missing frequency components
% - Bearing issue: High-frequency noise
```

### 6.4 Compare Multiple Vehicles

```matlab
% Load data from both vehicles
toyota_data = load('matlab/data/toyota_weekly_health.mat');
volvo_data = load('matlab/data/volvo_weekly_health.mat');

% Extract coolant temps
toyota_temp = toyota_data.Coolant_Temp_degree_F_;
volvo_temp = volvo_data.Coolant_Temp_degree_C_ * 9/5 + 32;  % Convert to F

% Compare warmup curves
figure;
plot(toyota_temp, 'b', 'LineWidth', 1.5); hold on;
plot(volvo_temp, 'r', 'LineWidth', 1.5);
xlabel('Sample');
ylabel('Coolant Temperature (°F)');
title('Warmup Comparison');
legend('Toyota Tacoma', 'Volvo');
grid on;

% Time to reach operating temp
op_temp = 195;  % °F
toyota_warmup_time = find(toyota_temp > op_temp, 1);
volvo_warmup_time = find(volvo_temp > op_temp, 1);

fprintf('Warmup time comparison:\n');
fprintf('  Toyota: %d samples (~%.1f min)\n', toyota_warmup_time, toyota_warmup_time/60);
fprintf('  Volvo: %d samples (~%.1f min)\n', volvo_warmup_time, volvo_warmup_time/60);
```

---

## 7. Tips and Best Practices

### 7.1 Performance Optimization

**For large datasets:**
```matlab
% Pre-allocate arrays
n_files = 100;
results = zeros(n_files, 1);

% Vectorize operations instead of loops
% SLOW:
for i = 1:length(data)
    processed(i) = data(i) * 2 + 1;
end

% FAST:
processed = data * 2 + 1;

% Use parfor for parallel processing (requires Parallel Computing Toolbox)
parfor i = 1:n_files
    results(i) = process_file(files(i));
end
```

### 7.2 Handling Missing Data

```matlab
% Remove NaN values
data_clean = data(~isnan(data));

% Interpolate missing values
data_interp = fillmissing(data, 'linear');

% Replace with median
data_filled = fillmissing(data, 'constant', median(data, 'omitnan'));
```

### 7.3 Publication-Quality Plots

```matlab
% Configure plot for publication
figure('Position', [100 100 800 600]);
plot(t, rpm, 'LineWidth', 2);
xlabel('Time (s)', 'FontSize', 14);
ylabel('Engine Speed (RPM)', 'FontSize', 14);
title('Engine RPM During Acceleration', 'FontSize', 16, 'FontWeight', 'bold');
grid on;
set(gca, 'FontSize', 12);

% Export high-resolution
print('figure_rpm', '-dpng', '-r300');  % 300 DPI
```

### 7.4 Automated Batch Processing

```matlab
% Process all files in directory
files = dir('matlab/data/*.mat');

for i = 1:length(files)
    fprintf('Processing %s...\n', files(i).name);

    data = load(fullfile(files(i).folder, files(i).name));

    % Your analysis here
    result = analyze_data(data);

    % Save results
    save(sprintf('results_%d.mat', i), 'result');
end

fprintf('✓ Processed %d files\n', length(files));
```

### 7.5 Integration with Python

**Call MATLAB from Python:**
```python
import matlab.engine

# Start MATLAB engine
eng = matlab.engine.start_matlab()

# Call MATLAB function
result = eng.analyze_diagnostic_data('matlab/data/test.mat')

# Stop engine
eng.quit()
```

**Call Python from MATLAB:**
```matlab
% Call Python function from MATLAB
py.import('export_to_matlab')
py.export_to_matlab.export_session_to_mat('data.csv', 'data.mat')
```

---

## 8. Helper Functions

### 8.1 Find Parameter Index

```matlab
function idx = find_param_index(data, keyword)
    % Find parameter index by keyword search
    idx = find(contains(data.column_names, keyword, 'IgnoreCase', true), 1);
    if isempty(idx)
        error('Parameter "%s" not found', keyword);
    end
end
```

### 8.2 Extract Parameter by Name

```matlab
function param = get_parameter(data, name)
    % Extract parameter by exact or partial name match
    idx = find_param_index(data, name);
    param = data.data(:, idx);
end
```

### 8.3 Compare Two Sessions

```matlab
function compare_sessions(file1, file2, param_name)
    % Quick comparison of same parameter in two sessions

    data1 = load(file1);
    data2 = load(file2);

    param1 = get_parameter(data1, param_name);
    param2 = get_parameter(data2, param_name);

    figure;
    plot(param1, 'b'); hold on;
    plot(param2, 'r');
    legend('Session 1', 'Session 2');
    title(sprintf('Comparison: %s', param_name));
    grid on;

    % Stats
    fprintf('\nSession 1: Mean=%.2f, Std=%.2f\n', mean(param1), std(param1));
    fprintf('Session 2: Mean=%.2f, Std=%.2f\n', mean(param2), std(param2));
end
```

---

## 9. Research Applications

### 9.1 Thesis/Publication Figures

**High-quality figure generation:**
```matlab
% Create multi-panel figure for paper
figure('Position', [100 100 1200 800]);

% Panel A: Time series
subplot(2,2,1);
plot(data.rpm, 'LineWidth', 1.5);
title('(A) Engine Speed');
ylabel('RPM');

% Panel B: Frequency domain
subplot(2,2,2);
[pxx, f] = pwelch(data.rpm);
plot(f, 10*log10(pxx), 'LineWidth', 1.5);
title('(B) Frequency Spectrum');
ylabel('Power (dB)');

% Panel C: Wavelet
subplot(2,2,3);
[cfs, f] = cwt(data.maf);
surface(1:length(data.maf), f, abs(cfs));
shading interp;
view(0,90);
title('(C) Wavelet Analysis');

% Panel D: Statistics
subplot(2,2,4);
histogram(data.ltft, 30);
title('(D) Fuel Trim Distribution');
xlabel('LTFT (%)');

% Save for publication
print('figure_comprehensive', '-dpng', '-r300');
```

### 9.2 Dataset Documentation

```matlab
% Generate dataset summary for paper
function generate_dataset_summary(matlab_data_dir)
    files = dir(fullfile(matlab_data_dir, '*.mat'));

    fprintf('Dataset Summary\n');
    fprintf('===============\n\n');
    fprintf('Total files: %d\n', length(files));

    total_samples = 0;
    total_parameters = 0;

    for i = 1:length(files)
        data = load(fullfile(files(i).folder, files(i).name));
        total_samples = total_samples + data.num_samples;
        total_parameters = max(total_parameters, data.num_parameters);
    end

    fprintf('Total samples: %d\n', total_samples);
    fprintf('Max parameters per session: %d\n', total_parameters);
    fprintf('\nFor inclusion in paper methods section.\n');
end
```

---

## 10. Troubleshooting

### Common Issues:

**Issue:** "Undefined function or variable"
**Solution:** Ensure file is in MATLAB path: `addpath('matlab')`

**Issue:** "Array size mismatch"
**Solution:** Check that all sessions have same sampling rate/parameters

**Issue:** "Out of memory"
**Solution:** Process files in batches or downsample data

**Issue:** "Slow performance"
**Solution:** Vectorize loops, use `parfor`, or process in chunks

---

## 11. Next Steps

**Advanced Topics:**
1. **System Identification:** Model engine dynamics from data
2. **Kalman Filtering:** Optimal sensor fusion
3. **Neural Networks:** Train in MATLAB, compare to Python
4. **Simulink Integration:** Real-time diagnostic simulation
5. **Hardware Integration:** Connect to vehicle via MATLAB

**Further Reading:**
- MATLAB Signal Processing Toolbox documentation
- "Digital Signal Processing" by Oppenheim & Schafer
- "Vehicle Dynamics and Control" by Rajesh Rajamani
- SAE papers on automotive diagnostics

---

**Your MATLAB-Python pipeline is now complete and ready for advanced automotive diagnostic research!** 🚗📊

---

*Last Updated: January 13, 2026*
*BCScanTool v2.0 | Neural Harmonics Lab*
