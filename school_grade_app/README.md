# School Marks & Grade App

A FastAPI backend and Streamlit user interface for calculating a student's total marks, percentage, subject grades, and overall result.

## Setup

```powershell
cd D:\Code\school_grade_app
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

Open two PowerShell terminals in the project folder.

Terminal 1 — FastAPI:

```powershell
python -m uvicorn backend.main:app --reload
```

Terminal 2 — Streamlit:

```powershell
python -m streamlit run streamlit_app.py
```

Open `http://localhost:8501`. API documentation is at `http://127.0.0.1:8000/docs`.

To use a backend on another host, set `GRADE_API_URL` before starting Streamlit.
