@echo off
title MarketBank - A101 SOS System
echo [INFO] Sunucu Baslatiliyor...
start "MarketBank Server" python market_bank_core.py

echo [INFO] Sunucunun acilmasi bekleniyor (3 saniye)...
timeout /t 3 /nobreak >nul

echo [INFO] Tarayici Sekmeleri Aciliyor...
start http://localhost:5000/
start http://localhost:5000/pos

echo [INFO] Kivy Uygulamasi (A101 SOS) Baslatiliyor...
start "A101 SOS App" python main.py

echo [BASARILI] Tum sistemler calisiyor.
pause