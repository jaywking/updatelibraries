@echo off
setlocal

REM Set the name of the virtual environment directory
set VENV_DIR=.venv

REM Check if the virtual environment directory exists
if not exist "%VENV_DIR%\Scripts\activate" (
    echo Creating virtual environment in %VENV_DIR%...
    REM Use the system's python to create the venv. Make sure python is in your PATH.
    python -m venv %VENV_DIR%
    if %errorlevel% neq 0 (
        echo Failed to create virtual environment. Please ensure Python is installed and in your PATH.
        goto :error
    )
)

REM Activate the virtual environment
call "%VENV_DIR%\Scripts\activate"

REM Install dependencies from requirements.txt
echo Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies.
    goto :error
)

REM Run the main Python script
echo Running the library update script...
python UpdateLibraries.py %*

goto :end

:error
echo.
echo An error occurred.

:end
echo.
pause
endlocal
