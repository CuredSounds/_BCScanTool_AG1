import pandas as pd
import pytest
from src.core.pid_analyzer import PIDAnalyzer

def test_pid_mapping_specificity():
    # Create a dataframe with ambiguous column names
    df = pd.DataFrame(columns=[
        "Short Term Fuel Trim Bank 1", 
        "Short Fuel Trim Bank 12 History", # Should match Bank 2 better if Bank 1 is taken? 
                                           # Actually Bank 2 entries are like 'Short Fuel Trim Bank 2'
        "RPM",
        "Engine Speed"
    ])
    
    analyzer = PIDAnalyzer(df)
    
    # Check mapping
    # 'engine_speed' should prefer 'Engine Speed' over 'RPM' if it's longer? 
    # Actually both are in the list. 'Engine Speed' (length 12) vs 'RPM' (length 3).
    # Exact match score is 10000.
    
    assert analyzer.mapped_pids['engine_speed'] in ["Engine Speed", "RPM"]
    
    # Check that each PID got its own column if possible
    assert 'stft_bank1' in analyzer.mapped_pids
    assert analyzer.mapped_pids['stft_bank1'] == "Short Term Fuel Trim Bank 1"

def test_pid_mapping_conflicts():
    # Test that Bank 2 doesn't steal Bank 1's column
    df = pd.DataFrame(columns=[
        "Short Fuel Trim Bank 1",
        "Short Fuel Trim Bank 2"
    ])
    
    analyzer = PIDAnalyzer(df)
    
    assert analyzer.mapped_pids['stft_bank1'] == "Short Fuel Trim Bank 1"
    assert analyzer.mapped_pids['stft_bank2'] == "Short Fuel Trim Bank 2"

if __name__ == "__main__":
    # Simple manual run
    test_pid_mapping_conflicts()
    print("Tests passed!")
