@echo off
title MarketBank - Baslatiliyor...
echo ==========================================
echo    MarketBank Yerel Sunucu ve Dashboard
echo ==========================================
echo.

:: Python kontrolü
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [HATA] Python yuklu degil! Lutfen Python kurun ve PATH'e ekleyin.
    pause
    exit /b
)

:: Gereksinimleri kontrol et/yukle (Opsiyonel ama guvenlik icin)
echo [1/3] Gereksinimler kontrol ediliyor...
pip install -r requirements.txt --quiet

:: Sunucuyu baslat
echo [2/3] Sunucu baslatiliyor (market_bank_core.py)...
start /b python market_bank_core.py

:: Dashboard'u ac
echo [3/3] Web Dashboard tarayicida aciliyor...
timeout /t 3 /nobreak >nul
start http://localhost:5000

echo.
echo ==========================================
echo    MarketBank CALISIYOR! 
echo    Panel: http://localhost:5000
echo    Kapatmak icin bu pencereyi kapatibilirsiniz.
echo ==========================================
pause
