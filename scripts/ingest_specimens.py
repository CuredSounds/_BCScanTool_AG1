import os
import json
import numpy as np
import librosa

# Define absolute paths based on the directory structure
BASE_DIR = os.path.join(os.getcwd(), "cured_sounds_assets")
INCOMING_DIR = os.path.join(BASE_DIR, "incoming")
SPECIMENS_DIR = os.path.join(BASE_DIR, "specimens")
FEATURES_DIR = os.path.join(SPECIMENS_DIR, "features")
MASTER_METADATA_FILE = os.path.join(SPECIMENS_DIR, "metadata.json")

# Ensure directories exist
for folder in [INCOMING_DIR, SPECIMENS_DIR, FEATURES_DIR]:
    os.makedirs(folder, exist_ok=True)

def extract_tinyml_features(audio_path, sample_rate=22050):
    """
    Extracts high-value, lightweight acoustic features that an ARM Cortex-M7
    can realistically compute or utilize for target matching.
    """
    # Load audio (force mono for consistent analysis)
    y, sr = librosa.load(audio_path, sr=sample_rate, mono=True)
    
    # 1. Spectral Centroid (Brightness)
    spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    
    # 2. Zero-Crossing Rate (Noisiness / Transient roughness)
    zero_crossings = librosa.feature.zero_crossing_rate(y=y)[0]
    
    # 3. MFCCs (Mel-Frequency Cepstral Coefficients - 13 coefficients for timbral shape)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    
    # Calculate global statistical summaries for the ML profile
    feature_summary = {
        "spectral_centroid_mean": float(np.mean(spectral_centroids)),
        "spectral_centroid_std": float(np.std(spectral_centroids)),
        "zero_crossing_rate_mean": float(np.mean(zero_crossings)),
        "mfcc_means": [float(m) for m in np.mean(mfccs, axis=1)]
    }
    
    # Save the raw time-series arrays for deep neural training later
    time_series_data = {
        "spectral_centroid": spectral_centroids.tolist() if isinstance(spectral_centroids, np.ndarray) else spectral_centroids,
        "zero_crossings": zero_crossings.tolist() if isinstance(zero_crossings, np.ndarray) else zero_crossings,
        "mfccs": mfccs.tolist() if isinstance(mfccs, np.ndarray) else mfccs
    }
    
    return feature_summary, time_series_data

def ingest_new_specimens():
    # Load existing master metadata or create a new database dictionary
    if os.path.exists(MASTER_METADATA_FILE):
        with open(MASTER_METADATA_FILE, 'r') as f:
            master_catalog = json.load(f)
    else:
        master_catalog = {}

    # Scan incoming directory for WAV files
    incoming_files = [f for f in os.listdir(INCOMING_DIR) if f.endswith('.wav')]
    
    if not incoming_files:
        print("No new WAV files found in incoming directory.")
        return

    print(f"Found {len(incoming_files)} new specimen(s) to process...")

    for audio_file in incoming_files:
        specimen_id = os.path.splitext(audio_file)[0]
        audio_path = os.path.join(INCOMING_DIR, audio_file)
        
        # Look for a matching .txt file containing field notes
        notes_path = audio_path.replace('.wav', '.txt')
        field_notes = {
            "description": "Unknown field recording",
            "location": "Ohio Woodlot",
            "temperature": "Unknown",
            "time_of_day": "Unknown"
        }
        
        if os.path.exists(notes_path):
            try:
                with open(notes_path, 'r') as f:
                    # Expect simple lines like: description=Northern Cardinal
                    for line in f:
                        if '=' in line:
                            k, v = line.strip().split('=', 1)
                            field_notes[k.lower()] = v
            except Exception as e:
                print(f"Error reading field notes for {specimen_id}: {e}")

        print(f"Analyzing audio for {specimen_id}...")
        try:
            # Run librosa extraction
            summary, raw_series = extract_tinyml_features(audio_path)
            
            # Move the physical audio file to the permanent specimens home
            permanent_audio_path = os.path.join(SPECIMENS_DIR, audio_file)
            os.rename(audio_path, permanent_audio_path)
            
            # Clean up the processed notes file if it existed
            if os.path.exists(notes_path):
                os.remove(notes_path)
                
            # Save raw time-series matrices as binary numpy arrays for super-fast ML loading
            np_feature_path = os.path.join(FEATURES_DIR, f"{specimen_id}_features.npy")
            np.save(np_feature_path, raw_series, allow_pickle=True)
            
            # Compile master entry
            master_catalog[specimen_id] = {
                "file_path": permanent_audio_path,
                "feature_file_path": np_feature_path,
                "metadata": field_notes,
                "acoustic_profile": summary
            }
            print(f"Successfully cataloged {specimen_id}!")
            
        except Exception as e:
            print(f"Failed to process {specimen_id}: {e}")
            
    # Write updated catalog back to disk
    with open(MASTER_METADATA_FILE, 'w') as f:
        json.dump(master_catalog, f, indent=4)
    print("Master metadata catalog updated successfully.")

if __name__ == "__main__":
    ingest_new_specimens()
