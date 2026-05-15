% BCScanTool v2.0 - MATLAB Analysis Script
% Advanced signal processing and visualization for automotive diagnostic data
%
% Usage:
%   analyze_diagnostic_data('Tacoma Data/TOYOTA_989347712041_20251103165921.mat')
%
% Features:
%   - Time-series visualization
%   - FFT frequency analysis
%   - Wavelet analysis for transient detection
%   - Statistical analysis
%   - Anomaly detection
%
% Author: BCScanTool Project
% Date: January 2026

function analyze_diagnostic_data(matfile)
    % Load diagnostic data
    if nargin < 1
        % If no file specified, prompt user
        [file, path] = uigetfile('*.mat', 'Select Diagnostic Data File');
        if file == 0
            disp('No file selected');
            return
        end
        matfile = fullfile(path, file);
    end

    fprintf('\n========================================\n');
    fprintf('  BCScanTool MATLAB Analysis\n');
    fprintf('========================================\n\n');
    fprintf('Loading: %s\n', matfile);

    % Load data
    data = load(matfile);

    % Display data structure
    fprintf('\nData Structure:\n');
    fprintf('  Samples: %d\n', data.num_samples);
    fprintf('  Parameters: %d\n', data.num_parameters);
    fprintf('  Source: %s\n', data.source_file);

    % Extract key time series
    rpm = extract_parameter(data, 'rpm');
    coolant_temp = extract_parameter(data, 'coolant');
    maf = extract_parameter(data, 'maf');
    load_pct = extract_parameter(data, 'load');

    % Create comprehensive visualization
    create_dashboard(rpm, coolant_temp, maf, load_pct, data);

    % Frequency analysis
    if ~isempty(rpm)
        perform_fft_analysis(rpm, 'Engine RPM');
    end

    % Wavelet analysis for transient detection
    if ~isempty(maf)
        perform_wavelet_analysis(maf, 'MAF Sensor');
    end

    % Statistical summary
    generate_statistical_report(data);

    fprintf('\n✓ Analysis complete!\n\n');
end

function param = extract_parameter(data, keyword)
    % Extract parameter by keyword search with common automotive synonyms
    param = [];
    
    % Define synonyms for common parameters
    search_keywords = {lower(keyword)};
    if strcmpi(keyword, 'rpm')
        search_keywords = [search_keywords, {'engine speed', 'engine_speed', 'engine_rpm'}];
    elseif strcmpi(keyword, 'coolant')
        search_keywords = [search_keywords, {'coolant', 'temp', 'temperature', 'ect'}];
    elseif strcmpi(keyword, 'maf')
        search_keywords = [search_keywords, {'maf', 'mass air', 'mass_air', 'airflow', 'air flow'}];
    elseif strcmpi(keyword, 'load')
        search_keywords = [search_keywords, {'load', 'calc load', 'engine load'}];
    end

    % Get all field names
    fields = fieldnames(data);

    % Search for matching parameter in field names first
    for k = 1:length(search_keywords)
        current_kw = search_keywords{k};
        for i = 1:length(fields)
            field_lower = lower(fields{i});
            if contains(field_lower, current_kw)
                val = data.(fields{i});
                % Ensure it's numeric and has data
                if isnumeric(val) && length(val) > 1
                    param = val;
                    fprintf('  Found: %s\n', fields{i});
                    return
                end
            end
        end
    end

    % If not found as separate field, search column names
    if isfield(data, 'column_names') && isfield(data, 'data')
        cols = cellstr(data.column_names);
        
        for k = 1:length(search_keywords)
            current_kw = search_keywords{k};
            idx = find(contains(lower(cols), current_kw), 1);
            
            if ~isempty(idx)
                param = data.data(:, idx);
                fprintf('  Found in column %d: %s\n', idx, cols{idx});
                return
            end
        end
    end
end

function create_dashboard(rpm, coolant_temp, maf, load_pct, data)
    % Create comprehensive dashboard visualization

    figure('Name', 'Diagnostic Data Dashboard', 'Position', [100 100 1400 900]);

    % Time vector (assume 1 Hz sampling if not provided)
    t = (1:data.num_samples)';

    % Subplot 1: Engine RPM
    subplot(3,2,1);
    if ~isempty(rpm)
        plot(t, rpm, 'b', 'LineWidth', 1.5);
        ylabel('RPM');
        title('Engine Speed');
        grid on;
        ylim([0 max(rpm)*1.1]);
    else
        text(0.5, 0.5, 'RPM data not available', ...
            'HorizontalAlignment', 'center');
        axis off;
    end

    % Subplot 2: Coolant Temperature
    subplot(3,2,2);
    if ~isempty(coolant_temp)
        plot(t, coolant_temp, 'r', 'LineWidth', 1.5);
        ylabel('Temperature (°F)');
        title('Coolant Temperature');
        grid on;
        % Add normal operating range
        hold on;
        yline(195, '--g', 'Operating Temp');
        yline(220, '--r', 'Warning');
        hold off;
    else
        text(0.5, 0.5, 'Coolant temp data not available', ...
            'HorizontalAlignment', 'center');
        axis off;
    end

    % Subplot 3: MAF Sensor
    subplot(3,2,3);
    if ~isempty(maf)
        plot(t, maf, 'k', 'LineWidth', 1.5);
        ylabel('Airflow (g/s)');
        title('Mass Air Flow');
        grid on;
    else
        text(0.5, 0.5, 'MAF data not available', ...
            'HorizontalAlignment', 'center');
        axis off;
    end

    % Subplot 4: Engine Load
    subplot(3,2,4);
    if ~isempty(load_pct)
        plot(t, load_pct, 'Color', [0.85 0.33 0.10], 'LineWidth', 1.5);
        ylabel('Load (%)');
        title('Engine Load');
        grid on;
        ylim([0 100]);
    else
        text(0.5, 0.5, 'Load data not available', ...
            'HorizontalAlignment', 'center');
        axis off;
    end

    % Subplot 5: RPM vs MAF (correlation plot)
    subplot(3,2,5);
    if ~isempty(rpm) && ~isempty(maf)
        scatter(rpm, maf, 10, t, 'filled');
        xlabel('Engine RPM');
        ylabel('MAF (g/s)');
        title('RPM vs Airflow (colored by time)');
        grid on;
        colorbar;
    else
        text(0.5, 0.5, 'Correlation plot not available', ...
            'HorizontalAlignment', 'center');
        axis off;
    end

    % Subplot 6: Parameter statistics
    subplot(3,2,6);
    if ~isempty(rpm)
        % Create simple statistics display
        stats_text = sprintf(...
            'RPM Statistics:\n' + ...
            '  Mean: %.0f\n' + ...
            '  Std: %.0f\n' + ...
            '  Min: %.0f\n' + ...
            '  Max: %.0f\n\n', ...
            mean(rpm, 'omitnan'), std(rpm, 'omitnan'), ...
            min(rpm), max(rpm));

        if ~isempty(coolant_temp)
            stats_text = stats_text + sprintf(...
                'Coolant Temp:\n' + ...
                '  Mean: %.1f°F\n' + ...
                '  Max: %.1f°F\n', ...
                mean(coolant_temp, 'omitnan'), max(coolant_temp));
        end

        text(0.1, 0.9, stats_text, 'FontName', 'Courier', ...
            'FontSize', 10, 'VerticalAlignment', 'top');
        axis off;
    end

    sgtitle(sprintf('Diagnostic Data Analysis - %d samples', data.num_samples));
end

function perform_fft_analysis(signal, param_name)
    % Perform FFT frequency analysis

    figure('Name', sprintf('FFT Analysis - %s', param_name));

    % Remove mean
    signal_centered = signal - mean(signal, 'omitnan');

    % Remove NaN values
    signal_clean = signal_centered(~isnan(signal_centered));

    % FFT
    N = length(signal_clean);
    Fs = 1; % 1 Hz sampling rate (adjust if known)

    Y = fft(signal_clean);
    P2 = abs(Y/N);
    P1 = P2(1:floor(N/2)+1);
    P1(2:end-1) = 2*P1(2:end-1);

    f = Fs*(0:floor(N/2))/N;

    % Plot
    subplot(2,1,1);
    plot(signal_clean);
    title(sprintf('%s - Time Domain', param_name));
    xlabel('Sample');
    ylabel('Amplitude');
    grid on;

    subplot(2,1,2);
    plot(f, P1, 'LineWidth', 1.5);
    title('Frequency Domain (FFT)');
    xlabel('Frequency (Hz)');
    ylabel('|P1(f)|');
    grid on;

    % Identify dominant frequencies
    [peaks, locs] = findpeaks(P1, 'SortStr', 'descend', 'NPeaks', 3);
    if ~isempty(peaks)
        fprintf('\nDominant Frequencies in %s:\n', param_name);
        for i = 1:min(3, length(peaks))
            fprintf('  %.3f Hz (Amplitude: %.2f)\n', f(locs(i)), peaks(i));
        end
    end
end

function perform_wavelet_analysis(signal, param_name)
    % Perform continuous wavelet transform for transient detection

    figure('Name', sprintf('Wavelet Analysis - %s', param_name));

    % Remove NaN values
    signal_clean = signal(~isnan(signal));

    % Continuous Wavelet Transform
    [cfs, f] = cwt(signal_clean, 'morse', 1);  % 1 Hz sampling

    % Plot scalogram
    subplot(2,1,1);
    plot(signal_clean);
    title(sprintf('%s - Time Domain', param_name));
    xlabel('Sample');
    ylabel('Amplitude');
    grid on;

    subplot(2,1,2);
    surface(1:length(signal_clean), f, abs(cfs));
    axis tight;
    shading interp;
    xlabel('Sample');
    ylabel('Frequency (Hz)');
    title('Wavelet Scalogram (Time-Frequency Analysis)');
    colorbar;
    view(0, 90);

    fprintf('\nWavelet analysis complete for %s\n', param_name);
    fprintf('  Use scalogram to identify transient events\n');
    fprintf('  High energy at specific times indicates anomalies\n');
end

function generate_statistical_report(data)
    % Generate comprehensive statistical report

    fprintf('\n========================================\n');
    fprintf('  Statistical Summary\n');
    fprintf('========================================\n\n');

    if ~isfield(data, 'column_names') || ~isfield(data, 'data')
        fprintf('Statistical analysis requires column_names and data fields\n');
        return;
    end

    % Analyze each parameter
    cols = cellstr(data.column_names);
    fprintf('Parameter Statistics:\n\n');
    fprintf('%-40s %10s %10s %10s %10s\n', ...
        'Parameter', 'Mean', 'Std', 'Min', 'Max');
    fprintf('%s\n', repmat('-', 1, 80));

    for i = 1:min(10, length(cols))  % Show first 10
        col_data = data.data(:, i);
        col_data_clean = col_data(~isnan(col_data));

        if isempty(col_data_clean)
            continue;
        end

        param_name = cols{i};
        if length(param_name) > 40
            param_name = [param_name(1:37) '...'];
        end

        fprintf('%-40s %10.2f %10.2f %10.2f %10.2f\n', ...
            param_name, ...
            mean(col_data_clean), ...
            std(col_data_clean), ...
            min(col_data_clean), ...
            max(col_data_clean));
    end

    if data.num_parameters > 10
        fprintf('\n... and %d more parameters\n', data.num_parameters - 10);
    end
end

function analyze_test_triplet(triplet_file)
    % Analyze baseline-fault-cleared triplet
    % Special function for comparing test conditions

    fprintf('\n========================================\n');
    fprintf('  Test Triplet Analysis\n');
    fprintf('========================================\n\n');
    fprintf('Loading: %s\n', triplet_file);

    data = load(triplet_file);

    % Extract baseline, fault, cleared
    baseline_data = data.baseline.data;
    fault_data = data.fault.data;
    cleared_data = data.cleared.data;

    % Compare key parameters
    figure('Name', 'Test Triplet Comparison', 'Position', [100 100 1400 600]);

    % Find key parameter (e.g., MAF for MAF disconnect test)
    % This example assumes parameter is in first few columns
    param_idx = 1;  % Adjust based on your data

    baseline_param = baseline_data(:, param_idx);
    fault_param = fault_data(:, param_idx);
    cleared_param = cleared_data(:, param_idx);

    % Plot comparison
    subplot(1,3,1);
    plot(baseline_param, 'b', 'LineWidth', 1.5);
    title('Baseline (Normal)');
    ylabel('Parameter Value');
    xlabel('Sample');
    grid on;

    subplot(1,3,2);
    plot(fault_param, 'r', 'LineWidth', 1.5);
    title('Fault Induced');
    ylabel('Parameter Value');
    xlabel('Sample');
    grid on;

    subplot(1,3,3);
    plot(cleared_param, 'g', 'LineWidth', 1.5);
    title('Cleared (Restored)');
    ylabel('Parameter Value');
    xlabel('Sample');
    grid on;

    % Statistical comparison
    fprintf('\nParameter Comparison:\n');
    fprintf('  Baseline Mean: %.2f (Std: %.2f)\n', ...
        mean(baseline_param, 'omitnan'), std(baseline_param, 'omitnan'));
    fprintf('  Fault Mean: %.2f (Std: %.2f)\n', ...
        mean(fault_param, 'omitnan'), std(fault_param, 'omitnan'));
    fprintf('  Cleared Mean: %.2f (Std: %.2f)\n', ...
        mean(cleared_param, 'omitnan'), std(cleared_param, 'omitnan'));

    % Difference from baseline
    fault_diff = mean(fault_param, 'omitnan') - mean(baseline_param, 'omitnan');
    cleared_diff = mean(cleared_param, 'omitnan') - mean(baseline_param, 'omitnan');

    fprintf('\nDeviation from Baseline:\n');
    fprintf('  Fault: %.2f (%.1f%%)\n', fault_diff, ...
        100*fault_diff/mean(baseline_param, 'omitnan'));
    fprintf('  Cleared: %.2f (%.1f%%)\n', cleared_diff, ...
        100*cleared_diff/mean(baseline_param, 'omitnan'));

    fprintf('\n✓ Triplet analysis complete!\n');
end

% Helper function: Detect anomalies using statistical methods
function anomalies = detect_anomalies_statistical(signal, threshold_std)
    % Detect anomalies using z-score method

    if nargin < 2
        threshold_std = 3;  % 3 sigma threshold
    end

    % Remove NaN
    signal_clean = signal(~isnan(signal));

    % Calculate z-scores
    mu = mean(signal_clean);
    sigma = std(signal_clean);
    z_scores = abs((signal_clean - mu) / sigma);

    % Flag anomalies
    anomalies = z_scores > threshold_std;

    fprintf('Anomaly Detection:\n');
    fprintf('  Total samples: %d\n', length(signal_clean));
    fprintf('  Anomalies detected: %d (%.1f%%)\n', ...
        sum(anomalies), 100*sum(anomalies)/length(signal_clean));
end
