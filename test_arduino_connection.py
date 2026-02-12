# -*- coding: utf-8 -*-
"""
Arduino Bağlantı Test Scripti
"""
import serial.tools.list_ports
import time

print("=== ARDUINO BAGLANTI TESTI ===\n")

print("1. Mevcut COM Portlari:")
ports = serial.tools.list_ports.comports()
if not ports:
    print("   [HATA] Hic COM portu bulunamadi!")
else:
    for port in ports:
        print(f"   - {port.device} - {port.description}")
        if any(x in port.description for x in ["Arduino", "CH340", "USB Serial"]):
            print(f"      [ARDUINO BULUNDU!]")

print("\n2. Arduino ile Iletisim Testi:")
arduino_found = False

for port in ports:
    if any(x in port.description for x in ["Arduino", "CH340", "USB Serial"]):
        arduino_found = True
        print(f"\n   [TEST] {port.device} ile test ediliyor...")
        try:
            with serial.Serial(port.device, 9600, timeout=2) as ser:
                print(f"      [OK] Port acildi!")
                print(f"      [WAIT] 2 saniye bekleniyor...")
                time.sleep(2)
                
                test_cmd = "REGISTER:10\n"
                print(f"      [SEND] Gonderiliyor: {test_cmd.strip()}")
                ser.write(test_cmd.encode('utf-8'))
                
                print(f"      [WAIT] Cevap bekleniyor...")
                time.sleep(1)
                response = ser.readline().decode('utf-8').strip()
                
                if response:
                    print(f"      [RECV] Cevap alindi: '{response}'")
                else:
                    print(f"      [WARN] Cevap gelmedi")
                    
        except Exception as e:
            print(f"      [ERROR] Hata: {e}")

if not arduino_found:
    print("\n   [HATA] Arduino bulunamadi!")

print("\n=== TEST TAMAMLANDI ===")
