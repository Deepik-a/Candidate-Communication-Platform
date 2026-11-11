@echo off
echo ===================================================
echo  Starting Candidate Communication Platform
echo ===================================================

echo [1/3] Starting Dummy Provider on Port 9000...
start "Dummy Provider (Port 9000)" cmd /k "cd /d %~dp0dummy_provider && python server.py"

timeout /t 2 /nobreak >nul

echo [2/3] Starting Backend API on Port 8000...
start "Backend API (Port 8000)" cmd /k "cd /d %~dp0backend && (if exist venv\Scripts\activate.bat (call venv\Scripts\activate.bat) else if exist .venv312\Scripts\activate.bat (call .venv312\Scripts\activate.bat)) && python manage.py migrate && python manage.py runserver 8000"

timeout /t 2 /nobreak >nul

echo [3/3] Starting Frontend Next.js Dev Server on Port 3000...
start "Frontend (Port 3000)" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo All 3 services have been launched in separate terminal windows!
echo - Dummy Provider UI: http://localhost:9000
echo - Backend API:       http://localhost:8000
echo - Frontend UI:       http://localhost:3000
echo ===================================================
pause

