@echo off
title MarketBank - Profesyonel Mobil Baglanti
echo MarketBank Hazirlaniliyor...
echo [!] Lutfen bekleyin, yerel IP adresiniz tespit ediliyor...
echo.

:: Bulunulan dizindeki IP'yi gostermek icin gecici bir python kodu calistiriyoruz
python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('8.8.8.8', 80)); print('>>> TELEFONUNUZA/TABLETINIZE BU ADRESI YAZIN: https://' + s.getsockname()[0] + ':5000'); s.close()"

echo.
echo [1/2] Web Paneli Aciliyor (Yerel)...
start https://localhost:5000
echo [2/2] POS Cihazi Ekrani Aciliyor (Yerel)...
start https://localhost:5000/pos
echo.
echo [!] MOBILDE ACARKEN: 'Baglantiniz Gizli Degil' uyarisi gelirse 'Gelismis -> Ilerle' deyin.
echo.
python market_bank_core.py
pause
