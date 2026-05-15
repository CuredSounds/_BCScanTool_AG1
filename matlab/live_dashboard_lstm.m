% live_dashboard_lstm.m
% OPTION 3: MATLAB Live Deep Learning Dashboard
% Continuously polls FastAPI and updates a live LSTM prediction plot.

vin = '5TFUU4EN2BX005907';
apiUrl = sprintf('http://127.0.0.1:8080/api/vehicles/%s/diagnostics', vin);
options = weboptions('Timeout', 5);

figure('Name', 'Live Deep Learning Predictions', 'NumberTitle', 'off');
hPlot = animatedline('Color', 'r', 'LineWidth', 2);
xlabel('Time / Scan Index');
ylabel('Anomaly Prediction Score');
title('Real-Time LSTM Monitoring');
grid on;

disp('Starting Live MATLAB Dashboard. Press Ctrl+C to stop.');

scanIndex = 1;

while true
    try
        % 1. Fetch live data from Python API
        data = webread(apiUrl, options);
        
        % 2. Extract sensor variables 
        % (In practice, you extract the arrays from the JSON)
        rpm = 800 + randn()*50; % Simulated extraction
        
        % 3. Run MATLAB Deep Learning Inference 
        % prediction = predict(myLSTM_Net, rpm);
        simulatedPrediction = sin(scanIndex/5) + randn()*0.1;
        
        % 4. Update the live plot
        addpoints(hPlot, scanIndex, simulatedPrediction);
        drawnow limitrate;
        
        scanIndex = scanIndex + 1;
        
        % Wait 2 seconds before polling again
        pause(2);
    catch
        disp('Waiting for FastAPI server...');
        pause(5);
    end
end
