import subprocess
import sys

def install(package):
    print(f"Yükleniyor: {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--user"])

if __name__ == "__main__":
    try:
        # Önce pip'i güncelle
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip", "--user"])
    except:
        pass

    try:
        install("flask")
        install("flask-cors")
        install("firebase-admin")
        install("qrcode")
        install("pyOpenSSL")
        install("cryptography")
        install("requests")
        install("kivy")
        print("\n✅ TÜM YÜKLEMELER BAŞARILI!")
        print("Şimdi 'baslat.bat' ile sistemi HTTPS modunda çalıştırabilirsiniz.")
    except Exception as e:
        print(f"\n❌ HATA OLUŞTU: {e}")
        print("Lütfen internet bağlantınızı kontrol edin.")
    
    input("\nÇıkmak için Enter'a basın...")
