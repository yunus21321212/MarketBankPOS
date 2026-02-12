from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window

# Firebase yöneticisini içe aktar
from firebase_manager import FirebaseManager

# Pencere boyutu (Test için telefon boyutu)
# Window.size = (360, 640)

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        
        lbl = Label(text="MarketBank POS Sistemine\nHoşgeldiniz", font_size=24, halign='center')
        layout.add_widget(lbl)

        btn_pos = Button(text="POS Terminali (Telefon)", background_color=(0.2, 0.6, 0.8, 1))
        btn_pos.bind(on_press=self.go_to_pos)
        layout.add_widget(btn_pos)

        btn_cashier = Button(text="Kasa Ekranı (Tablet)", background_color=(0.8, 0.4, 0.2, 1))
        btn_cashier.bind(on_press=self.go_to_cashier)
        layout.add_widget(btn_cashier)

        self.add_widget(layout)

    def go_to_pos(self, instance):
        self.manager.current = 'pos_screen'

    def go_to_cashier(self, instance):
        self.manager.current = 'cashier_screen'


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


class MarketBankApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name='menu_screen'))
        sm.add_widget(POSScreen(name='pos_screen'))
        sm.add_widget(CashierScreen(name='cashier_screen'))
        return sm

if __name__ == '__main__':
    MarketBankApp().run()
