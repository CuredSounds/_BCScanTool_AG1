#!/usr/bin/env python3
"""
LAUNCH X431 Diagnostic Log Parser

Unified parser for .x431 binary files, supporting both raw and clean 
Excel-friendly output formats.

Author: Neural Harmonics Lab
"""

import struct
import csv
from pathlib import Path
from typing import List, Tuple, Dict, Any


class X431Parser:
    """Parser for LAUNCH X431 diagnostic log files."""

    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.file_data = self._read_file()
        self.point_values: List[str] = []
        self.column_count = 0

    def _read_file(self) -> bytes:
        """Read the entire file into memory."""
        with open(self.filepath, 'rb') as f:
            return f.read()

    def _read_uint8(self, offset: int) -> int:
        """Read unsigned 8-bit integer at offset."""
        return struct.unpack_from('<B', self.file_data, offset)[0]

    def _read_uint16(self, offset: int) -> int:
        """Read unsigned 16-bit little-endian integer at offset."""
        return struct.unpack_from('<H', self.file_data, offset)[0]

    def _read_uint32(self, offset: int) -> int:
        """Read unsigned 32-bit little-endian integer at offset."""
        return struct.unpack_from('<I', self.file_data, offset)[0]

    def _extract_channel_count(self) -> int:
        """
        Extract the number of data channels/columns.
        Fixed to read as uint32 to support 200+ parameters.
        """
        return self._read_uint32(0x134) // 4

    def _extract_point_values(self) -> List[str]:
        """Extract all point value strings from the file."""
        offset = 0x0c
        var32 = self._read_uint32(offset)
        offset += 4 + var32

        # Skip 8 header sections
        for _ in range(8):
            var16 = self._read_uint16(offset)
            offset += var16

        # Read all point values
        point_values = []
        file_size = len(self.file_data)

        while offset < file_size:
            if offset + 2 > file_size:
                break

            var16 = self._read_uint16(offset)
            offset += 2

            if var16 < 3 or offset + var16 - 2 > file_size:
                break

            # Extract string (null-terminated)
            value_bytes = self.file_data[offset:offset + var16 - 3]
            try:
                value = value_bytes.decode('utf-8', errors='ignore')
                point_values.append(value)
            except Exception:
                point_values.append("")

            offset += var16 - 2

        return point_values

    def _clean_parameter_name(self, name: str) -> str:
        """Clean and simplify parameter names for Excel."""
        if not name:
            return "Unknown"
        
        name = name.strip()
        
        # Common abbreviations and cleaning
        replacements = {
            'B1S1': '(Bank1 Sensor1)',
            'B2S1': '(Bank2 Sensor1)',
            'A/F': 'Air/Fuel',
            'A/C': 'AC',
            'Cat OT MF F/C': 'Catalyst Misfire',
            '#': 'Count',
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        return name

    def _get_headers(self, clean: bool = True) -> List[str]:
        """Extract column header names."""
        headers = ["Row"] if clean else ["Num"]
        offset = 0x138

        # Collect parameter names
        param_names = []
        for i in range(self.column_count):
            index = self._read_uint16(offset)
            offset += 4
            if index != 0 and (index - 0x09) < len(self.point_values):
                param_names.append(self.point_values[index - 0x09])
            else:
                param_names.append(f"Channel_{i + 1}")

        # Collect units
        units = []
        for i in range(self.column_count):
            index = self._read_uint16(offset)
            offset += 4
            if index != 0 and (index - 0x09) < len(self.point_values):
                units.append(self.point_values[index - 0x09])
            else:
                units.append("")

        # Combine into headers
        for i, (param, unit) in enumerate(zip(param_names, units)):
            if clean:
                p_clean = self._clean_parameter_name(param)
                u_clean = self._clean_parameter_name(unit)
                if u_clean and u_clean != p_clean and u_clean != "Unknown":
                    headers.append(f"{p_clean} [{u_clean}]")
                else:
                    headers.append(p_clean)
            else:
                headers.append(f"{i + 1}. {param} ({unit})")

        return headers

    def _get_data_rows(self) -> List[List[str]]:
        """Extract all data rows from the file."""
        offset = 0x11c
        var16 = self._read_uint16(offset)
        offset = var16 + 8

        # Fixed to read records count as uint32
        records_count = self._read_uint32(offset)
        offset += 8

        total_rows = (records_count // 4) // self.column_count
        rows = []

        for row_num in range(total_rows):
            row = [str(row_num + 1)]
            for _ in range(self.column_count):
                if offset + 2 > len(self.file_data):
                    row.append("0")
                    continue
                index = self._read_uint16(offset) - 0x09
                offset += 4
                if 0 <= index < len(self.point_values):
                    row.append(self.point_values[index])
                else:
                    row.append("0")
            rows.append(row)

        return rows

    def to_csv(self, output_path: Path, clean: bool = True) -> int:
        """
        Parse and save as CSV.
        
        Args:
            output_path: Path to save the CSV
            clean: Whether to use clean, Excel-friendly headers
            
        Returns:
            Number of rows exported
        """
        self.column_count = self._extract_channel_count()
        self.point_values = self._extract_point_values()
        
        headers = self._get_headers(clean=clean)
        rows = self._get_data_rows()

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
            
        return len(rows)


def convert_file(input_path: Path, output_path: Path = None, clean: bool = True) -> Path:
    """Convenience function to convert a single file."""
    input_path = Path(input_path)
    if output_path is None:
        suffix = "_clean.csv" if clean else ".csv"
        output_path = input_path.parent / (input_path.stem + suffix)
    
    parser = X431Parser(input_path)
    parser.to_csv(output_path, clean=clean)
    return output_path
