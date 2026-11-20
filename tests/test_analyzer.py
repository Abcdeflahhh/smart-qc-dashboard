#!/usr/bin/env python3
"""
Smart QC Dashboard - Test Suite for QC Analyzer
Tests all analyzer functions using pytest.
"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

from qc_analyzer import QCAnalyzer


# ============================================================
# FIXTURES
# ============================================================
@pytest.fixture(scope="session")
def analyzer():
    """Create QCAnalyzer instance for testing."""
    return QCAnalyzer()


@pytest.fixture(scope="session")
def sample_data(analyzer):
    """Return the loaded DataFrame."""
    return analyzer.df


# ============================================================
# TESTS: DATA LOADING
# ============================================================
class TestDataLoading:
    """Tests for data loading and validation."""

    def test_data_file_exists(self, analyzer):
        """Verify data file was loaded successfully."""
        assert analyzer.df is not None
        assert len(analyzer.df) > 0

    def test_data_shape(self, analyzer):
        """Verify data has expected shape (500 rows, 8 columns)."""
        assert len(analyzer.df) == 500
        assert len(analyzer.df.columns) == 8

    def test_required_columns(self, analyzer):
        """Verify all required columns exist."""
        expected_cols = [
            'timestamp', 'batch_id', 'line_id',
            'temperature_c', 'pressure_bar', 'dimension_mm',
            'defect_type', 'status'
        ]
        for col in expected_cols:
            assert col in analyzer.df.columns, f"Missing column: {col}"

    def test_timestamp_parsed(self, analyzer):
        """Verify timestamp column is parsed as datetime."""
        assert pd.api.types.is_datetime64_any_dtype(analyzer.df['timestamp'])

    def test_numeric_columns(self, analyzer):
        """Verify numeric columns are proper types."""
        for col in ['temperature_c', 'pressure_bar', 'dimension_mm']:
            assert pd.api.types.is_numeric_dtype(analyzer.df[col])

    def test_status_values(self, analyzer):
        """Verify status only contains PASS/REJECT."""
        unique_status = set(analyzer.df['status'].unique())
        assert unique_status.issubset({'PASS', 'REJECT'})

    def test_line_ids(self, analyzer):
        """Verify line IDs are valid."""
        unique_lines = set(analyzer.df['line_id'].unique())
        expected = {'LINE-A', 'LINE-B', 'LINE-C', 'LINE-D'}
        assert unique_lines.issubset(expected)

    def test_batch_count(self, analyzer):
        """Verify we have multiple batches."""
        assert analyzer.df['batch_id'].nunique() >= 10


# ============================================================
# TESTS: KPI CALCULATION
# ============================================================
class TestKPICalculation:
    """Tests for KPI calculation functions."""

    def test_calculate_kpis_returns_dict(self, analyzer):
        """Verify calculate_kpis returns a dictionary."""
        kpis = analyzer.calculate_kpis()
        assert isinstance(kpis, dict)

    def test_kpis_has_required_keys(self, analyzer):
        """Verify all required KPI keys are present."""
        kpis = analyzer.calculate_kpis()
        required_keys = [
            'total_inspections', 'pass_count', 'reject_count',
            'pass_rate_pct', 'defect_rate_pct', 'oee_score',
            'availability_pct', 'performance_pct', 'quality_pct',
            'unique_batches', 'unique_lines', 'date_range'
        ]
        for key in required_keys:
            assert key in kpis, f"Missing KPI key: {key}"

    def test_kpis_values_reasonable(self, analyzer):
        """Verify KPI values are within reasonable ranges."""
        kpis = analyzer.calculate_kpis()

        assert kpis['total_inspections'] == 500
        assert kpis['pass_count'] + kpis['reject_count'] == 500
        assert 0 <= kpis['pass_rate_pct'] <= 100
        assert 0 <= kpis['defect_rate_pct'] <= 100
        assert abs(kpis['pass_rate_pct'] + kpis['defect_rate_pct'] - 100) < 0.01
        assert 0 <= kpis['oee_score'] <= 100
        assert 0 <= kpis['availability_pct'] <= 100
        assert 0 <= kpis['performance_pct'] <= 100
        assert 0 <= kpis['quality_pct'] <= 100
        assert kpis['quality_pct'] == kpis['pass_rate_pct']
        assert kpis['unique_batches'] > 0
        assert kpis['unique_lines'] == 4

    def test_kpis_date_range(self, analyzer):
        """Verify date range is present and valid."""
        kpis = analyzer.calculate_kpis()
        dr = kpis['date_range']
        assert 'start' in dr
        assert 'end' in dr
        assert dr['start'] is not None
        assert dr['end'] is not None
        # Start should be before end
        assert pd.Timestamp(dr['start']) <= pd.Timestamp(dr['end'])


# ============================================================
# TESTS: ANOMALY DETECTION
# ============================================================
class TestAnomalyDetection:
    """Tests for anomaly detection (Z-Score & IQR)."""

    def test_detect_anomalies_returns_dataframe(self, analyzer):
        """Verify detect_anomalies returns DataFrame."""
        anomalies = analyzer.detect_anomalies()
        assert isinstance(anomalies, pd.DataFrame)

    def test_anomalies_same_length_as_data(self, analyzer):
        """Verify anomalies DataFrame has same row count as source data."""
        anomalies = analyzer.detect_anomalies()
        assert len(anomalies) == len(analyzer.df)

    def test_anomaly_columns_present(self, analyzer):
        """Verify required anomaly columns exist."""
        anomalies = analyzer.detect_anomalies()
        required_cols = [
            'index', 'timestamp', 'batch_id', 'line_id',
            'is_anomaly', 'anomaly_methods', 'anomaly_params',
            'anomaly_reasons', 'z_scores', 'iqr_flags'
        ]
        for col in required_cols:
            assert col in anomalies.columns, f"Missing anomaly column: {col}"

    def test_anomaly_detection_finds_some(self, analyzer):
        """Verify anomalies are detected (we injected ~5% anomalies)."""
        anomalies = analyzer.detect_anomalies()
        anomaly_count = anomalies['is_anomaly'].sum()
        # Should detect at least some anomalies (we injected extreme values)
        assert anomaly_count > 0
        assert anomaly_count < len(analyzer.df)  # Not everything is anomaly

    def test_z_scores_calculated(self, analyzer):
        """Verify Z-scores are calculated for each parameter."""
        anomalies = analyzer.detect_anomalies()
        # Check first row has z_scores dict with all 3 params
        z_scores = anomalies.iloc[0]['z_scores']
        assert isinstance(z_scores, dict)
        for param in ['temperature_c', 'pressure_bar', 'dimension_mm']:
            assert param in z_scores
            assert isinstance(z_scores[param], (int, float))

    def test_iqr_flags_calculated(self, analyzer):
        """Verify IQR flags are calculated."""
        anomalies = analyzer.detect_anomalies()
        iqr_flags = anomalies.iloc[0]['iqr_flags']
        assert isinstance(iqr_flags, dict)
        for param in ['temperature_c', 'pressure_bar', 'dimension_mm']:
            assert param in iqr_flags
            flag = iqr_flags[param]
            assert 'Q1' in flag
            assert 'Q3' in flag
            assert 'IQR' in flag
            assert 'lower_bound' in flag
            assert 'upper_bound' in flag
            assert 'is_outlier' in flag
            # Accept both Python bool and numpy bool
            assert isinstance(flag['is_outlier'], (bool, np.bool_))

    def test_anomaly_reasons_populated(self, analyzer):
        """Verify anomaly reasons are provided for flagged rows."""
        anomalies = analyzer.detect_anomalies()
        anomaly_rows = anomalies[anomalies['is_anomaly'] == True]
        assert len(anomaly_rows) > 0
        for _, row in anomaly_rows.iterrows():
            assert len(row['anomaly_reasons']) > 0
            assert len(row['anomaly_methods']) > 0
            assert len(row['anomaly_params']) > 0

    def test_get_anomaly_summary(self, analyzer):
        """Verify anomaly summary returns expected structure."""
        anomalies = analyzer.detect_anomalies()
        summary = analyzer.get_anomaly_summary(anomalies)

        required_keys = [
            'total_anomalies', 'anomaly_rate_pct',
            'by_method', 'by_parameter', 'by_line', 'by_batch', 'anomaly_indices'
        ]
        for key in required_keys:
            assert key in summary, f"Missing summary key: {key}"

        assert summary['total_anomalies'] == anomalies['is_anomaly'].sum()
        assert 0 <= summary['anomaly_rate_pct'] <= 100
        assert isinstance(summary['by_method'], dict)
        assert isinstance(summary['by_parameter'], dict)
        assert isinstance(summary['by_line'], dict)
        assert isinstance(summary['by_batch'], dict)
        assert isinstance(summary['anomaly_indices'], list)

    def test_custom_thresholds(self, analyzer):
        """Verify custom Z-threshold and IQR multiplier work."""
        # Very high threshold - should find fewer anomalies
        anomalies_high = analyzer.detect_anomalies(z_threshold=5.0, iqr_multiplier=3.0)
        # Default threshold
        anomalies_default = analyzer.detect_anomalies(z_threshold=3.0, iqr_multiplier=1.5)
        # High threshold should find <= default
        assert anomalies_high['is_anomaly'].sum() <= anomalies_default['is_anomaly'].sum()


# ============================================================
# TESTS: DEFECT AGGREGATION
# ============================================================
class TestDefectAggregation:
    """Tests for defect trend aggregation."""

    def test_aggregate_by_batch_returns_dataframe(self, analyzer):
        """Verify batch aggregation returns DataFrame."""
        result = analyzer.aggregate_defects_by_batch()
        assert isinstance(result, pd.DataFrame)

    def test_batch_aggregation_has_expected_columns(self, analyzer):
        """Verify batch aggregation has expected columns."""
        result = analyzer.aggregate_defects_by_batch()
        expected_base = ['batch_id', 'total_inspections', 'pass_count', 'reject_count',
                         'pass_rate_pct', 'defect_rate_pct', 'batch_start', 'batch_end']
        for col in expected_base:
            assert col in result.columns, f"Missing batch column: {col}"

    def test_batch_aggregation_row_count(self, analyzer):
        """Verify one row per unique batch."""
        result = analyzer.aggregate_defects_by_batch()
        assert len(result) == analyzer.df['batch_id'].nunique()

    def test_batch_rates_calculated(self, analyzer):
        """Verify pass/defect rates are calculated correctly."""
        result = analyzer.aggregate_defects_by_batch()
        for _, row in result.iterrows():
            total = row['total_inspections']
            if total > 0:
                expected_pass = round(row['pass_count'] / total * 100, 2)
                expected_defect = round(row['reject_count'] / total * 100, 2)
                assert abs(row['pass_rate_pct'] - expected_pass) < 0.01
                assert abs(row['defect_rate_pct'] - expected_defect) < 0.01

    def test_aggregate_by_line_returns_dataframe(self, analyzer):
        """Verify line aggregation returns DataFrame."""
        result = analyzer.aggregate_defects_by_line()
        assert isinstance(result, pd.DataFrame)

    def test_line_aggregation_has_expected_columns(self, analyzer):
        """Verify line aggregation has expected columns."""
        result = analyzer.aggregate_defects_by_line()
        expected_base = ['line_id', 'total_inspections', 'pass_count', 'reject_count',
                         'pass_rate_pct', 'defect_rate_pct', 'unique_batches',
                         'anomaly_count', 'anomaly_rate_pct']
        for col in expected_base:
            assert col in result.columns, f"Missing line column: {col}"

    def test_line_aggregation_row_count(self, analyzer):
        """Verify one row per unique line (4 lines)."""
        result = analyzer.aggregate_defects_by_line()
        assert len(result) == 4

    def test_line_parameter_stats(self, analyzer):
        """Verify process parameter stats per line."""
        result = analyzer.aggregate_defects_by_line()
        param_cols = [c for c in result.columns if any(p in c for p in ['temperature', 'pressure', 'dimension'])
                      and any(s in c for s in ['mean', 'std', 'min', 'max'])]
        assert len(param_cols) > 0  # Should have parameter stats

    def test_defect_types_breakdown(self, analyzer):
        """Verify defect type breakdown exists in both aggregations."""
        batch_result = analyzer.aggregate_defects_by_batch()
        line_result = analyzer.aggregate_defects_by_line()

        defect_cols_batch = [c for c in batch_result.columns if c.startswith('defect_')]
        defect_cols_line = [c for c in line_result.columns if c.startswith('defect_')]

        # Should have at least some defect type columns
        assert len(defect_cols_batch) > 0
        assert len(defect_cols_line) > 0


# ============================================================
# TESTS: TIME SERIES
# ============================================================
class TestTimeSeries:
    """Tests for time-series defect trends."""

    def test_get_defect_trend_timeseries(self, analyzer):
        """Verify time-series aggregation works."""
        result = analyzer.get_defect_trend_timeseries(freq='h')
        assert isinstance(result, pd.DataFrame)
        assert 'timestamp' in result.columns
        assert 'total_inspections' in result.columns
        assert 'pass_rate_pct' in result.columns
        assert 'defect_rate_pct' in result.columns

    def test_different_frequencies(self, analyzer):
        """Verify different resampling frequencies work."""
        for freq in ['h', 'D', '30min']:
            result = analyzer.get_defect_trend_timeseries(freq=freq)
            assert len(result) > 0
            assert 'timestamp' in result.columns


# ============================================================
# TESTS: EDGE CASES
# ============================================================
class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_analyzer(self, tmp_path):
        """Test analyzer with empty CSV."""
        empty_csv = tmp_path / "empty.csv"
        empty_csv.write_text("timestamp,batch_id,line_id,temperature_c,pressure_bar,dimension_mm,defect_type,status\n")

        analyzer = QCAnalyzer(str(empty_csv))
        kpis = analyzer.calculate_kpis()
        assert kpis['total_inspections'] == 0
        assert kpis['pass_rate_pct'] == 0.0

        anomalies = analyzer.detect_anomalies()
        assert len(anomalies) == 0

        batch_agg = analyzer.aggregate_defects_by_batch()
        assert len(batch_agg) == 0

    def test_missing_file_raises_error(self):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            QCAnalyzer("nonexistent_file.csv")


# ============================================================
# INTEGRATION TEST
# ============================================================
class TestIntegration:
    """Integration test - full analysis pipeline."""

    def test_full_analysis_pipeline(self, analyzer):
        """Run complete analysis pipeline without errors."""
        # 1. KPIs
        kpis = analyzer.calculate_kpis()
        assert kpis['total_inspections'] == 500

        # 2. Anomalies
        anomalies = analyzer.detect_anomalies()
        summary = analyzer.get_anomaly_summary(anomalies)
        assert summary['total_anomalies'] > 0

        # 3. Batch trends
        batch_trends = analyzer.aggregate_defects_by_batch()
        assert len(batch_trends) == 20  # 20 batches

        # 4. Line trends
        line_trends = analyzer.aggregate_defects_by_line()
        assert len(line_trends) == 4  # 4 lines

        # 5. Time series
        ts = analyzer.get_defect_trend_timeseries(freq='H')
        assert len(ts) > 0

        # All should complete without exception
        assert True


# ============================================================
# RUN TESTS
# ============================================================
if __name__ == '__main__':
    # Allow running directly with python -m pytest or python test_analyzer.py
    pytest.main([__file__, '-v', '--tb=short'])