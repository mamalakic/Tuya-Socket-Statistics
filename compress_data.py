import csv
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

CSV_FILE = "power_data.csv"
COMPRESSION_FACTOR = 12  # Average every 12 rows

def compress_data():
    if not os.path.exists(CSV_FILE):
        print(f"File {CSV_FILE} not found")
        return

    # Read the CSV file
    df = pd.read_csv(CSV_FILE)
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Sort by timestamp to ensure correct grouping
    df = df.sort_values('timestamp')
    
    # Create a temporary column for grouping
    df['group'] = np.arange(len(df)) // COMPRESSION_FACTOR
    
    # Group by the temporary column and calculate averages
    compressed_df = df.groupby('group').agg({
        'timestamp': 'first',  # Keep the first timestamp of each group
        'current_ma': 'mean',
        'power_w': 'mean',
        'voltage_v': 'mean'
    }).reset_index(drop=True)
    
    # Create backup of original file
    backup_file = f"{CSV_FILE}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.rename(CSV_FILE, backup_file)
    
    # Save compressed data
    compressed_df.to_csv(CSV_FILE, index=False)
    
    # Print compression statistics
    original_size = os.path.getsize(backup_file)
    compressed_size = os.path.getsize(CSV_FILE)
    reduction = (1 - compressed_size / original_size) * 100
    
    print(f"Compression complete:")
    print(f"Original size: {original_size/1024:.2f} KB")
    print(f"Compressed size: {compressed_size/1024:.2f} KB")
    print(f"Reduction: {reduction:.1f}%")
    print(f"Original rows: {len(df)}")
    print(f"Compressed rows: {len(compressed_df)}")
    print(f"Backup saved as: {backup_file}")

if __name__ == "__main__":
    compress_data() 