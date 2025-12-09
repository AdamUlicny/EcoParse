@echo off
echo ==========================================
echo      EcoParse Docker Launcher for Windows
echo ==========================================
echo.

:: Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running or not installed.
    echo Please start Docker Desktop and try again.
    echo.
    pause
    exit /b 1
)

echo Building EcoParse Docker image...
echo This may take a few minutes the first time.
docker build -t ecoparse-app .
if %errorlevel% neq 0 (
    echo.
    echo Error: Failed to build Docker image.
    pause
    exit /b 1
)

echo.
echo Starting EcoParse...
echo.
echo The application will be available at: http://localhost:8501
echo.
echo Press Ctrl+C to stop the server.
echo.

docker run -p 8501:8501 -p 4040:4040 ecoparse-app

pause
