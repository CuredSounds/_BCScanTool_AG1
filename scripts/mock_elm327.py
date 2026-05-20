#!/usr/bin/env python3
"""
🏎️ Mock ELM327 Wi-Fi Socket Server (mock_elm327.py)
Acts as a mock OBD2 Wi-Fi/TCP dongle streaming controlled 2Hz Tacoma CAN bus telemetry
to allow testing live ingestion engines without physical vehicle connection.
"""

import sys
import os
import time
import socket
import csv
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MockELM327")

DEFAULT_PORT = 35000
DEFAULT_HOST = "127.0.0.1"

def find_default_baseline_csv(project_root: Path) -> Path:
    """Searches for any baseline CSV file under data/labeled/baselines/."""
    baselines_dir = project_root / "data" / "labeled" / "baselines"
    if baselines_dir.exists():
        csv_files = list(baselines_dir.rglob("*.csv"))
        if csv_files:
            # Sort to keep selection stable, preferring B2 or B1 if available
            csv_files.sort(key=lambda p: p.name)
            for f in csv_files:
                if "B2" in f.name or "baseline" in f.name:
                    return f
            return csv_files[0]
    
    # Fallback template
    return project_root / "data" / "labeled" / "baselines" / "baseline_data" / "TOYOTA_989347712041_20260517180525_B2_warm_idle_baseline.csv"

def stream_telemetry(client_socket: socket.socket, csv_path: Path, rate_hz: float):
    """Streams CSV telemetry rows over the TCP socket at specified frequency with seamless looping."""
    interval = 1.0 / rate_hz
    
    if not csv_path.exists():
        logger.error(f"Target CSV file not found: {csv_path}")
        client_socket.sendall(b"ERROR: Target baseline CSV file not found on mock server.\n")
        return

    logger.info(f"Loading telemetry source file: {csv_path.name}")
    
    # Read all rows into memory to facilitate instant seamless looping
    with open(csv_path, mode="r", encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            logger.error("The CSV file is empty!")
            client_socket.sendall(b"ERROR: Empty CSV file.\n")
            return
        
        rows = list(reader)
        if not rows:
            logger.error("No data rows found in CSV.")
            client_socket.sendall(b"ERROR: No data rows in CSV.\n")
            return

    logger.info(f"Loaded headers and {len(rows)} data rows. Initializing streaming sequence...")
    
    # Send headers first
    header_str = ",".join(headers) + "\n"
    client_socket.sendall(header_str.encode("utf-8"))
    
    row_count = 0
    while True:
        for row in rows:
            row_str = ",".join(row) + "\n"
            try:
                client_socket.sendall(row_str.encode("utf-8"))
                row_count += 1
                if row_count % 20 == 0:
                    logger.info(f"Streamed {row_count} rows successfully.")
                time.sleep(interval)
            except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                logger.warning(f"Client disconnected: {e}")
                return

def main():
    parser = argparse.ArgumentParser(description="Mock ELM327 Wi-Fi Socket Server")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"TCP port to listen on (default: {DEFAULT_PORT})")
    parser.add_argument("--host", type=str, default=DEFAULT_HOST, help=f"IP address to bind to (default: {DEFAULT_HOST})")
    parser.add_argument("--csv", type=str, default=None, help="Path to specific baseline CSV file to stream")
    parser.add_argument("--rate", type=float, default=2.0, help="Streaming rate in Hz (default: 2.0)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    
    if args.csv:
        csv_path = Path(args.csv)
    else:
        csv_path = find_default_baseline_csv(project_root)
        
    logger.info("=" * 60)
    logger.info("   🏎️  BCScanTool Mock ELM327 Dongle Active  🏎️")
    logger.info("=" * 60)
    logger.info(f"Host IP:     {args.host}")
    logger.info(f"Port:        {args.port}")
    logger.info(f"Stream Rate: {args.rate} Hz (0.5s interval)")
    logger.info(f"Source file: {csv_path}")
    logger.info("=" * 60)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((args.host, args.port))
    except Exception as e:
        logger.error(f"Failed to bind socket on {args.host}:{args.port} - {e}")
        sys.exit(1)
        
    server_socket.listen(5)
    logger.info(f"Listening for connections on port {args.port}...")

    try:
        while True:
            client_sock, addr = server_socket.accept()
            logger.info(f"Client connected from: {addr[0]}:{addr[1]}")
            try:
                stream_telemetry(client_sock, csv_path, args.rate)
            except Exception as e:
                logger.error(f"Error during stream execution: {e}")
            finally:
                client_sock.close()
                logger.info("Connection closed. Waiting for new client...")
    except KeyboardInterrupt:
        logger.info("\nShutting down Mock ELM327 server.")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
