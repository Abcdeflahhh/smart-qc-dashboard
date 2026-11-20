# Smart QC Dashboard

> **Production Quality Control Inspection & Anomaly Detection System**  
> A full-stack web application for real-time monitoring, statistical anomaly detection, and executive reporting of manufacturing QC inspection data.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?logo=chart.js&logoColor=white)](https://chartjs.org)
[![Tests](https://img.shields.io/badge/Tests-35_Passing-brightgreen?logo=pytest&logoColor=white)](#testing)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 Table of Contents

- [Business Problem](#-business-problem)
- [System Architecture](#-system-architecture)
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation & Quick Start](#-installation--quick-start)
- [API Endpoints](#-api-endpoints)
- [Anomaly Detection Demo](#-anomaly-detection-demo)
- [Testing](#-testing)
- [Roadmap](#-roadmap)
- [Author](#-author)

---

## 🎯 Business Problem

In modern manufacturing, **Quality Control (QC) inspection generates massive volumes of time-series sensor data** (temperature, pressure, dimensions, defect classifications). However, most factories face critical challenges:

| Challenge | Impact |
|-----------|--------|
| **Manual inspection review** | Slow, error-prone, cannot scale to 1000+ inspections/day |
| **Reactive defect discovery** | Defects caught late → high scrap cost, rework, customer returns |
| **No statistical anomaly detection** | Process drift (tool wear, sensor calibration) goes unnoticed until OOS |
| **Siloed data** | Operators, engineers, and management view different reports |
| **Compliance & traceability** | Audit trails require structured, exportable evidence |

**Smart QC Dashboard** solves this by providing an **automated, statistical, and visual layer** over raw inspection logs — enabling **early anomaly detection**, **root-cause drill-down**, and **executive-ready reporting** in a single deployable application.

---

## 🏗 System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SMART QC DASHBOARD ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   CSV DATA   │────▶│  BACKEND     │────▶│  ANALYZER    │────▶│   REST API   │
│  (qc_produc- │     │  (FastAPI)   │     │  (Pandas +   │     │  (JSON)      │
│  tion_logs)  │     │  Port 8000   │     │   NumPy)     │     │              │
└──────────────┘     └──────┬───────┘     └──────────────┘     └──────┬───────┘
                            │                                           │
                            │          ┌──────────────┐                │
                            ├─────────▶│  FRONTEND    │◀───────────────┤
                            │          │  (Tailwind + │                │
                            │          │   Chart.js)  │                │
                            │          │  Port 8000   │                │
                            │          │  /frontend   │                │
                            │          └──────────────┘                │
                            │                                           │
                    ┌───────▼───────┐                         ┌────────▼────────┐
                    │  DATA STORE   │                         │  EXPORT ENGINE  │
                    │  (CSV Files)  │                         │  (CSV / JSON)   │
                    └───────────────┘                         └─────────────────┘

DATA FLOW DETAILS:
──────────────────
1. INGESTION
   CSV Upload (POST /api/upload-csv) ──▶ Validated ──▶ Stored ──▶ Analyzer Refreshed

2. ANALYSIS PIPELINE (qc_analyzer.QCAnalyzer)
   ├─ KPI Calculation
   │   ├─ Total Inspections, Pass/Reject Counts
   │   ├─ Pass Rate %, Defect Rate %
   │   └─ OEE Score (Availability × Performance × Quality)
   │
   ├─ Anomaly Detection (Dual Method)
   │   ├─ Z-Score (|Z| > 3.0) → Statistical outliers
   │   └─ IQR (1.5 × IQR) → Robust non-parametric bounds
   │       Applied to: temperature_c, pressure_bar, dimension_mm
   │
   └─ Trend Aggregation
       ├─ Per Batch: defect rates, parameter stats, date ranges
       ├─ Per Line: pass rates, anomaly rates, parameter distributions
       └─ Time-Series: hourly/daily resampling for charts

3. VISUALIZATION (Frontend SPA)
   ├─ KPI Cards (real-time summary)
   ├─ Line Chart: Pass/Defect Rate over time
   ├─ Doughnut Chart: Defect type distribution
   └─ Interactive Table: Filter, search, paginate, anomaly highlight

4. EXPORT & REPORTING
   ├─ GET /api/export-csv?format=csv|json
   ├─ Print-Ready Report (executive summary + anomaly details + data table)
   └─ Download trigger via browser
```

---

## ✨ Key Features

### 📊 Executive KPI Dashboard
- **Total Inspections**, **Pass Rate**, **Defect Rate**, **OEE Score** with breakdown (Availability / Performance / Quality)
- Real-time updates on data refresh

### 🔍 Dual-Method Anomaly Detection
| Method | Threshold | Use Case |
|--------|-----------|----------|
| **Z-Score** | \|Z\| > 3.0 (99.73% CI) | Gaussian-distributed parameters |
| **IQR** | 1.5 × IQR | Non-parametric, robust to skew |
- Applied to: `temperature_c`, `pressure_bar`, `dimension_mm`
- Each flagged row includes **human-readable reason** (e.g., `"temperature_c: Z-Score 4.57 (>3.0) → nilai tinggi ekstrem, mean=221.33, std=8.85"`)

### 📈 Interactive Visualizations
- **Trend Chart**: Pass/Defect rate over time (hourly, daily, 30-min)
- **Defect Distribution**: Doughnut chart with clickable legend
- **Parameter Sparkline**: Temperature, pressure, dimension averages

### 📋 Inspection Data Table
- **500+ rows** with pagination (25/page)
- **Color-coded rows**: 🔴 Anomaly (red), 🟡 Reject (amber), ⚪ Pass (normal)
- **Filters**: Status (All / PASS / REJECT / Anomaly), Free-text search
- **OOS Highlight**: Out-of-spec parameters in red

### 📤 Data Management
- **Upload CSV** → Auto-validate schema → Replace dataset → Refresh analyzer
- **Export Report** (CSV/JSON): KPIs + Anomaly details + Batch/Line trends
- **Print-Ready Report**: Executive summary + anomaly table + data appendix

### 🎨 Modern UX
- Light/Dark mode (persisted in `localStorage`)
- Responsive: mobile (stacked) → desktop (side-by-side)
- Keyboard shortcuts: `Ctrl+U` (upload), `Ctrl+P` (print), `Esc` (close modals)
- Toast notifications for async operations

---

## 🛠 Tech Stack

| Layer | Technology | Version | Purpose |
|-------|------------|---------|---------|
| **Backend API** | FastAPI | 0.115+ | High-performance async REST API |
| **Server** | Uvicorn | 0.30+ | ASGI server with hot-reload |
| **Data Analysis** | Pandas | 2.2+ | DataFrame operations, resampling |
| | NumPy | 1.26+ | Statistical computations |
| **Frontend** | Tailwind CSS | 3.4 (CDN) | Utility-first styling, dark mode |
| | Chart.js | 4.4 (CDN) | Interactive charts |
| | Vanilla JS (ES6+) | — | SPA logic, no build step |
| **Testing** | Pytest | 8.0+ | 35 unit/integration tests |
| **Data Format** | CSV | RFC 4180 | Input/Output interchange |

---

## 📁 Project Structure

```
smart-qc-dashboard/
├── backend/
│   ├── main.py              # FastAPI app: routes, CORS, static files, startup
│   ├── qc_analyzer.py       # Core analysis engine (KPI, anomalies, trends)
│   └── data_generator.py    # Synthetic data generator (500 rows, 20 batches)
├── frontend/
│   ├── index.html           # Semantic HTML5, Tailwind config, Chart.js CDN
│   ├── style.css            # Custom styles: cards, tables, modals, print
│   └── app.js               # SPA: fetch, filter, charts, upload, print
├── data/
│   └── qc_production_logs.csv   # Default dataset (500 inspections)
├── tests/
│   └── test_analyzer.py     # 35 tests: data, KPI, anomalies, trends, edges
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## 🚀 Installation & Quick Start

### Prerequisites
- **Python 3.10+**
- **Git** (for cloning)

### 1. Clone Repository
```bash
git clone https://github.com/Abcdeflahhh/smart-qc-dashboard.git
cd smart-qc-dashboard
```

### 2. Create Virtual Environment & Install Dependencies
```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run Development Server
```bash
# Single command (serves both API + Frontend)
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Access Application
| Interface | URL |
|-----------|-----|
| **Dashboard UI** | <http://localhost:8000/frontend/> |
| **API Documentation (Swagger)** | <http://localhost:8000/docs> |
| **API Documentation (ReDoc)** | <http://localhost:8000/redoc> |
| **Health Check** | <http://localhost:8000/health> |

---

## 📡 API Endpoints

| Method | Endpoint | Description | Query Params |
|--------|----------|-------------|--------------|
| `GET` | `/api/summary` | KPI summary (total, pass rate, defect rate, OEE) | — |
| `GET` | `/api/anomalies` | Anomaly list with Z-Score & IQR details | `z_threshold`, `iqr_multiplier`, `only_anomalies`, `limit` |
| `GET` | `/api/trends` | Time-series trend data for charts | `freq` (h\|D\|30min), `line_id`, `batch_id` |
| `POST` | `/api/upload-csv` | Upload new inspection CSV (multipart/form-data) | `file` (CSV) |
| `GET` | `/api/export-csv` | Download analysis report | `format` (csv\|json), `include_anomalies`, `include_trends` |

### Example: Fetch Anomalies Only
```bash
curl "http://localhost:8000/api/anomalies?only_anomalies=true&limit=10"
```

### Example: Upload New CSV
```bash
curl -X POST "http://localhost:8000/api/upload-csv" \
  -F "file=@data/qc_production_logs.csv"
```

---

## 🔬 Anomaly Detection Demo

### Sample Output (Anomaly Flagged Row)
```json
{
  "index": 22,
  "timestamp": "2024-01-01 06:24:58",
  "batch_id": "BATCH-0001",
  "line_id": "LINE-A",
  "is_anomaly": true,
  "anomaly_methods": ["Z-Score", "IQR"],
  "anomaly_params": ["temperature_c"],
  "anomaly_reasons": [
    "temperature_c: Z-Score 4.57 (>3.0) -> nilai tinggi ekstrem, mean=221.33, std=8.85",
    "temperature_c: 261.74 di atas upper bound (IQR bounds: 206.93 - 234.10, Q1=217.12, Q3=223.91, IQR=6.79)"
  ],
  "z_scores": {
    "temperature_c": 4.565,
    "pressure_bar": 0.042,
    "dimension_mm": 0.059
  },
  "iqr_flags": {
    "temperature_c": {
      "Q1": 217.122, "Q3": 223.915, "IQR": 6.792,
      "lower_bound": 206.934, "upper_bound": 234.104, "is_outlier": true
    }
  }
}
```

### Anomaly Summary (500-row dataset)
| Metric | Value |
|--------|-------|
| **Total Anomalies Detected** | 32 (6.4%) |
| **By Method** | IQR: 32, Z-Score: 23 |
| **By Parameter** | Temperature: 14, Pressure: 14, Dimension: 12 |
| **By Line** | LINE-A: 14, LINE-C: 7, LINE-B: 7, LINE-D: 4 |

> **Note**: The synthetic dataset injects ~5% extreme anomalies (temperature spikes >260°C, pressure drops <55 bar, dimensional shifts >50.5mm) — all correctly flagged by both methods.

---

## 🧪 Testing

```bash
# Run full test suite (35 tests)
python -m pytest tests/test_analyzer.py -v

# Run with coverage
python -m pytest tests/test_analyzer.py --cov=backend --cov-report=term-missing
```

### Test Coverage
| Module | Tests | Coverage |
|--------|-------|----------|
| Data Loading | 8 | 100% |
| KPI Calculation | 4 | 100% |
| Anomaly Detection (Z-Score + IQR) | 8 | 100% |
| Defect Aggregation (Batch + Line) | 8 | 100% |
| Time-Series Trends | 2 | 100% |
| Edge Cases (empty, missing file) | 2 | 100% |
| Integration Pipeline | 1 | 100% |
| **Total** | **35** | **✅ All Passing** |

---

## 🗺 Roadmap

- [ ] **WebSocket** real-time updates for live production monitoring
- [ ] **Authentication** (JWT/OAuth2) for multi-user roles (Operator, Engineer, Manager)
- [ ] **Database** migration (PostgreSQL + SQLAlchemy) for historical queries
- [ ] **ML Model** integration (Isolation Forest, LSTM) for predictive anomaly detection
- [ ] **Docker** multi-stage build + docker-compose for one-command deployment
- [ ] **Grafana** dashboard export for enterprise observability stacks
- [ ] **Multi-language** i18n (EN/ID/DE/JP) for global factories

---

## 👤 Author

**Aflah Athallah Tamam Kapukong**  
🔗 **GitHub**: [@Abcdeflahhh](https://github.com/Abcdeflahhh)  
📧 **Contact**: Open to opportunities in Data Engineering, ML Ops, and Manufacturing Analytics

> *Built with ❤️ for the manufacturing quality community. Star ⭐ the repo if you find it useful!*

---

## 📄 License

MIT License — Free for personal and commercial use. See [LICENSE](LICENSE) for details.