import serial
import serial.tools.list_ports
import requests
import time
import urllib3

# SSL Sertifika uyarilarini kapat (Localhost icin)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
SERVER_URL = "https://localhost:5000/api"

def find_arduino():
    """Arduino portunu otomatik bulur."""
    ports = serial.tools.list_ports.comports()
    for port in ports:
        if any(x in port.description for x in ["Arduino", "CH340", "USB Serial"]):
            return port.device
    return None

def complete_transaction(card_id):
    """Gelen kart ID ile sunucudaki bekleyen islemi tamamlar."""
    try:
        data = {"card_id": str(card_id)}
        resp = requests.post(f"{SERVER_URL}/transaction/complete", json=data, verify=False, timeout=5)
        if resp.status_code == 200:
            print(f"✅ ISLEM TAMAMLANDI: Kart {card_id}")
            return True
        else:
            print(f"❌ HATA: {resp.json().get('message')}")
    except Exception as e:
        print(f"📡 SUNUCU HATASI: {e}")
    return False

def main():
    print("========================================")
    print("   MarketBank Arduino-Server Bridge     ")
    print("========================================")
    
    arduino_port = None
    
    while True:
        if not arduino_port:
            arduino_port = find_arduino()
            if arduino_port:
                try:
                    ser = serial.Serial(arduino_port, 9600, timeout=1)
                    print(f"🔗 Arduino Baglandi: {arduino_port}")
                except:
                    arduino_port = None
            else:
                print("⏳ Arduino Bekleniyor...", end="\r")
                time.sleep(2)
                continue

        try:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    print(f"📥 Arduino'dan Veri: {line}")
                    
                    # Eğer veri "REGISTER:" veya "LOAD:" ile başlıyorsa bu bir admin komutudur
                    if ":" in line:
                        print("ℹ️ Admin komutu algilandi. Lütfen Kasiyer GUI kullanin.")
                    else:
                        # Normal Kart ID: Bekleyen islemi tamamla
                        complete_transaction(line)
        except Exception as e:
            print(f"\n⚠️ Baglanti koptu: {e}")
            arduino_port = None
            time.sleep(2)

if __name__ == "__main__":
    main()
