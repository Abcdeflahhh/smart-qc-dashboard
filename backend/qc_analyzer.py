#!/usr/bin/env python3
"""
Smart QC Dashboard - QC Analyzer Module
Reads qc_production_logs.csv and provides:
1. KPI Summary (Total Inspections, Pass Rate, Defect Rate, OEE Score)
2. Anomaly Detection (Z-Score & IQR methods)
3. Defect Trend Aggregation (per batch & per line)
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class QCAnalyzer:
    """Quality Control Data Analyzer for production inspection data."""

    def __init__(self, data_path: str = None):
        """
        Initialize analyzer with data path.

        Args:
            data_path: Path to qc_production_logs.csv. Defaults to data/ in project root.
        """
        if data_path is None:
            project_root = Path(__file__).parent.parent
            data_path = project_root / 'data' / 'qc_production_logs.csv'

        self.data_path = Path(data_path)
        self.df: Optional[pd.DataFrame] = None
        self._load_data()

    def _load_data(self) -> None:
        """Load and validate CSV data."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data file not found: {self.data_path}")

        self.df = pd.read_csv(self.data_path)

        # Ensure proper dtypes
        self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])
        numeric_cols = ['temperature_c', 'pressure_bar', 'dimension_mm']
        for col in numeric_cols:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        # Sort by timestamp
        self.df = self.df.sort_values('timestamp').reset_index(drop=True)

    # ============================================================
    # 1. KPI SUMMARY
    # ============================================================
    def calculate_kpis(self) -> Dict[str, Any]:
        """
        Calculate main KPIs for QC dashboard.

        Returns:
            Dict with keys: total_inspections, pass_count, reject_count,
                           pass_rate_pct, defect_rate_pct, oee_score,
                           availability_pct, performance_pct, quality_pct
        """
        if self.df is None or len(self.df) == 0:
            return self._empty_kpis()

        total = len(self.df)
        pass_count = (self.df['status'] == 'PASS').sum()
        reject_count = (self.df['status'] == 'REJECT').sum()

        pass_rate = (pass_count / total) * 100 if total > 0 else 0
        defect_rate = (reject_count / total) * 100 if total > 0 else 0

        # OEE Simulation (simplified)
        # Availability: % of scheduled time actually running (assume 95% baseline - downtime from rejects)
        # Performance: % of ideal throughput achieved (assume 90% baseline - slowdowns from anomalies)
        # Quality: Pass rate (first-pass yield)

        # Availability: reduce by reject ratio impact (each reject = ~2 min downtime in 8hr shift)
        shift_minutes = 8 * 60
        est_downtime_min = reject_count * 2
        availability = max(0, (shift_minutes - est_downtime_min) / shift_minutes) * 100
        availability = min(availability, 100)  # cap at 100%

        # Performance: reduce by anomaly ratio (anomalies = process instability)
        anomaly_ratio = self._get_anomaly_ratio()
        performance = max(0, 95 - anomaly_ratio * 20)  # baseline 95%, drops with anomalies

        # Quality = Pass Rate (First Pass Yield)
        quality = pass_rate

        # OEE = Availability * Performance * Quality / 10000
        oee = (availability * performance * quality) / 10000

        return {
            'total_inspections': int(total),
            'pass_count': int(pass_count),
            'reject_count': int(reject_count),
            'pass_rate_pct': round(pass_rate, 2),
            'defect_rate_pct': round(defect_rate, 2),
            'oee_score': round(oee, 2),
            'availability_pct': round(availability, 2),
            'performance_pct': round(performance, 2),
            'quality_pct': round(quality, 2),
            'unique_batches': int(self.df['batch_id'].nunique()),
            'unique_lines': int(self.df['line_id'].nunique()),
            'date_range': {
                'start': self.df['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S'),
                'end': self.df['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
            }
        }

    def _get_anomaly_ratio(self) -> float:
        """Estimate anomaly ratio for performance calculation."""
        # Use IQR outliers as proxy
        params = ['temperature_c', 'pressure_bar', 'dimension_mm']
        total_outliers = 0
        for param in params:
            Q1 = self.df[param].quantile(0.25)
            Q3 = self.df[param].quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            outliers = ((self.df[param] < lower) | (self.df[param] > upper)).sum()
            total_outliers += outliers
        return total_outliers / (len(self.df) * len(params)) if len(self.df) > 0 else 0

    def _empty_kpis(self) -> Dict[str, Any]:
        """Return empty KPI structure."""
        return {
            'total_inspections': 0, 'pass_count': 0, 'reject_count': 0,
            'pass_rate_pct': 0.0, 'defect_rate_pct': 0.0, 'oee_score': 0.0,
            'availability_pct': 0.0, 'performance_pct': 0.0, 'quality_pct': 0.0,
            'unique_batches': 0, 'unique_lines': 0,
            'date_range': {'start': None, 'end': None}
        }

    # ============================================================
    # 2. ANOMALY DETECTION (Z-Score & IQR)
    # ============================================================
    def detect_anomalies(
        self,
        columns: List[str] = None,
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5
    ) -> pd.DataFrame:
        """
        Detect anomalies using both Z-Score and IQR methods.

        Args:
            columns: List of columns to check. Defaults to process parameters.
            z_threshold: Z-score threshold for anomaly (default 3.0 = 99.73% CI)
            iqr_multiplier: IQR multiplier for outlier bounds (default 1.5)

        Returns:
            DataFrame with anomaly flags and reasons for each row
        """
        if self.df is None or len(self.df) == 0:
            return pd.DataFrame()

        if columns is None:
            columns = ['temperature_c', 'pressure_bar', 'dimension_mm']

        results = []

        for idx, row in self.df.iterrows():
            anomaly_info = {
                'index': idx,
                'timestamp': row['timestamp'],
                'batch_id': row['batch_id'],
                'line_id': row['line_id'],
                'is_anomaly': False,
                'anomaly_methods': [],
                'anomaly_params': [],
                'anomaly_reasons': [],
                'z_scores': {},
                'iqr_flags': {}
            }

            for col in columns:
                val = row[col]
                if pd.isna(val):
                    continue

                # Z-Score method
                mean_val = self.df[col].mean()
                std_val = self.df[col].std()
                if std_val > 0:
                    z_score = (val - mean_val) / std_val
                    anomaly_info['z_scores'][col] = round(z_score, 3)
                    if abs(z_score) > z_threshold:
                        anomaly_info['is_anomaly'] = True
                        anomaly_info['anomaly_methods'].append('Z-Score')
                        anomaly_info['anomaly_params'].append(col)
                        direction = 'tinggi' if z_score > 0 else 'rendah'
                        anomaly_info['anomaly_reasons'].append(
                            f"{col}: Z-Score {z_score:.2f} (>{z_threshold}) -> nilai {direction} ekstrem, "
                            f"mean={mean_val:.2f}, std={std_val:.2f}"
                        )

                # IQR method
                Q1 = self.df[col].quantile(0.25)
                Q3 = self.df[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - iqr_multiplier * IQR
                upper_bound = Q3 + iqr_multiplier * IQR

                anomaly_info['iqr_flags'][col] = {
                    'Q1': round(Q1, 3),
                    'Q3': round(Q3, 3),
                    'IQR': round(IQR, 3),
                    'lower_bound': round(lower_bound, 3),
                    'upper_bound': round(upper_bound, 3),
                    'is_outlier': val < lower_bound or val > upper_bound
                }

                if anomaly_info['iqr_flags'][col]['is_outlier']:
                    anomaly_info['is_anomaly'] = True
                    if 'IQR' not in anomaly_info['anomaly_methods']:
                        anomaly_info['anomaly_methods'].append('IQR')
                    anomaly_info['anomaly_params'].append(col)
                    direction = 'di atas upper bound' if val > upper_bound else 'di bawah lower bound'
                    anomaly_info['anomaly_reasons'].append(
                        f"{col}: {val:.2f} {direction} (IQR bounds: {lower_bound:.2f} - {upper_bound:.2f}, "
                        f"Q1={Q1:.2f}, Q3={Q3:.2f}, IQR={IQR:.2f})"
                    )

            # Deduplicate params
            anomaly_info['anomaly_params'] = list(set(anomaly_info['anomaly_params']))
            anomaly_info['anomaly_methods'] = list(set(anomaly_info['anomaly_methods']))

            results.append(anomaly_info)

        return pd.DataFrame(results)

    def get_anomaly_summary(self, anomalies_df: pd.DataFrame = None) -> Dict[str, Any]:
        """
        Get summary statistics of detected anomalies.

        Args:
            anomalies_df: Output from detect_anomalies(). If None, runs detection.

        Returns:
            Dict with anomaly counts by method, parameter, line, batch
        """
        if anomalies_df is None:
            anomalies_df = self.detect_anomalies()

        if len(anomalies_df) == 0:
            return {'total_anomalies': 0, 'anomaly_rate_pct': 0.0}

        anomaly_rows = anomalies_df[anomalies_df['is_anomaly'] == True]
        total_anomalies = len(anomaly_rows)
        total_rows = len(anomalies_df)

        # By method
        method_counts = {}
        for methods in anomaly_rows['anomaly_methods']:
            for m in methods:
                method_counts[m] = method_counts.get(m, 0) + 1

        # By parameter
        param_counts = {}
        for params in anomaly_rows['anomaly_params']:
            for p in params:
                param_counts[p] = param_counts.get(p, 0) + 1

        # By line
        line_counts = anomaly_rows['line_id'].value_counts().to_dict()

        # By batch
        batch_counts = anomaly_rows['batch_id'].value_counts().to_dict()

        return {
            'total_anomalies': int(total_anomalies),
            'anomaly_rate_pct': round((total_anomalies / total_rows) * 100, 2),
            'by_method': method_counts,
            'by_parameter': param_counts,
            'by_line': line_counts,
            'by_batch': batch_counts,
            'anomaly_indices': anomaly_rows['index'].tolist()
        }

    # ============================================================
    # 3. DEFECT TREND AGGREGATION
    # ============================================================
    def aggregate_defects_by_batch(self) -> pd.DataFrame:
        """
        Aggregate defect counts and rates per batch.

        Returns:
            DataFrame with batch-level defect statistics
        """
        if self.df is None or len(self.df) == 0:
            return pd.DataFrame()

        # Total per batch
        batch_totals = self.df.groupby('batch_id').size().rename('total_inspections')

        # Pass/Reject counts
        status_counts = self.df.groupby(['batch_id', 'status']).size().unstack(fill_value=0)
        status_counts.columns = [f'{c.lower()}_count' for c in status_counts.columns]

        # Defect type breakdown (excluding NONE)
        defect_df = self.df[self.df['defect_type'] != 'NONE']
        defect_counts = defect_df.groupby(['batch_id', 'defect_type']).size().unstack(fill_value=0)
        defect_counts.columns = [f'defect_{c.lower()}' for c in defect_counts.columns]

        # Line distribution per batch
        line_counts = self.df.groupby(['batch_id', 'line_id']).size().unstack(fill_value=0)
        line_counts.columns = [f'line_{c}' for c in line_counts.columns]

        # Combine
        result = pd.concat([batch_totals, status_counts, defect_counts, line_counts], axis=1).fillna(0)

        # Calculate rates
        if 'pass_count' in result.columns:
            result['pass_rate_pct'] = (result['pass_count'] / result['total_inspections'] * 100).round(2)
        if 'reject_count' in result.columns:
            result['defect_rate_pct'] = (result['reject_count'] / result['total_inspections'] * 100).round(2)

        # Add date range per batch
        date_range = self.df.groupby('batch_id')['timestamp'].agg(['min', 'max'])
        date_range.columns = ['batch_start', 'batch_end']
        result = result.join(date_range)

        # Sort by batch_start
        result = result.sort_values('batch_start').reset_index()

        # Convert numeric columns to int
        int_cols = [c for c in result.columns if result[c].dtype in ['float64', 'int64'] and 'rate' not in c.lower() and 'pct' not in c.lower()]
        for col in int_cols:
            if col in result.columns:
                result[col] = result[col].astype(int)

        return result

    def aggregate_defects_by_line(self) -> pd.DataFrame:
        """
        Aggregate defect counts and rates per production line.

        Returns:
            DataFrame with line-level defect statistics
        """
        if self.df is None or len(self.df) == 0:
            return pd.DataFrame()

        # Total per line
        line_totals = self.df.groupby('line_id').size().rename('total_inspections')

        # Pass/Reject counts
        status_counts = self.df.groupby(['line_id', 'status']).size().unstack(fill_value=0)
        status_counts.columns = [f'{c.lower()}_count' for c in status_counts.columns]

        # Defect type breakdown
        defect_df = self.df[self.df['defect_type'] != 'NONE']
        defect_counts = defect_df.groupby(['line_id', 'defect_type']).size().unstack(fill_value=0)
        defect_counts.columns = [f'defect_{c.lower()}' for c in defect_counts.columns]

        # Batch count per line
        batch_counts = self.df.groupby('line_id')['batch_id'].nunique().rename('unique_batches')

        # Process parameter stats per line
        param_stats = self.df.groupby('line_id')[['temperature_c', 'pressure_bar', 'dimension_mm']].agg(['mean', 'std', 'min', 'max'])
        param_stats.columns = [f'{c[0]}_{c[1]}' for c in param_stats.columns]

        # Combine
        result = pd.concat([line_totals, status_counts, defect_counts, batch_counts, param_stats], axis=1).fillna(0)

        # Calculate rates
        if 'pass_count' in result.columns:
            result['pass_rate_pct'] = (result['pass_count'] / result['total_inspections'] * 100).round(2)
        if 'reject_count' in result.columns:
            result['defect_rate_pct'] = (result['reject_count'] / result['total_inspections'] * 100).round(2)

        # Anomaly rate per line (using IQR)
        anomalies = self.detect_anomalies()
        anomaly_by_line = anomalies[anomalies['is_anomaly']].groupby('line_id').size().rename('anomaly_count')
        result = result.join(anomaly_by_line, how='left').fillna(0)
        result['anomaly_rate_pct'] = (result['anomaly_count'] / result['total_inspections'] * 100).round(2)

        # Convert numeric columns
        int_cols = [c for c in result.columns if result[c].dtype in ['float64', 'int64'] and 'rate' not in c.lower() and 'pct' not in c.lower() and 'mean' not in c.lower() and 'std' not in c.lower() and 'min' not in c.lower() and 'max' not in c.lower()]
        for col in int_cols:
            if col in result.columns:
                result[col] = result[col].astype(int)

        return result.reset_index()

    def get_defect_trend_timeseries(self, freq: str = 'h') -> pd.DataFrame:
        """
        Get time-series defect trend (resampled by frequency).

        Args:
            freq: Resampling frequency ('H'=hourly, 'D'=daily, '30T'=30min)

        Returns:
            DataFrame with timestamp index and defect metrics over time
        """
        if self.df is None or len(self.df) == 0:
            return pd.DataFrame()

        df_ts = self.df.set_index('timestamp')

        # Resample
        resampled = df_ts.resample(freq).agg(
            total_inspections=('status', 'size'),
            pass_count=('status', lambda x: (x == 'PASS').sum()),
            reject_count=('status', lambda x: (x == 'REJECT').sum()),
        )

        # Defect types over time
        defect_types = ['SCRATCH', 'DENT', 'CRACK', 'DIMENSIONAL', 'CONTAMINATION', 'BURR', 'WARPAGE', 'DISCOLORATION', 'INCOMPLETE']
        for dt in defect_types:
            resampled[f'defect_{dt.lower()}'] = df_ts[df_ts['defect_type'] == dt].resample(freq).size()

        resampled = resampled.fillna(0)

        # Rates
        resampled['pass_rate_pct'] = (resampled['pass_count'] / resampled['total_inspections'] * 100).round(2)
        resampled['defect_rate_pct'] = (resampled['reject_count'] / resampled['total_inspections'] * 100).round(2)

        # Process parameter averages
        param_avg = df_ts[['temperature_c', 'pressure_bar', 'dimension_mm']].resample(freq).mean()
        resampled = resampled.join(param_avg, how='left')

        return resampled.reset_index()


def main():
    """Demo function to show analyzer capabilities."""
    print("=" * 70)
    print("Smart QC Dashboard - QC Analyzer Demo")
    print("=" * 70)

    analyzer = QCAnalyzer()

    # 1. KPI Summary
    print("\n[KPI] KPI SUMMARY")
    print("-" * 40)
    kpis = analyzer.calculate_kpis()
    for k, v in kpis.items():
        if k != 'date_range':
            print(f"  {k}: {v}")
    print(f"  date_range: {kpis['date_range']['start']} -> {kpis['date_range']['end']}")

    # 2. Anomaly Detection
    print("\n[ANOMALY] ANOMALY DETECTION (Z-Score & IQR)")
    print("-" * 40)
    anomalies = analyzer.detect_anomalies()
    anomaly_summary = analyzer.get_anomaly_summary(anomalies)
    print(f"  Total anomalies: {anomaly_summary['total_anomalies']} ({anomaly_summary['anomaly_rate_pct']}%)")
    print(f"  By method: {anomaly_summary['by_method']}")
    print(f"  By parameter: {anomaly_summary['by_parameter']}")
    print(f"  By line: {anomaly_summary['by_line']}")

    # Show first few anomalies with reasons
    anomaly_rows = anomalies[anomalies['is_anomaly'] == True]
    print("\n  Sample anomalies with reasons:")
    for _, row in anomaly_rows.head(3).iterrows():
        print(f"    [{row['timestamp']}] {row['batch_id']} {row['line_id']}")
        for reason in row['anomaly_reasons'][:2]:
            print(f"      -> {reason}")

    # 3. Defect Trends
    print("\n[TREND] DEFECT TRENDS BY BATCH")
    print("-" * 40)
    batch_trends = analyzer.aggregate_defects_by_batch()
    print(batch_trends[['batch_id', 'total_inspections', 'pass_count', 'reject_count', 'defect_rate_pct']].to_string(index=False))

    print("\n[TREND] DEFECT TRENDS BY LINE")
    print("-" * 40)
    line_trends = analyzer.aggregate_defects_by_line()
    print(line_trends[['line_id', 'total_inspections', 'pass_count', 'reject_count', 'defect_rate_pct', 'anomaly_rate_pct']].to_string(index=False))

    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)


if __name__ == '__main__':
    main()