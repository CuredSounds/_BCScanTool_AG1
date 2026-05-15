cd '/Users/sonic.design/Documents/GitHub/_BCScanTool-v1/matlab/data'
% Find the most recent Toyota session (searching recursively)
files = dir('**/*TOYOTA*.mat');
if ~isempty(files)
    % Sort by date to get the newest
    [~, idx] = sort([files.datenum], 'descend');
    latest_file = fullfile(files(idx(1)).folder, files(idx(1)).name);
    fprintf('Loading: %s\n', latest_file);
    load(latest_file);
    whos
else
    fprintf('No Toyota .mat files found in %s\n', pwd);
end