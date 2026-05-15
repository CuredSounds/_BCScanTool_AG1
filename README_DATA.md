# OBD2 Data Usage Definitions

This project processes vehicle diagnostic data from `.x431` files into standard, high-performance formats.

## 1. Generated Data Files
After running `python obd2.py`, the following files are created in the `data/` directory:

| Filename | Format | Best For... |
| :--- | :--- | :--- |
| `obd2_dataset.parquet` | **Parquet** | **Google Cloud (BigQuery)**, Python (Pandas), **MATLAB** (R2019+), Machine Learning. *Highly recommended.* |
| `obd2_data.db` | **SQLite** | **JetBrains DataSpell**, DBeaver, SQL exploration, Local Apps. |
| `csv/Vehicle_make_model/{Make}/{Model}/` | **CSV** | Organized by vehicle. Legacy tools, quick inspection. Warning: Large size/slow. |

## 2. Integration Guides

### JetBrains DataSpell / PyCharm
1.  Open the **Database** tool window (usually on the right).
2.  Click `+` -> **Data Source** -> **SQLite**.
3.  For **File**, browse to `/Users/sonic.design/Documents/GitHub/_BCScanTool-v1/data/obd2_data.db`.
4.  Click **Test Connection** (download drivers if asked).
5.  You can now run SQL queries like:
    ```sql
    SELECT Source_File, AVG(`Engine RPM`)
    FROM sensor_data
    GROUP BY Source_File
    ```

### Google Cloud Platform (GCP)
1.  **Storage**: Upload `obd2_dataset.parquet` to a Google Cloud Storage (GCS) bucket.
2.  **BigQuery**:
    *   Create a dataset.
    *   Create a table from **Upload** (select your Parquet file).
    *   Select **Source Format**: Parquet.
    *   This is much faster and cheaper than CSV import.
    *   You can then connect Vertex AI or Auto ML directly to BigQuery.

### MATLAB
Modern MATLAB (R2019b+) supports Parquet natively:
```matlab
% Effective way to load
T = parquetread('data/obd2_dataset.parquet');
summary(T);

% Train a model
% regressionLearner(T, 'TargetColumn');
```
If using an older version, use the CSV files in `data/csv/`.

## 3. Workflow: Adding More Data
The `obd2.py` script works incrementally:

1.  **Connect Device**: Ensure your Android device is mounted.
2.  **Run Script**: `python3 obd2.py`
3.  **Process**:
    *   It checks for **new** `.x431` files in the source directory.
    *   It copies ONLY the new files to `data/raw_x431`.
    *   It converts ONLY the new files to CSV.
    *   It **rebuilds** the Parquet and SQLite databases with the full dataset (processed + new).
4.  **Result**: Your `obd2_dataset.parquet` and `obd2_data.db` stay up to date with all historical data.

*Tip: If you want to force a full re-process, delete the `data/csv` directory.*
