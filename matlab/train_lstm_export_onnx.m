% train_lstm_export_onnx.m
% OPTION 1: Train in MATLAB, Export to Python
% Requires: Deep Learning Toolbox

disp('1. Loading Training Data from CSV...');

% Dynamically find the project root regardless of MATLAB's current folder
scriptPath = fileparts(mfilename('fullpath'));
projectRoot = fullfile(scriptPath, '..');

% Load your processed CSV data
csvFile = fullfile(projectRoot, 'data', 'processed', 'diagnostic_reports.csv');
disp(['Attempting to load data from: ', csvFile]);
data = readtable(csvFile);

% Extract only numeric sensor columns for the LSTM
numericCols = varfun(@isnumeric, data, 'OutputFormat', 'uniform');
sensorData = data{:, numericCols};

% Fill missing values with 0
sensorData(isnan(sensorData)) = 0;

% We transpose data because LSTM expects (Features x Sequence Length)
XTrain = {sensorData'}; 

% Create the target variable for the LSTM (we'll try to predict 'total_misfire')
if ismember('total_misfire', data.Properties.VariableNames)
    yData = [data.total_misfire]';
    % Fix: Remove NaNs from the target variable to prevent MATLAB crashes
    yData(isnan(yData)) = 0;
else
    yData = rand(1, size(data, 1)) * 10; % Fallback dummy target
end

% Since we pass XTrain as a single sequence block, YTrain must also be a sequence block
YTrain = {yData};

disp('2. Defining LSTM Deep Learning Architecture...');
numFeatures = size(sensorData, 2);
numHiddenUnits = 50;
numResponses = 1;

layers = [ ...
    sequenceInputLayer(numFeatures, 'Name', 'input')
    lstmLayer(numHiddenUnits, 'OutputMode', 'sequence', 'Name', 'lstm')
    fullyConnectedLayer(numResponses, 'Name', 'fc')
    regressionLayer('Name', 'output')];

disp('3. Training Network using Deep Learning Toolbox...');
options = trainingOptions('adam', ...
    'MaxEpochs', 15, ...
    'MiniBatchSize', 16, ...
    'Plots', 'training-progress', ...
    'Verbose', 0);

net = trainNetwork(XTrain, YTrain, layers, options);

disp('4. Exporting to ONNX for FastAPI Backend...');
exportPath = fullfile(projectRoot, 'models', 'vehicle_lstm_model.onnx');

% Ensure the models directory exists
if ~exist(fullfile(projectRoot, 'models'), 'dir')
    mkdir(fullfile(projectRoot, 'models'));
end

exportONNXNetwork(net, exportPath);

disp(['SUCCESS! Model exported to: ' exportPath]);
disp('Your FastAPI server will now automatically load it!');
