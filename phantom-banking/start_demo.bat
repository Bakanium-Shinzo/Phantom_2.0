@echo off
echo Starting FNB Phantom Banking Demo...
echo.

REM Start API Server
echo Starting API Server on port 5000...
start "Phantom Banking API" C:\Users\Bakang\anaconda3\envs\Phantom\python.exe api_server.py

REM Wait for API to start
timeout /t 3 > nul

REM Start Streamlit Frontend
echo Starting Streamlit Frontend on port 8501...
start "Phantom Banking Frontend" C:\Users\Bakang\anaconda3\envs\Phantom\python.exe -m streamlit run streamlit_app.py

echo.
echo Demo started successfully!
echo Frontend: http://localhost:8501
echo API: http://localhost:5000
echo.
echo Press any key to continue...
pause > nul
