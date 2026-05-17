% train_vehicle_specific_autoencoder.m
% OPTION 2: MATLAB Vehicle-Specific Deep Learning Autoencoder
% Requires: Deep Learning Toolbox

disp('============================================================');
disp(' 🏎️ MATLAB - Vehicle-Specific Deep Learning Trainer 🏎️');
disp('============================================================');

disp('1. Scanning for raw datastream CSVs for Toyota Tacoma...');
scriptPath = fileparts(mfilename('fullpath'));
projectRoot = fullfile(scriptPath, '..');
dataDir = fullfile(projectRoot, 'data', 'csv', 'Vehicle_make_model', 'Toyota', 'Tacoma');

% Find all clean CSVs
files = dir(fullfile(dataDir, '*_clean.csv'));
if isempty(files)
    error('No _clean.csv files found for this vehicle.');
end

disp(['Found ', num2str(length(files)), ' datastream files. Loading...']);
allData = cell(length(files), 1);
for i = 1:length(files)
    try
        allData{i} = readtable(fullfile(files(i).folder, files(i).name));
    catch
        disp(['Skipping ', files(i).name]);
    end
end
masterTable = vertcat(allData{:});

disp('2. Discovering Vehicle-Specific Features...');
% Extract only numeric columns
numericCols = varfun(@isnumeric, masterTable, 'OutputFormat', 'uniform');
sensorData = masterTable{:, numericCols};

% Remove NaNs
sensorData(isnan(sensorData)) = 0;
numFeatures = size(sensorData, 2);
disp(['   => Discovered ', num2str(numFeatures), ' unique sensors/parameters!']);

disp('3. Preprocessing (Standardization)...');
mu = mean(sensorData, 1);
sig = std(sensorData, 0, 1);
% Prevent division by zero
sig(sig == 0) = 1;

normalizedData = (sensorData - mu) ./ sig;

% Create sequence windows of length 10
sequenceLength = 10;
numSamples = size(normalizedData, 1) - sequenceLength;
XTrain = cell(numSamples, 1);
YTrain = cell(numSamples, 1);

for i = 1:numSamples
    % MATLAB deep learning expects (Features x SequenceLength) for LSTM
    window = normalizedData(i:(i+sequenceLength-1), :)';
    XTrain{i} = window;
    YTrain{i} = window; % Autoencoder target is the input itself!
end

disp('4. Building LSTM Autoencoder Architecture...');
% In MATLAB, an autoencoder can be built using sequence-to-sequence LSTMs 
% with a bottleneck layer in the middle.
layers = [ ...
    sequenceInputLayer(numFeatures, 'Name', 'sensor_input')
    lstmLayer(64, 'OutputMode', 'sequence', 'Name', 'encoder_lstm')
    lstmLayer(32, 'OutputMode', 'sequence', 'Name', 'bottleneck_lstm')
    lstmLayer(64, 'OutputMode', 'sequence', 'Name', 'decoder_lstm')
    fullyConnectedLayer(numFeatures, 'Name', 'reconstruction_output')
    regressionLayer('Name', 'mse_loss')];

options = trainingOptions('adam', ...
    'MaxEpochs', 5, ...
    'MiniBatchSize', 32, ...
    'Plots', 'training-progress', ...
    'Verbose', 1);

disp('5. Training Autoencoder via Deep Learning Toolbox...');
net = trainNetwork(XTrain, YTrain, layers, options);

disp('6. Exporting to ONNX...');
exportPath = fullfile(projectRoot, 'models', 'vehicle_specific_autoencoder_Toyota_Tacoma.onnx');
exportONNXNetwork(net, exportPath);

disp(['SUCCESS! Model exported to: ' exportPath]);
disp('Your FastAPI server can now be configured to load this custom ONNX model!');
