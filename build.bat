@echo off
chcp 65001 > nul
title AppKS - Compilador

echo.
echo ========================================================
echo   AppKS - Generar launcher .exe
echo ========================================================
echo.

if not exist "start_app.py" (
    echo ERROR: Ejecuta este script desde la raiz del proyecto AppKS
    pause
    exit /b 1
)

:: Cerrar AppKS.exe si esta corriendo
taskkill /f /im AppKS.exe 2>nul
timeout /t 2 /nobreak >nul

:: Activar entorno virtual
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Instalar / actualizar PyInstaller
echo [1/3] Verificando PyInstaller...
pip install --quiet --upgrade pyinstaller
if errorlevel 1 (
    echo ERROR: No se pudo instalar PyInstaller
    pause
    exit /b 1
)

:: Limpiar compilaciones anteriores
echo [2/3] Limpiando compilacion anterior...
if exist "dist\AppKS.exe" del /f /q "dist\AppKS.exe"
if exist "build" rmdir /s /q "build"

:: Compilar
echo [3/3] Compilando AppKS.exe...
pyinstaller --onefile --name AppKS --noconsole start_app.py

if errorlevel 1 (
    echo.
    echo ERROR: La compilacion fallo.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   COMPILACION EXITOSA: dist\AppKS.exe
echo.
echo   IMPORTANTE: Copia dist\AppKS.exe a la raiz del proyecto
echo   (junto a run.py y la carpeta venv\) para que funcione.
echo ========================================================
echo.
pause
