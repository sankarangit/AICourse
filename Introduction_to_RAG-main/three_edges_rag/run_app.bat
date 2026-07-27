@echo off
setlocal
cd /d "%~dp0"

rem Load the existing course-level environment file without printing secrets.
if exist "..\..\.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("..\..\.env") do set "%%A=%%B"
)
if not defined LangSmith_API_Key if defined langsmith_api_key set "LangSmith_API_Key=%langsmith_api_key%"

set "APP_PYTHON=..\..\Ai\Scripts\python.exe"
if not exist "%APP_PYTHON%" set "APP_PYTHON=python"

"%APP_PYTHON%" -m streamlit run app.py --server.fileWatcherType none
