% fetch_api_data.m
% 
% This script demonstrates how to fetch diagnostic data and ML predictions 
% from the BCScanTool FastAPI backend using standard HTTP requests.
% NO DATABASE TOOLBOX REQUIRED!

function vehicleData = fetch_api_data(vin)
    if nargin < 1
        % Default VIN for testing (Toyota Tacoma from Phase 3 dataset)
        vin = '5TFUU4EN2BX005907';
    end

    % Define the local FastAPI endpoint
    apiUrl = sprintf('http://127.0.0.1:8080/api/vehicles/%s/diagnostics', vin);
    
    fprintf('Fetching AI Diagnostics for VIN: %s...\n', vin);
    
    try
        % webread automatically parses the JSON response into a MATLAB struct
        options = weboptions('Timeout', 15);
        vehicleData = webread(apiUrl, options);
        
        % Display High-Level Metrics
        fprintf('\n=========================================\n');
        fprintf('  VEHICLE HEALTH: %d/100 (%s)\n', vehicleData.health_score, vehicleData.health_grade);
        fprintf('  STATUS: %s\n', vehicleData.health_status);
        fprintf('=========================================\n\n');
        
        % Process and Display ML Predictive Alerts
        if isfield(vehicleData, 'predictions') && ~isempty(vehicleData.predictions)
            disp('--- PREDICTIVE ALERTS DETECTED ---');
            
            % Handle both single struct and array of structs
            alerts = vehicleData.predictions;
            if ~iscell(alerts) && length(alerts) == 1
                alerts = {alerts};
            end
            
            for i = 1:length(alerts)
                if iscell(alerts)
                    alert = alerts{i};
                else
                    alert = alerts(i);
                end
                
                fprintf('[%s] %s\n', alert.severity, alert.issue);
                fprintf('    Details: %s\n', alert.details);
                fprintf('    Confidence: %s\n\n', alert.confidence);
            end
        else
            disp('✓ No predictive alerts detected. Vehicle operating normally.');
        end
        
        % Plotting Example (If you want to visualize the score)
        figure('Name', sprintf('Health Score - %s', vin));
        bar(vehicleData.health_score);
        ylim([0 100]);
        ylabel('Health Score');
        title(sprintf('Overall Health: %s', vehicleData.health_grade));
        
    catch ME
        fprintf(2, 'Error connecting to API: %s\n', ME.message);
        fprintf(2, 'Make sure your FastAPI server is running via scripts/start_phase3.py\n');
        vehicleData = [];
    end
end
