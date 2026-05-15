%% MATLAB Script to query BCScanTool Diagnostics Database
% This script demonstrates how to load diagnostic data directly from the
% SQLite database into MATLAB for analysis.

% 1. Connection Details
dbPath = '../data/diagnostics.db';

% Check if file exists
if ~exist(dbPath, 'file')
    error('Database not found at %s. Please run scripts/import_to_db.py first.', dbPath);
end

% 2. Connect to SQLite database
% Note: MATLAB's sqlite function is part of the Database Toolbox
% If you don't have it, you can use the community SQLite driver or 
% export to .mat from Python as described in the Integration Guide.
try
    conn = sqlite(dbPath);
    fprintf('Connected to database: %s\n', dbPath);
catch
    error('Could not connect to database. Ensure Database Toolbox is installed.');
end

% 3. List available vehicles
vehicles = fetch(conn, 'SELECT * FROM vehicles');
disp('Available Vehicles:');
disp(vehicles);

% 4. List recent sessions with their labels (classifiers)
sessions = fetch(conn, 'SELECT s.id, v.make, s.label, s.timestamp FROM sessions s JOIN vehicles v ON s.vehicle_id = v.id ORDER BY s.id DESC LIMIT 10');
disp('Recent Sessions:');
disp(sessions);

% 5. Query data for a specific session (e.g., Session 1)
% This query pivots the normalized data into a wide format suitable for MATLAB
sessionId = 1;
query = ['SELECT r.row_index, p.name, r.value ' ...
         'FROM readings r ' ...
         'JOIN parameters p ON r.parameter_id = p.id ' ...
         'WHERE r.session_id = ' num2str(sessionId) ' ' ...
         'ORDER BY r.row_index, p.name'];

rawData = fetch(conn, query);

% Convert to table
data = cell2table(rawData, 'VariableNames', {'Row', 'Parameter', 'Value'});

% Pivot data to have parameters as columns
% (Note: unstack is useful here if you have many parameters)
pivotedData = unstack(data, 'Value', 'Parameter');

% 6. Visualization Example
if ismember('Engine_Speed_rpm_', pivotedData.Properties.VariableNames)
    figure;
    plot(pivotedData.Row, pivotedData.Engine_Speed_rpm_);
    title(['Engine Speed - Session ' num2str(sessionId)]);
    xlabel('Sample index');
    ylabel('RPM');
    grid on;
end

% Close connection
close(conn);
