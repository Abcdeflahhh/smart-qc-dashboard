#!/usr/bin/env python3
"""
Smart QC Dashboard - FastAPI Backend
Provides REST API for QC analysis with endpoints:
- GET /api/summary - KPI summary
- GET /api/anomalies - Anomaly detection results
- GET /api/trends - Trend data for charts
- POST /api/upload-csv - Upload new CSV for analysis
- GET /api/export-csv - Export analysis report
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
import json
import io

# Import local analyzer
import sys
sys.path.insert(0, str(Path(__file__).parent))
from qc_analyzer import QCAnalyzer

# ============================================================
# FastAPI App Configuration
# ============================================================
app = FastAPI(
    title="Smart QC Dashboard API",
    description="Quality Control Production Inspection Analysis API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# Global State
# ============================================================
# Default analyzer instance
DEFAULT_DATA_PATH = Path(__file__).parent.parent / "data" / "qc_production_logs.csv"
analyzer: QCAnalyzer = None
current_data_path: Path = DEFAULT_DATA_PATH


def get_analyzer() -> QCAnalyzer:
    """Get or create analyzer instance."""
    global analyzer, current_data_path
    if analyzer is None or not current_data_path.exists():
        if current_data_path.exists():
            analyzer = QCAnalyzer(str(current_data_path))
        else:
            # Create empty analyzer if no data
            analyzer = QCAnalyzer.__new__(QCAnalyzer)
            analyzer.df = pd.DataFrame()
            analyzer.data_path = current_data_path
    return analyzer


def refresh_analyzer(data_path: Path = None):
    """Refresh analyzer with new data path."""
    global analyzer, current_data_path
    if data_path:
        current_data_path = data_path
    analyzer = QCAnalyzer(str(current_data_path))
    return analyzer


# ============================================================
# Pydantic Models
# ============================================================
class KPIResponse(BaseModel):
    total_inspections: int
    pass_count: int
    reject_count: int
    pass_rate_pct: float
    defect_rate_pct: float
    oee_score: float
    availability_pct: float
    performance_pct: float
    quality_pct: float
    unique_batches: int
    unique_lines: int
    date_range: Dict[str, Optional[str]]


class AnomalyItem(BaseModel):
    index: int
    timestamp: str
    batch_id: str
    line_id: str
    is_anomaly: bool
    anomaly_methods: List[str]
    anomaly_params: List[str]
    anomaly_reasons: List[str]
    z_scores: Dict[str, float]
    iqr_flags: Dict[str, Dict[str, Any]]


class AnomalyResponse(BaseModel):
    anomalies: List[AnomalyItem]
    summary: Dict[str, Any]


class TrendPoint(BaseModel):
    timestamp: str
    total_inspections: int
    pass_count: int
    reject_count: int
    pass_rate_pct: float
    defect_rate_pct: float
    temperature_c: Optional[float] = None
    pressure_bar: Optional[float] = None
    dimension_mm: Optional[float] = None
    defect_scratch: Optional[int] = None
    defect_dent: Optional[int] = None
    defect_crack: Optional[int] = None
    defect_dimensional: Optional[int] = None
    defect_contamination: Optional[int] = None
    defect_burr: Optional[int] = None
    defect_warpage: Optional[int] = None
    defect_discoloration: Optional[int] = None
    defect_incomplete: Optional[int] = None


class TrendResponse(BaseModel):
    data: List[TrendPoint]
    freq: str


class UploadResponse(BaseModel):
    success: bool
    message: str
    rows: int
    columns: List[str]
    preview: List[Dict[str, Any]]


class ExportResponse(BaseModel):
    success: bool
    message: str
    download_url: Optional[str] = None


# ============================================================
# Startup Event
# ============================================================
@app.on_event("startup")
async def startup_event():
    """Initialize analyzer on startup."""
    global analyzer
    try:
        if DEFAULT_DATA_PATH.exists():
            analyzer = QCAnalyzer(str(DEFAULT_DATA_PATH))
            print(f"[OK] Analyzer initialized with {len(analyzer.df)} rows from {DEFAULT_DATA_PATH}")
        else:
            print(f"[WARN] Default data file not found: {DEFAULT_DATA_PATH}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize analyzer: {e}")


# ============================================================
# API Endpoints
# ============================================================
@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": "Smart QC Dashboard API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "summary": "GET /api/summary",
            "anomalies": "GET /api/anomalies",
            "trends": "GET /api/trends",
            "upload": "POST /api/upload-csv",
            "export": "GET /api/export-csv"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# --- 1. GET /api/summary ---
@app.get("/api/summary", response_model=KPIResponse)
async def get_summary():
    """
    Get main KPI summary for dashboard.
    Returns: total inspections, pass rate, defect rate, OEE score, etc.
    """
    try:
        an = get_analyzer()
        if an.df is None or len(an.df) == 0:
            raise HTTPException(status_code=404, detail="No data available")

        kpis = an.calculate_kpis()
        return KPIResponse(**kpis)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating KPIs: {str(e)}")


# --- 2. GET /api/anomalies ---
@app.get("/api/anomalies", response_model=AnomalyResponse)
async def get_anomalies(
    z_threshold: float = Query(3.0, ge=1.0, le=10.0, description="Z-score threshold"),
    iqr_multiplier: float = Query(1.5, ge=0.5, le=5.0, description="IQR multiplier"),
    only_anomalies: bool = Query(False, description="Return only anomalous rows"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return")
):
    """
    Get anomaly detection results using Z-Score and IQR methods.
    """
    try:
        an = get_analyzer()
        if an.df is None or len(an.df) == 0:
            raise HTTPException(status_code=404, detail="No data available")

        anomalies_df = an.detect_anomalies(
            z_threshold=z_threshold,
            iqr_multiplier=iqr_multiplier
        )

        if only_anomalies:
            anomalies_df = anomalies_df[anomalies_df['is_anomaly'] == True]

        # Limit results
        anomalies_df = anomalies_df.head(limit)

        # Convert to response format
        anomalies_list = []
        for _, row in anomalies_df.iterrows():
            # Convert numpy types to Python native
            z_scores = {k: float(v) for k, v in row['z_scores'].items()}
            iqr_flags = {}
            for param, flags in row['iqr_flags'].items():
                iqr_flags[param] = {k: (float(v) if isinstance(v, (np.floating, np.integer)) else
                                        (bool(v) if isinstance(v, np.bool_) else v))
                                    for k, v in flags.items()}

            anomalies_list.append(AnomalyItem(
                index=int(row['index']),
                timestamp=str(row['timestamp']),
                batch_id=str(row['batch_id']),
                line_id=str(row['line_id']),
                is_anomaly=bool(row['is_anomaly']),
                anomaly_methods=list(row['anomaly_methods']),
                anomaly_params=list(row['anomaly_params']),
                anomaly_reasons=list(row['anomaly_reasons']),
                z_scores=z_scores,
                iqr_flags=iqr_flags
            ))

        summary = an.get_anomaly_summary(anomalies_df)

        return AnomalyResponse(
            anomalies=anomalies_list,
            summary=summary
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error detecting anomalies: {str(e)}")


# --- 3. GET /api/trends ---
@app.get("/api/trends", response_model=TrendResponse)
async def get_trends(
    freq: str = Query("h", description="Resample frequency: h, D, 30min"),
    line_id: Optional[str] = Query(None, description="Filter by production line"),
    batch_id: Optional[str] = Query(None, description="Filter by batch")
):
    """
    Get time-series trend data for charts.
    Supports filtering by line and batch.
    """
    try:
        an = get_analyzer()
        if an.df is None or len(an.df) == 0:
            raise HTTPException(status_code=404, detail="No data available")

        df = an.df.copy()

        # Apply filters
        if line_id:
            df = df[df['line_id'] == line_id]
        if batch_id:
            df = df[df['batch_id'] == batch_id]

        if len(df) == 0:
            return TrendResponse(data=[], freq=freq)

        # Create temporary analyzer with filtered data
        temp_analyzer = QCAnalyzer.__new__(QCAnalyzer)
        temp_analyzer.df = df.sort_values('timestamp').reset_index(drop=True)
        temp_analyzer.data_path = an.data_path

        # Get trends
        trends_df = temp_analyzer.get_defect_trend_timeseries(freq=freq)

        if len(trends_df) == 0:
            return TrendResponse(data=[], freq=freq)

        # Convert to response format
        trend_points = []
        for _, row in trends_df.iterrows():
            point = TrendPoint(
                timestamp=row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                total_inspections=int(row['total_inspections']),
                pass_count=int(row['pass_count']),
                reject_count=int(row['reject_count']),
                pass_rate_pct=float(row['pass_rate_pct']),
                defect_rate_pct=float(row['defect_rate_pct']),
            )

            # Add optional fields
            for field in ['temperature_c', 'pressure_bar', 'dimension_mm']:
                if field in row and pd.notna(row[field]):
                    setattr(point, field, float(row[field]))

            # Add defect type columns
            for dt in ['scratch', 'dent', 'crack', 'dimensional', 'contamination',
                       'burr', 'warpage', 'discoloration', 'incomplete']:
                col = f'defect_{dt}'
                if col in row:
                    setattr(point, col, int(row[col]) if pd.notna(row[col]) else 0)

            trend_points.append(point)

        return TrendResponse(data=trend_points, freq=freq)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting trends: {str(e)}")


# --- 4. POST /api/upload-csv ---
@app.post("/api/upload-csv", response_model=UploadResponse)
async def upload_csv(file: UploadFile = File(...)):
    """
    Upload new CSV file for analysis.
    Replaces current dataset and refreshes analyzer.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="File must be a CSV")

        # Read file content
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")

        # Parse CSV
        try:
            df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid CSV format: {str(e)}")

        # Validate required columns
        required_cols = ['timestamp', 'batch_id', 'line_id', 'temperature_c', 'pressure_bar', 'dimension_mm', 'defect_type', 'status']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            raise HTTPException(status_code=400, detail=f"Missing required columns: {missing_cols}")

        # Save to data directory
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"qc_production_logs_{timestamp}.csv"
        new_path = data_dir / new_filename

        # Also overwrite default
        default_path = data_dir / "qc_production_logs.csv"
        df.to_csv(default_path, index=False)
        df.to_csv(new_path, index=False)

        # Refresh analyzer
        refresh_analyzer(default_path)

        # Preview first 5 rows
        preview = df.head(5).to_dict('records')

        return UploadResponse(
            success=True,
            message=f"CSV uploaded successfully. {len(df)} rows loaded.",
            rows=len(df),
            columns=list(df.columns),
            preview=preview
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading CSV: {str(e)}")


# --- 5. GET /api/export-csv ---
@app.get("/api/export-csv")
async def export_csv(
    include_anomalies: bool = Query(True, description="Include anomaly analysis columns"),
    include_trends: bool = Query(True, description="Include trend summary"),
    format: str = Query("csv", description="Export format: csv or json")
):
    """
    Export analysis report as CSV or JSON.
    Includes KPIs, anomalies, and trends.
    """
    try:
        an = get_analyzer()
        if an.df is None or len(an.df) == 0:
            raise HTTPException(status_code=404, detail="No data available")

        # Collect all analysis data
        kpis = an.calculate_kpis()
        anomalies_df = an.detect_anomalies()
        anomaly_summary = an.get_anomaly_summary(anomalies_df)

        # Create export data
        export_data = {
            "generated_at": datetime.now().isoformat(),
            "data_source": str(current_data_path),
            "kpis": kpis,
            "anomaly_summary": anomaly_summary,
        }

        if include_anomalies:
            # Include full anomaly details
            anomaly_details = []
            for _, row in anomalies_df[anomalies_df['is_anomaly'] == True].iterrows():
                anomaly_details.append({
                    "index": int(row['index']),
                    "timestamp": str(row['timestamp']),
                    "batch_id": str(row['batch_id']),
                    "line_id": str(row['line_id']),
                    "methods": list(row['anomaly_methods']),
                    "parameters": list(row['anomaly_params']),
                    "reasons": list(row['anomaly_reasons']),
                    "z_scores": {k: float(v) for k, v in row['z_scores'].items()},
                    "iqr_flags": {k: {kk: (float(vv) if isinstance(vv, (np.floating, np.integer)) else vv)
                                      for kk, vv in v.items()}
                                  for k, v in row['iqr_flags'].items()}
                })
            export_data["anomalies"] = anomaly_details

        if include_trends:
            # Include batch and line trends
            batch_trends = an.aggregate_defects_by_batch()
            line_trends = an.aggregate_defects_by_line()

            export_data["batch_trends"] = batch_trends.to_dict('records')
            export_data["line_trends"] = line_trends.to_dict('records')

        # Create export file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = Path(__file__).parent.parent / "data"
        data_dir.mkdir(exist_ok=True)

        if format.lower() == "json":
            filename = f"qc_analysis_report_{timestamp}.json"
            filepath = data_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
            media_type = "application/json"
        else:
            filename = f"qc_analysis_report_{timestamp}.csv"
            filepath = data_dir / filename

            # Flatten for CSV - create summary sheet
            summary_rows = [
                ["Metric", "Value"],
                ["Generated At", export_data["generated_at"]],
                ["Data Source", export_data["data_source"]],
                ["", ""],
                ["KPI", "Value"],
                ["Total Inspections", kpis["total_inspections"]],
                ["Pass Count", kpis["pass_count"]],
                ["Reject Count", kpis["reject_count"]],
                ["Pass Rate %", kpis["pass_rate_pct"]],
                ["Defect Rate %", kpis["defect_rate_pct"]],
                ["OEE Score", kpis["oee_score"]],
                ["Availability %", kpis["availability_pct"]],
                ["Performance %", kpis["performance_pct"]],
                ["Quality %", kpis["quality_pct"]],
                ["Unique Batches", kpis["unique_batches"]],
                ["Unique Lines", kpis["unique_lines"]],
                ["Date Range Start", kpis["date_range"]["start"]],
                ["Date Range End", kpis["date_range"]["end"]],
                ["", ""],
                ["Anomaly Summary", ""],
                ["Total Anomalies", anomaly_summary["total_anomalies"]],
                ["Anomaly Rate %", anomaly_summary["anomaly_rate_pct"]],
                ["By Method", str(anomaly_summary["by_method"])],
                ["By Parameter", str(anomaly_summary["by_parameter"])],
                ["By Line", str(anomaly_summary["by_line"])],
            ]

            # Write CSV
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = pd.DataFrame(summary_rows)
                writer.to_csv(f, index=False, header=False)

            media_type = "text/csv"

        return FileResponse(
            path=str(filepath),
            filename=filename,
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting report: {str(e)}")


# ============================================================
# Static Files (Frontend)
# ============================================================
frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path), html=True), name="frontend")
    # Also serve at root for convenience
    @app.get("/app")
    async def serve_frontend():
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return {"message": "Frontend not built yet. Place index.html in frontend/ folder."}


# ============================================================
# Run Server
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )