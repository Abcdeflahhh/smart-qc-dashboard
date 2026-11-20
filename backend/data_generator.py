#!/usr/bin/env python3
"""
Smart QC Dashboard - Data Generator
Generates simulated QC production inspection dataset with 500 rows.
Includes normal production data and injected extreme anomalies.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Ensure we can import from parent directory if needed
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_qc_dataset(n_rows: int = 500, seed: int = 42) -> pd.DataFrame:
    """
    Generate simulated QC production inspection data.

    Parameters:
        n_rows: Number of rows to generate (default 500)
        seed: Random seed for reproducibility

    Returns:
        DataFrame with columns: timestamp, batch_id, line_id, temperature_c,
        pressure_bar, dimension_mm, defect_type, status
    """
    np.random.seed(seed)

    # Configuration
    start_time = datetime(2024, 1, 1, 6, 0, 0)  # Jan 1, 2024 06:00
    lines = ['LINE-A', 'LINE-B', 'LINE-C', 'LINE-D']
    defect_types = [
        'NONE',           # No defect
        'SCRATCH',        # Surface scratch
        'DENT',           # Dents/deformation
        'CRACK',          # Cracks
        'DIMENSIONAL',    # Out of spec dimensions
        'CONTAMINATION',  # Foreign material
        'BURR',           # Burrs/flash
        'WARPAGE',        # Warping
        'DISCOLORATION',  # Color variation
        'INCOMPLETE'      # Incomplete fill/mold
    ]
    defect_weights = [0.72, 0.08, 0.05, 0.03, 0.04, 0.02, 0.02, 0.02, 0.01, 0.01]

    # Normal process parameters (in-control)
    normal_params = {
        'temperature_c': {'mean': 220.0, 'std': 5.0, 'min': 205, 'max': 235},
        'pressure_bar': {'mean': 85.0, 'std': 3.0, 'min': 75, 'max': 95},
        'dimension_mm': {'mean': 50.0, 'std': 0.15, 'min': 49.5, 'max': 50.5},
    }

    # Specification limits
    spec_limits = {
        'temperature_c': (200, 240),
        'pressure_bar': (70, 100),
        'dimension_mm': (49.7, 50.3),
    }

    data = []

    for i in range(n_rows):
        # Timestamp - roughly 1 inspection per minute across shifts
        minutes_offset = i * np.random.uniform(0.5, 2.5)
        timestamp = start_time + timedelta(minutes=minutes_offset)

        # Batch ID - changes every ~25-50 parts
        batch_num = (i // np.random.randint(25, 51)) + 1
        batch_id = f"BATCH-{batch_num:04d}"

        # Production line
        line_id = np.random.choice(lines, p=[0.3, 0.3, 0.25, 0.15])

        # Determine if this row gets an injected anomaly (5% chance)
        is_anomaly = np.random.random() < 0.05
        anomaly_type = np.random.choice(['temp_spike', 'pressure_drop', 'dim_shift', 'multi_param']) if is_anomaly else None

        # Generate process parameters
        if is_anomaly:
            if anomaly_type == 'temp_spike':
                # Extreme temperature spike
                temperature_c = np.random.uniform(260, 300)
                pressure_bar = np.random.normal(normal_params['pressure_bar']['mean'], normal_params['pressure_bar']['std'])
                dimension_mm = np.random.normal(normal_params['dimension_mm']['mean'], normal_params['dimension_mm']['std'])
            elif anomaly_type == 'pressure_drop':
                # Sudden pressure loss
                temperature_c = np.random.normal(normal_params['temperature_c']['mean'], normal_params['temperature_c']['std'])
                pressure_bar = np.random.uniform(30, 55)
                dimension_mm = np.random.normal(normal_params['dimension_mm']['mean'], normal_params['dimension_mm']['std'])
            elif anomaly_type == 'dim_shift':
                # Tool wear causing dimensional shift
                temperature_c = np.random.normal(normal_params['temperature_c']['mean'], normal_params['temperature_c']['std'])
                pressure_bar = np.random.normal(normal_params['pressure_bar']['mean'], normal_params['pressure_bar']['std'])
                dimension_mm = np.random.uniform(50.8, 52.5)  # Way out of spec
            elif anomaly_type == 'multi_param':
                # Multiple parameter excursion (e.g., machine malfunction)
                temperature_c = np.random.uniform(250, 280)
                pressure_bar = np.random.uniform(110, 130)
                dimension_mm = np.random.uniform(48.5, 49.0)  # Undersize
        else:
            # Normal production variation
            temperature_c = np.random.normal(normal_params['temperature_c']['mean'], normal_params['temperature_c']['std'])
            pressure_bar = np.random.normal(normal_params['pressure_bar']['mean'], normal_params['pressure_bar']['std'])
            dimension_mm = np.random.normal(normal_params['dimension_mm']['mean'], normal_params['dimension_mm']['std'])

        # Clip normal values to reasonable ranges (anomalies stay extreme)
        if not is_anomaly:
            temperature_c = np.clip(temperature_c, normal_params['temperature_c']['min'], normal_params['temperature_c']['max'])
            pressure_bar = np.clip(pressure_bar, normal_params['pressure_bar']['min'], normal_params['pressure_bar']['max'])
            dimension_mm = np.clip(dimension_mm, normal_params['dimension_mm']['min'], normal_params['dimension_mm']['max'])

        # Determine defect type based on process conditions
        # Higher chance of defects when parameters are out of spec
        temp_oos = temperature_c < spec_limits['temperature_c'][0] or temperature_c > spec_limits['temperature_c'][1]
        press_oos = pressure_bar < spec_limits['pressure_bar'][0] or pressure_bar > spec_limits['pressure_bar'][1]
        dim_oos = dimension_mm < spec_limits['dimension_mm'][0] or dimension_mm > spec_limits['dimension_mm'][1]

        oos_count = sum([temp_oos, press_oos, dim_oos])

        # Adjust defect weights based on OOS conditions
        if oos_count >= 2:
            # Multiple OOS - high defect probability
            adj_weights = [0.15, 0.15, 0.12, 0.10, 0.20, 0.08, 0.05, 0.05, 0.05, 0.05]
        elif oos_count == 1:
            # Single OOS - moderate defect probability
            adj_weights = [0.40, 0.12, 0.08, 0.06, 0.12, 0.05, 0.04, 0.04, 0.05, 0.04]
        else:
            # In control - base weights
            adj_weights = defect_weights

        defect_type = np.random.choice(defect_types, p=adj_weights)

        # Determine PASS/REJECT status
        # Reject if: any critical OOS, or defect present (except NONE)
        is_reject = (
            oos_count >= 1 or  # Any out-of-spec parameter
            defect_type != 'NONE' or  # Any defect
            is_anomaly  # All anomalies are rejects
        )

        # Small chance of false reject (overly conservative QC) - 1%
        if not is_reject and np.random.random() < 0.01:
            is_reject = True
            defect_type = np.random.choice(['SCRATCH', 'DISCOLORATION', 'BURR'])

        # Small chance of false accept (escape) - 0.5% when should reject
        if is_reject and np.random.random() < 0.005:
            is_reject = False
            defect_type = 'NONE'

        status = 'REJECT' if is_reject else 'PASS'

        data.append({
            'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'batch_id': batch_id,
            'line_id': line_id,
            'temperature_c': round(temperature_c, 2),
            'pressure_bar': round(pressure_bar, 2),
            'dimension_mm': round(dimension_mm, 4),
            'defect_type': defect_type,
            'status': status
        })

    df = pd.DataFrame(data)
    return df


def save_dataset(df: pd.DataFrame, output_path: str) -> None:
    """Save dataset to CSV with proper directory creation."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Dataset saved to: {output_path}")
    print(f"Shape: {df.shape}")
    print(f"Status distribution:\n{df['status'].value_counts()}")
    print(f"\nDefect type distribution:\n{df['defect_type'].value_counts()}")
    print(f"\nLine distribution:\n{df['line_id'].value_counts()}")
    print(f"\nBatch count: {df['batch_id'].nunique()}")
    print(f"\nTemperature range: {df['temperature_c'].min():.2f} - {df['temperature_c'].max():.2f} °C")
    print(f"Pressure range: {df['pressure_bar'].min():.2f} - {df['pressure_bar'].max():.2f} bar")
    print(f"Dimension range: {df['dimension_mm'].min():.4f} - {df['dimension_mm'].max():.4f} mm")


def main():
    """Main entry point."""
    # Get project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_path = os.path.join(project_root, 'data', 'qc_production_logs.csv')

    print("=" * 60)
    print("Smart QC Dashboard - Data Generator")
    print("=" * 60)
    print(f"Generating 500 rows of QC production inspection data...")
    print(f"Output: {output_path}")
    print()

    # Generate dataset
    df = generate_qc_dataset(n_rows=500, seed=42)

    # Save to CSV
    save_dataset(df, output_path)

    print()
    print("=" * 60)
    print("Data generation complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()