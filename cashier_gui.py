import threading
import serial
import serial.tools.list_ports
import time

# --- AYARLAR ---
SERVER_URL = "http://localhost:5000/api"
CURRENT_USER = None # Giriş yapan kullanıcı

# --- API FONKSİYONLARI ---
def api_login(user_id, password):
    try:
        data = {"user_id": user_id, "password": password}
        resp = requests.post(f"{SERVER_URL}/login", json=data)
        if resp.status_code == 200:
            return resp.json()
    except:
        return None
    return None

def api_satis(kart_id, tutar):
    try:
        data = {"card_id": kart_id, "amount": tutar, "cashier_id": CURRENT_USER['name']}
        resp = requests.post(f"{SERVER_URL}/odeme", json=data)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def api_bakiye_ekle(kart_id, tutar):
    try:
        data = {"card_id": kart_id, "amount": tutar, "cashier_id": CURRENT_USER['name']}
        resp = requests.post(f"{SERVER_URL}/bakiye_ekle", json=data)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def api_kart_tanit(kart_id, isim, bakiye):
    try:
        data = {"card_id": kart_id, "name": isim, "initial_balance": bakiye, "cashier_id": CURRENT_USER['name']}
        resp = requests.post(f"{SERVER_URL}/kart_tanit", json=data)
        return resp.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- ARAYÜZ (GUI) ---
class MarketBankApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MarketBank - Kasa Sistemi")
        self.root.geometry("800x600")
        self.root.configure(bg="#2c3e50") # Koyu tema
        
        self.toplam = 0.0
        
        # Arduino Bağlantısı
        self.arduino = None
        self.serial_thread = None
        self.baglan_arduino()

        self.giris_ekrani()

    def baglan_arduino(self):
        """Arduino'yu otomatik bulup bağlanır."""
        def listen():
            while True:
                if not self.arduino:
                    ports = serial.tools.list_ports.comports()
                    for port in ports:
                        if "Arduino" in port.description or "CH340" in port.description or "USB Serial" in port.description:
                            try:
                                self.arduino = serial.Serial(port.device, 9600, timeout=1)
                                print(f"Arduino bağlandı: {port.device}")
                                break
                            except: pass
                
                if self.arduino:
                    try:
                        line = self.arduino.readline().decode('utf-8').strip()
                        if line:
                            print(f"Arduino'dan gelen kod: {line}")
                            # Gelen kodu GUI'de göster veya bir değişkene yaz
                            self.root.after(0, lambda: self.handle_arduino_data(line))
                    except:
                        self.arduino = None # Bağlantı koptu
                time.sleep(0.1)

        self.serial_thread = threading.Thread(target=listen, daemon=True)
        self.serial_thread.start()

    def handle_arduino_data(self, code):
        """Arduino'dan gelen kodu işler."""
        if ":" in code:
            cmd, val = code.split(":")
            if cmd == "REGISTER":
                self.root.after(0, lambda: self.kart_tanit_penceresi_with_id(val))
            elif cmd == "LOAD":
                self.root.after(0, lambda: self.bakiye_yukle_penceresi_with_id(val))
        else:
            messagebox.showinfo("Arduino", f"Arduino'dan Kart Okundu: {code}\nKaydetmek veya Yüklemek için bu kodu kullanabilirsiniz.")

    def kart_tanit_penceresi_with_id(self, kart_id):
        isim = simpledialog.askstring("Müşteri Bilgisi", f"Kart ID: {kart_id}\nMüşteri Adı Soyadı:")
        if not isim: return
        bakiye = simpledialog.askfloat("Açılış Bakiyesi", "Başlangıç Bakiyesi (Opsiyonel):", initialvalue=0)
        res = api_kart_tanit(kart_id, isim, bakiye)
        if res['status'] == 'success':
            messagebox.showinfo("Başarılı", "Müşteri Sisteme Kaydedildi ✅")
        else:
            messagebox.showerror("Hata", res['message'])

    def bakiye_yukle_penceresi_with_id(self, kart_id):
        tutar = simpledialog.askfloat("Bakiye Yükle", f"Kart ID: {kart_id}\nYüklenecek Tutar (TL):")
        if not tutar: return
        res = api_bakiye_ekle(kart_id, tutar)
        if res['status'] == 'success':
            messagebox.showinfo("Başarılı", f"Yükleme Tamamlandı.\nYeni Bakiye: {res['new_balance']} TL")
        else:
            messagebox.showerror("Hata", res['message'])

    def temizle(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def giris_ekrani(self):
        self.temizle()
        frame = tk.Frame(self.root, bg="white", padx=20, pady=20)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="KASA GİRİŞİ", font=("Arial", 20, "bold"), bg="white").pack(pady=10)
        
        tk.Label(frame, text="Kullanıcı ID:", font=("Arial", 12), bg="white").pack(anchor="w")
        self.entry_user = tk.Entry(frame, font=("Arial", 14))
        self.entry_user.pack(pady=5, fill="x")
        self.entry_user.insert(0, "ADMIN_U") # Test için

        tk.Label(frame, text="Şifre:", font=("Arial", 12), bg="white").pack(anchor="w")
        self.entry_pass = tk.Entry(frame, font=("Arial", 14), show="*")
        self.entry_pass.pack(pady=5, fill="x")
        self.entry_pass.insert(0, "admin") # Test için

        tk.Button(frame, text="GİRİŞ YAP", bg="#27ae60", fg="white", font=("Arial", 14, "bold"), 
                  command=self.login_yap).pack(pady=20, fill="x")

    def login_yap(self):
        user_id = self.entry_user.get()
        password = self.entry_pass.get()
        res = api_login(user_id, password)
        
        if res and res['status'] == 'success':
            global CURRENT_USER
            CURRENT_USER = res
            if res['role'] == 'admin':
                self.admin_paneli() # Şimdilik worker ile aynı yere yönlendirebiliriz veya özelleştirebiliriz
            else:
                self.kasa_ekrani()
        else:
            messagebox.showerror("Hata", "Giriş Başarısız! Sunucu açık mı?")

    def kasa_ekrani(self):
        self.temizle()

        # ÜST BAR
        top_bar = tk.Frame(self.root, bg="#34495e", height=50)
        top_bar.pack(fill="x")
        tk.Label(top_bar, text=f"Kasiyer: {CURRENT_USER['name']} ({CURRENT_USER['role']})", 
                 fg="white", bg="#34495e", font=("Arial", 12)).pack(side="left", padx=10, pady=10)
        
        if CURRENT_USER['role'] == 'admin':
            tk.Button(top_bar, text="⚙ ADMİN PANELİ", bg="#f39c12", fg="white", 
                      command=self.admin_paneli).pack(side="left", padx=10, pady=5)

        tk.Button(top_bar, text="ÇIKIŞ", bg="#c0392b", fg="white", command=self.giris_ekrani).pack(side="right", padx=10, pady=5)

        # SOL PANEL - ÜRÜNLER (Butonlar A101 tarzı)
        self.left_panel = tk.Frame(self.root, bg="#bdc3c7", width=500)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        self.urunleri_yenile()
    
    def urunleri_yenile(self):
        for widget in self.left_panel.winfo_children():
            widget.destroy()

        try:
            resp = requests.get(f"{SERVER_URL}/urunler")
            urunler = resp.json()
        except:
            urunler = {}

        row, col = 0, 0
        for barcode, info in urunler.items():
            btn_text = f"{info['name']}\n{info['price']} TL\nStok: {info['stock']}"
            btn = tk.Button(self.left_panel, text=btn_text, font=("Arial", 12, "bold"), bg="white",
                            height=4, width=15, command=lambda a=info['name'], f=info['price']: self.sepete_ekle(a, f))
            btn.grid(row=row, column=col, padx=5, pady=5)
            col += 1
            if col > 2:
                col = 0
                row += 1

        # SAĞ PANEL - SEPET VE İŞLEMLER
        right_panel = tk.Frame(self.root, bg="white", width=300)
        right_panel.pack(side="right", fill="y", padx=10, pady=10)

        tk.Label(right_panel, text="SEPET", font=("Arial", 16, "bold"), bg="white").pack(pady=5)
        
        self.listbox = tk.Listbox(right_panel, font=("Courier", 12), width=30, height=15)
        self.listbox.pack(padx=5, pady=5)

        self.lbl_toplam = tk.Label(right_panel, text="TOPLAM: 0.00 TL", font=("Arial", 18, "bold"), fg="#c0392b", bg="white")
        self.lbl_toplam.pack(pady=10)

        # BÜYÜK İŞLEM BUTONLARI
        btn_frame = tk.Frame(right_panel, bg="white")
        btn_frame.pack(fill="x", pady=10)

        tk.Button(btn_frame, text="SEPETİ TEMİZLE", bg="#e74c3c", fg="white", font=("Arial", 12), command=self.sepeti_temizle).pack(fill="x", pady=2)
        tk.Button(btn_frame, text="ÖDEME AL (NAKİT/KART)", bg="#27ae60", fg="white", font=("Arial", 16, "bold"), command=self.odeme_penceresi).pack(fill="x", pady=10)

        # ALT BAR - EKSTRA İŞLEMLER (ADMIN/WORKER)
        bottom_frame = tk.Frame(right_panel, bg="#ecf0f1", pady=10)
        bottom_frame.pack(fill="x", side="bottom")

        tk.Button(bottom_frame, text="➕ BAKİYE YÜKLE", bg="#2980b9", fg="white", command=self.bakiye_yukle_penceresi).pack(fill="x", pady=2)
        tk.Button(bottom_frame, text="🆔 KART TANIT", bg="#8e44ad", fg="white", command=self.kart_tanit_penceresi).pack(fill="x", pady=2)

    def sepete_ekle(self, ad, fiyat):
        self.sepet.append((ad, fiyat))
        self.toplam += fiyat
        self.listbox.insert(tk.END, f"{ad:<15} {fiyat} TL")
        self.lbl_toplam.config(text=f"TOPLAM: {self.toplam:.2f} TL")

    def sepeti_temizle(self):
        self.sepet = []
        self.toplam = 0.0
        self.listbox.delete(0, tk.END)
        self.lbl_toplam.config(text=f"TOPLAM: {self.toplam:.2f} TL")

    def odeme_penceresi(self):
        if self.toplam == 0:
            return
            
        # Kasiyer sadece "POS'a Gönder" der
        try:
            data = {"amount": self.toplam, "cashier_id": CURRENT_USER['name']}
            resp = requests.post(f"{SERVER_URL}/transaction/start", json=data)
            if resp.status_code == 200:
                messagebox.showinfo("POS", "Tutar POS cihazına gönderildi.\nMüşterinin kart okutması bekleniyor...")
                self.sepeti_temizle() # İşlem başladı, sepeti temizleyebiliriz (veya onay bekleyebiliriz)
            else:
                messagebox.showerror("Hata", "POS Bağlantı Hatası")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def bakiye_yukle_penceresi(self):
        kart_id = simpledialog.askstring("Bakiye Yükle", "Yüklenecek Kart ID:")
        if not kart_id: return
        
        tutar = simpledialog.askfloat("Bakiye Yükle", "Yüklenecek Tutar (TL):")
        if not tutar: return

        # Çalışan Limiti Kontrolü (GUI tarafında da uyarı)
        if tutar > 500:
            onay = messagebox.askyesno("Limit Uyarısı", "500 TL üzeri yükleme yapıyorsunuz. Devam edilsin mi? (Loglanacak)")
            if not onay: return

        res = api_bakiye_ekle(kart_id, tutar)
        if res['status'] == 'success':
            messagebox.showinfo("Başarılı", f"Yükleme Tamamlandı.\nYeni Bakiye: {res['new_balance']} TL")
        else:
            messagebox.showerror("Hata", res['message'])

    def kart_tanit_penceresi(self):
        kart_id = simpledialog.askstring("Kart Tanıt", "Yeni Kartı Okutun (1-99 ID):")
        if not kart_id: return
        
        # Kart ID Aralığı Kontrolü (GUI'den de ekleyelim)
        try:
            k_id_int = int(kart_id)
            if not (1 <= k_id_int <= 99):
                messagebox.showerror("Hata", "Lütfen 1 ile 99 arasında bir Kart ID girin!")
                return
        except:
            messagebox.showerror("Hata", "Kart ID sayısal olmalıdır!")
            return

        isim = simpledialog.askstring("Müşteri Bilgisi", "Müşteri Adı Soyadı:")
        if not isim: return

        bakiye = simpledialog.askfloat("Açılış Bakiyesi", "Başlangıç Bakiyesi (Opsiyonel):", initialvalue=0)
        
        res = api_kart_tanit(kart_id, isim, bakiye)
        if res['status'] == 'success':
            messagebox.showinfo("Başarılı", "Müşteri Sisteme Kaydedildi ✅")
        else:
            messagebox.showerror("Hata", res['message'])

    def admin_paneli(self):
        self.temizle()
        tk.Label(self.root, text="ADMİN KONTROL PANELİ", font=("Arial", 24, "bold"), fg="white", bg="#2c3e50").pack(pady=20)
        
        btn_frame = tk.Frame(self.root, bg="#2c3e50")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="📦 Ürün Yönetimi", font=("Arial", 14), width=20, command=self.urun_yonetimi).pack(pady=5)
        tk.Button(btn_frame, text="👥 Kullanıcı Yönetimi", font=("Arial", 14), width=20, command=self.kullanici_yonetimi).pack(pady=5)
        tk.Button(btn_frame, text="📊 Satış Raporları", font=("Arial", 14), width=20, command=self.satis_raporlari).pack(pady=5)
        tk.Button(btn_frame, text="🔙 Kasaya Dön", font=("Arial", 14), bg="#7f8c8d", fg="white", width=20, command=self.kasa_ekrani).pack(pady=20)

    def urun_yonetimi(self):
        # Ürün Ekleme/Düzenleme Basit Dialog
        barcode = simpledialog.askstring("Ürün Ekle", "Barkod Okutun:")
        if not barcode: return
        name = simpledialog.askstring("Ürün Ekle", "Ürün Adı:")
        price = simpledialog.askfloat("Ürün Ekle", "Fiyat:")
        stock = simpledialog.askinteger("Ürün Ekle", "Stok Miktarı:")
        
        try:
            resp = requests.post(f"{SERVER_URL}/urun_ekle", json={"barcode": barcode, "name": name, "price": price, "stock": stock})
            if resp.status_code == 200:
                messagebox.showinfo("Başarılı", "Ürün kaydedildi.")
                self.urunleri_yenile() # Listeyi güncelle
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def kullanici_yonetimi(self):
        user_id = simpledialog.askstring("Kullanıcı Ekle", "Kullanıcı ID (Örn: WORKER_2):")
        if not user_id: return
        name = simpledialog.askstring("Kullanıcı Ekle", "Ad Soyad:")
        role = simpledialog.askstring("Kullanıcı Ekle", "Rol (admin/worker):", initialvalue="worker")
        
        try:
            resp = requests.post(f"{SERVER_URL}/kullanici_ekle", json={"user_id": user_id, "name": name, "role": role})
            if resp.status_code == 200:
                messagebox.showinfo("Başarılı", "Kullanıcı kaydedildi.")
        except Exception as e:
            messagebox.showerror("Hata", str(e))

    def satis_raporlari(self):
        try:
            resp = requests.get(f"{SERVER_URL}/rapor/gunluk")
            data = resp.json()
            msg = f"Bugünkü Toplam Ciro: {data['total_sales']} TL\nToplam İşlem Sayısı: {data['transaction_count']}"
            messagebox.showinfo("Günlük Rapor", msg)
        except Exception as e:
            messagebox.showerror("Hata", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = MarketBankApp(root)
    root.mainloop()
