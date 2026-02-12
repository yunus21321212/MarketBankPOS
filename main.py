from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
import requests
import json

# Firebase yöneticisini içe aktar
from firebase_manager import FirebaseManager

from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup

# Pencere boyutu (Test için telefon boyutu)
# Window.size = (360, 640)

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ana Layout (Scroll edilebilir)
        root = BoxLayout(orientation='vertical')
        
        # Üst Başlık
        header = Label(text="A101 SOS\nMarket Yönetim Sistemi", font_size=24, size_hint_y=0.15, halign='center')
        root.add_widget(header)

        # Butonlar için ScrollView
        scroll = ScrollView(size_hint=(1, 0.75))
        grid = GridLayout(cols=2, padding=10, spacing=10, size_hint_y=None)
        grid.bind(minimum_height=grid.setter('height'))

        # --- YENI MODULLER ---
        modules = [
            ("Etiket Okutma", self.go_label_scan, (0.2, 0.6, 0.8, 1)),
            ("Denetim", self.go_audit, (0.8, 0.4, 0.2, 1)),
            ("Raporlar", self.go_reports, (0.4, 0.8, 0.4, 1)),
            ("Mağazalar", self.go_stores, (0.6, 0.4, 0.8, 1)),
            ("%101 İK", self.go_hr, (0.8, 0.8, 0.2, 1)),
        ]

        for text, func, color in modules:
            btn = Button(text=text, size_hint_y=None, height=120, background_normal='', background_color=color)
            btn.bind(on_press=func)
            grid.add_widget(btn)

        # --- ESKI MODULLER (ALTTA) ---
        grid.add_widget(Label(text="--- ARAÇLAR ---", size_hint_y=None, height=40, color=(1,1,1,0.5)))
        grid.add_widget(Label(text="", size_hint_y=None, height=40)) # Boşluk

        btn_pos = Button(text="POS Terminali", size_hint_y=None, height=80, background_normal='', background_color=(0.3, 0.3, 0.3, 1))
        btn_pos.bind(on_press=self.go_to_pos)
        grid.add_widget(btn_pos)

        btn_cashier = Button(text="Kasa Ekranı", size_hint_y=None, height=80, background_normal='', background_color=(0.3, 0.3, 0.3, 1))
        btn_cashier.bind(on_press=self.go_to_cashier)
        grid.add_widget(btn_cashier)

        scroll.add_widget(grid)
        root.add_widget(scroll)

        # Alt Bilgi
        footer = Label(text="v2.0 - A101 SOS Entegrasyonu", font_size=12, size_hint_y=0.1, color=(1,1,1,0.5))
        root.add_widget(footer)

        self.add_widget(root)

    def go_label_scan(self, instance): self.manager.current = 'label_scan_screen'
    def go_audit(self, instance): self.manager.current = 'audit_screen'
    def go_reports(self, instance): self.manager.current = 'reports_screen'
    def go_stores(self, instance): self.manager.current = 'stores_screen'
    def go_hr(self, instance): self.manager.current = 'hr_screen'

    def go_to_pos(self, instance): self.manager.current = 'pos_screen'
    def go_to_cashier(self, instance): self.manager.current = 'cashier_screen'


class POSScreen(Screen):
    """Telefon Arayüzü: Müşteri kartını okutur."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fb = FirebaseManager()
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        self.status_lbl = Label(text="Bekleniyor...", font_size=20)
        self.layout.add_widget(self.status_lbl)

        # Kart Okut Butonu
        self.pay_btn = Button(text="KART OKUT (NFC)", font_size=24, background_color=(0.2, 0.8, 0.2, 1))
        self.pay_btn.bind(on_press=self.simulate_nfc_payment)
        self.pay_btn.disabled = True # Ödeme emri gelmeden basılamaz
        self.layout.add_widget(self.pay_btn)

        back_btn = Button(text="Geri Dön", size_hint=(1, 0.2))
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)

        self.add_widget(self.layout)
        
        # Sürekli sunucuyu dinle
        Clock.schedule_interval(self.check_server, 1.0)

    def check_server(self, dt):
        if self.manager.current != 'pos_screen': return

        data = self.fb.get_transaction()
        if data:
            status = data.get('status')
            amount = data.get('amount')

            if status == 'pending':
                self.status_lbl.text = f"ÖDEME GEREKİYOR\nTutar: {amount} TL"
                self.pay_btn.disabled = False
                self.pay_btn.text = f"ÖDE: {amount} TL"
            elif status == 'success':
                self.status_lbl.text = "✅ ÖDEME BAŞARILI!"
                self.pay_btn.disabled = True
            elif status == 'failed':
                self.status_lbl.text = "❌ İŞLEM REDDEDİLDİ"
                self.pay_btn.disabled = True
            else:
                self.status_lbl.text = "Hazır. Kasa bekleniyor..."
                self.pay_btn.disabled = True

    def simulate_nfc_payment(self, instance):
        # Burada NFC okuma işlemi yapılır.
        # Biz simülasyon olarak status "success" gönderiyoruz.
        
        self.status_lbl.text = "İşleniyor..."
        
        # Mevcut tutarı etiket üzerinden veya kaydedilmiş veriden alalım
        try:
            amount_text = self.pay_btn.text.split(":")[-1].replace("TL", "").strip()
            amount = float(amount_text)
        except:
            amount = 0

        success = self.fb.put_transaction(amount=amount, status="success", cashier="POS_DEVICE")
        if success:
            self.status_lbl.text = "Onaylandı!"
            self.pay_btn.disabled = True

    def go_back(self, instance):
        self.manager.current = 'menu_screen'


class CashierScreen(Screen):
    """Tablet Arayüzü: Kasiyer satışı başlatır."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fb = FirebaseManager()
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)

        layout.add_widget(Label(text="KASİYER PANELİ", font_size=24))

        self.amount_input = Button(text="Tutar Gir: 10 TL (Demo)", font_size=20)
        self.amount_input.bind(on_press=self.start_transaction)
        layout.add_widget(self.amount_input)

        self.reset_btn = Button(text="Sıfırla", background_color=(0.8, 0.2, 0.2, 1))
        self.reset_btn.bind(on_press=self.reset_system)
        layout.add_widget(self.reset_btn)
        
        self.status_lbl = Label(text="Durum: Bekleniyor...")
        layout.add_widget(self.status_lbl)

        back_btn = Button(text="Geri Dön", size_hint=(1, 0.2))
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)

        self.add_widget(layout)
        Clock.schedule_interval(self.update_status, 1.0)

    def start_transaction(self, instance):
        # Demo: Sabit 10 TL istiyoruz
        self.fb.put_transaction(amount=10, status="pending", cashier="Cashier1")
        self.status_lbl.text = "İstek gönderildi. POS bekleniyor..."

    def reset_system(self, instance):
        self.fb.reset_transaction()
        self.status_lbl.text = "Sistem Sıfırlandı."

    def update_status(self, dt):
        if self.manager.current != 'cashier_screen': return
        
        data = self.fb.get_transaction()
        if data:
            self.status_lbl.text = f"Durum: {data.get('status')}\nTutar: {data.get('amount')}"

    def go_back(self, instance):
        self.manager.current = 'menu_screen'


class LabelScanningScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        layout.add_widget(Label(text="ETİKET OKUTMA", font_size=24, size_hint_y=None, height=50))
        
        self.code_input = TextInput(hint_text="Barkod Giriniz (örn: 11)", size_hint_y=None, height=50, multiline=False)
        layout.add_widget(self.code_input)
        
        btn_scan = Button(text="Sorgula", size_hint_y=None, height=50, background_color=(0.2, 0.6, 0.8, 1))
        btn_scan.bind(on_press=self.scan_barcode)
        layout.add_widget(btn_scan)
        
        self.result_lbl = Label(text="Sonuç bekleniyor...", valign='top')
        self.result_lbl.bind(size=self.result_lbl.setter('text_size'))
        layout.add_widget(self.result_lbl)

        back_btn = Button(text="Geri Dön", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def scan_barcode(self, instance):
        code = self.code_input.text.strip()
        if not code: return
        try:
            res = requests.get(f'http://localhost:5000/api/product/{code}')
            if res.status_code == 200:
                p = res.json().get('product')
                self.result_lbl.text = f"Ürün: {p['name']}\nFiyat: {p['price']} TL\nStok: {p['stock']}\nKategori: {p['category']}"
            else:
                self.result_lbl.text = "Ürün bulunamadı!"
        except Exception as e:
            self.result_lbl.text = f"Hata: {str(e)}"

    def go_back(self, instance): self.manager.current = 'menu_screen'

class AuditScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20)
        
        layout.add_widget(Label(text="DENETİM LOGLARI", font_size=24, size_hint_y=None, height=50))
        
        self.log_lbl = Label(text="Yükleniyor...", size_hint_y=None)
        self.log_lbl.bind(texture_size=self.log_lbl.setter('size'))
        
        scroll = ScrollView()
        scroll.add_widget(self.log_lbl)
        layout.add_widget(scroll)
        
        btn_refresh = Button(text="Yenile", size_hint_y=None, height=50, background_color=(0.8, 0.4, 0.2, 1))
        btn_refresh.bind(on_press=self.fetch_logs)
        layout.add_widget(btn_refresh)

        back_btn = Button(text="Geri Dön", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def fetch_logs(self, instance=None):
        try:
            res = requests.get('http://localhost:5000/api/audit/logs')
            logs = res.json()
            self.log_lbl.text = "\n".join(logs) if logs else "Kayıt yok."
        except: self.log_lbl.text = "Sunucuya bağlanılamadı."

    def on_enter(self): self.fetch_logs()
    def go_back(self, instance): self.manager.current = 'menu_screen'

class ReportsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        layout.add_widget(Label(text="RAPORLAR", font_size=24, size_hint_y=None, height=50))
        
        self.stats_lbl = Label(text="Veri çekiliyor...")
        layout.add_widget(self.stats_lbl)
        
        btn_refresh = Button(text="Güncelle", size_hint_y=None, height=50, background_color=(0.4, 0.8, 0.4, 1))
        btn_refresh.bind(on_press=self.fetch_report)
        layout.add_widget(btn_refresh)

        back_btn = Button(text="Geri Dön", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def fetch_report(self, instance=None):
        try:
            res = requests.get('http://localhost:5000/api/rapor/gunluk')
            d = res.json()
            self.stats_lbl.text = f"Toplam Satış: {d['total_sales']} TL\nİşlem Sayısı: {d['transaction_count']}\nMüşteri Sayısı: {d['customer_count']}"
        except: self.stats_lbl.text = "Bağlantı hatası."

    def on_enter(self): self.fetch_report()
    def go_back(self, instance): self.manager.current = 'menu_screen'

class StoresScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20)
        layout.add_widget(Label(text="MAĞAZALAR", font_size=24, size_hint_y=None, height=50))
        
        self.content = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.content)
        layout.add_widget(scroll)
        
        back_btn = Button(text="Geri Dön", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def on_enter(self):
        self.content.clear_widgets()
        try:
            res = requests.get('http://localhost:5000/api/stores')
            stores = res.json()
            for sid, s in stores.items():
                card = BoxLayout(orientation='vertical', size_hint_y=None, height=80, padding=5)
                card.add_widget(Label(text=f"{s['name']}", font_size=18, bold=True))
                card.add_widget(Label(text=f"{s['address']} - {s['phone']}"))
                self.content.add_widget(card)
        except: pass
    
    def go_back(self, instance): self.manager.current = 'menu_screen'

class HRScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20)
        layout.add_widget(Label(text="%101 İK - PERSONEL", font_size=24, size_hint_y=None, height=50))
        
        self.content = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.content.bind(minimum_height=self.content.setter('height'))
        
        scroll = ScrollView()
        scroll.add_widget(self.content)
        layout.add_widget(scroll)
        
        back_btn = Button(text="Geri Dön", size_hint_y=None, height=50)
        back_btn.bind(on_press=self.go_back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def on_enter(self):
        self.content.clear_widgets()
        try:
            res = requests.get('http://localhost:5000/api/hr/employees')
            emps = res.json()
            for e in emps:
                card = BoxLayout(orientation='vertical', size_hint_y=None, height=60, padding=5)
                card.add_widget(Label(text=f"{e['name']} ({e['role']})", bold=True))
                card.add_widget(Label(text=f"Puan: {e['points']} - Seviye: {e['tier']}"))
                self.content.add_widget(card)
        except: pass

    def go_back(self, instance): self.manager.current = 'menu_screen'


class MarketBankApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu_screen'))
        sm.add_widget(LabelScanningScreen(name='label_scan_screen'))
        sm.add_widget(AuditScreen(name='audit_screen'))
        sm.add_widget(ReportsScreen(name='reports_screen'))
        sm.add_widget(StoresScreen(name='stores_screen'))
        sm.add_widget(HRScreen(name='hr_screen'))
        
        sm.add_widget(POSScreen(name='pos_screen'))
        sm.add_widget(CashierScreen(name='cashier_screen'))
        return sm

if __name__ == '__main__':
    MarketBankApp().run()
