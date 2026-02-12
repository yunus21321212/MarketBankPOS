import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.popup import Popup
# Kivy için SSL hatasını yoksaymak bazen gerekebilir (Android'de sorun çıkarsa)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
# DİKKAT: Android cihazda localhost çalışmaz!
# Bilgisayarınızın IP adresini buraya yazın (ipconfig ile bakın).
SERVER_IP = "https://192.168.1.5:5000/api" 

class POSScreen(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.padding = 20
        self.spacing = 20
        
        # Üst Başlık
        self.lbl_status = Label(text="POS HAZIR\nÖdeme Bekleniyor...", font_size=30, halign="center")
        self.add_widget(self.lbl_status)
        
        # Durum Göstergesi (Renk)
        self.status_color = [0.2, 0.6, 0.8, 1] # Mavi
        
        # Kart Okut Butonu (Simülasyon)
        self.btn_pay = Button(text="KART OKUT (NFC)", font_size=25, background_color=self.status_color)
        self.btn_pay.bind(on_press=self.on_card_read)
        self.btn_pay.disabled = True # Ödeme gelene kadar pasif
        self.add_widget(self.btn_pay)

        # Sürekli Sunucuyu Kontrol Et (Her 1 saniyede)
        Clock.schedule_interval(self.check_server, 1.0)
        
    def check_server(self, dt):
        try:
            # verify=False ile SSL sertifika hatasını (self-signed olduğu için) yok sayıyoruz
            resp = requests.get(f"{SERVER_IP}/transaction/status", timeout=2, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status")
                amount = data.get("amount")
                
                if status == "pending":
                    self.lbl_status.text = f"ÖDEME BEKLENİYOR\nTUTAR: {amount} TL"
                    self.btn_pay.disabled = False
                    self.btn_pay.background_color = [0.9, 0.7, 0.1, 1] # Sarı
                    self.btn_pay.text = "KART OKUT (NFC)"
                elif status == "idle":
                    self.lbl_status.text = "POS HAZIR\nBekleniyor..."
                    self.btn_pay.disabled = True
                    self.btn_pay.background_color = [0.2, 0.6, 0.8, 1] # Mavi
                elif status == "success":
                    self.lbl_status.text = "✅ İŞLEM BAŞARILI"
                    self.btn_pay.disabled = True
                    self.btn_pay.background_color = [0.2, 0.8, 0.2, 1] # Yeşil
                elif status == "failed":
                    self.lbl_status.text = "❌ İŞLEM REDDEDİLDİ"
                    self.btn_pay.disabled = True
                    self.btn_pay.background_color = [0.8, 0.2, 0.2, 1] # Kırmızı
                    
        except Exception as e:
            self.lbl_status.text = "Bağlantı Hatası!\nSunucu IP Kontrol Et"
            print(e)

    def on_card_read(self, instance):
        # Gerçek uygulamada burada NFC kütüphanesi (plyer.nfc veya android.nfc) kullanılır.
        # Bu demo için sabit bir kart ID gönderiyoruz.
        target_card_id = "000000" # Admin Kartı (Test)
        
        self.lbl_status.text = "İşlem Yapılıyor..."
        self.send_payment(target_card_id)

    def send_payment(self, card_id):
        try:
            data = {"card_id": card_id}
            # verify=False ekledik
            resp = requests.post(f"{SERVER_IP}/transaction/complete", json=data, timeout=5, verify=False)
            # Sonuç zaten check_server döngüsünde güncellenecek (status değiştiği için)
            if resp.status_code != 200:
                self.lbl_status.text = "Hata Oluştu"
        except:
             self.lbl_status.text = "Sunucuya Ulaşılamadı"

class MarketPOSApp(App):
    def build(self):
        return POSScreen()

if __name__ == '__main__':
    MarketPOSApp().run()
