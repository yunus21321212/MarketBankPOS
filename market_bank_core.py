import json
import os
import time
import threading
import serial
import serial.tools.list_ports
import random
from datetime import datetime
from flask import Flask, request, jsonify, render_template

# SSL Sertifika uyarilarini kapat (Localhost icin)
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- AYARLAR ---
DB_FILE = "market_bank_db.json"
LOG_FILE = "transaction_log.txt"
base_dir = os.path.abspath(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, 'static')
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, static_folder=static_dir, template_folder=template_dir)

# --- VERİTABANI YÖNETİMİ ---
def db_yukle():
    if not os.path.exists(DB_FILE):
        varsayilan_db = {
            "users": {
                "ADMIN_U": {"name": "Süper Admin", "role": "admin", "password": "admin", "balance": 999999, "points": 1000, "tier": "Platinum", "iban": "MBANK-ADMIN"},
                "WORKER_1": {"name": "Kasiyer Ahmet", "role": "worker", "password": "123", "balance": 5000, "points": 100, "tier": "Bronze", "iban": "MBANK-WORKER"},
                "KASIYER_1": {"name": "Mehmet Kasiyer", "role": "cashier", "password": "123", "balance": 5000, "points": 100, "tier": "Bronze", "iban": "MBANK-CASH"},
                "STOK_1": {"name": "Ayşe Depo", "role": "stock_manager", "password": "123", "balance": 5000, "points": 50, "tier": "Bronze", "iban": "MBANK-STOCK"}
            },
            "cards": {"000000": "ADMIN_U", "123456": "KASIYER_1"},
            "products": {
                "11": {"name": "Ekmek", "price": 10.0, "stock": 100, "min_stock": 20, "category": "Gıda"},
                "25": {"name": "Süt", "price": 25.0, "stock": 50, "min_stock": 10, "category": "Süt Ürünleri"},
                "32": {"name": "Yumurta (30lu)", "price": 120.0, "stock": 20, "min_stock": 5, "category": "Gıda"}
            },
            "reports": {"daily_sales": 0.0, "transactions": [], "stock_logs": []},
            "vouchers": {}, # PIN: {"amount": X}
            "approvals": [],
            "stores": {
                "101": {"name": "Merkez Şube", "address": "Istanbul, Kadikoy", "manager": "Ahmet Yilmaz", "phone": "0216 123 45 67"},
                "102": {"name": "Uskudar Subesi", "address": "Istanbul, Uskudar", "manager": "Mehmet Demir", "phone": "0216 987 65 43"}
            }
        }
        db_kaydet(varsayilan_db)
        return varsayilan_db
    
    with open(DB_FILE, 'r', encoding='utf-8') as f:
        db = json.load(f)
        required_keys = {
            "users": {}, "cards": {}, "products": {}, 
            "reports": {"daily_sales": 0.0, "transactions": [], "stock_logs": []}, 
            "approvals": [],
            "stores": {}
        }
        updated = False
        for key, default_val in required_keys.items():
            if key not in db: db[key] = default_val; updated = True
            
        # Migration: Ensure all staff have passwords & IBANs
        default_passwords = {"ADMIN_U": "admin", "KASIYER_1": "123", "WORKER_1": "123", "STOK_1": "123"}
        for uid, user in db['users'].items():
            if user.get('role') in ['admin', 'cashier', 'stock_manager', 'worker']:
                if 'password' not in user:
                    user['password'] = default_passwords.get(uid, "123")
                    updated = True
                if 'iban' not in user:
                    user['iban'] = f"MBANK-{uid.split('_')[-1]}".upper()
                    updated = True
            
        # Ön Kayıtlı Kartların Var Olduğundan Emin Ol (Test Kolaylığı)
        test_cards = {"10": "USER_10", "20": "USER_20", "30": "USER_30"}
        for cid, uid in test_cards.items():
            if cid not in db['cards']:
                db['cards'][cid] = uid
                db['users'][uid] = {"name": f"Test Musteri {cid}", "role": "customer", "balance": 500, "points": 0, "tier": "Bronze"}
                updated = True
        
        if 'vouchers' not in db: db['vouchers'] = {}; updated = True
        
        if updated: db_kaydet(db)
        return db

def db_kaydet(db):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def log_islem(islem_tipi, detay, yapan="Sistem"):
    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_mesaji = f"[{zaman}] [{islem_tipi}] {yapan}: {detay}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f: f.write(log_mesaji)
    print(f" >>> {log_mesaji.strip()}")

# --- POS SENKRONİZASYON ---
active_transaction = {"amount": 0.0, "status": "idle", "cashier": None, "cart": [], "final_amount": 0.0, "type": "payment"}

@app.route('/')
def index(): return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    uid, pw = data.get('user_id'), data.get('password')
    db = db_yukle()
    if uid in db['users']:
        u = db['users'][uid]
        if u['role'] in ['admin', 'cashier', 'stock_manager', 'worker']:
            if u.get('password') != pw: return jsonify({"status": "error", "message": "Hatali Sifre"}), 401
        log_islem("GIRIS", f"{u['name']} giris yapti.", yapan=u['name'])
        return jsonify({"status": "success", "role": u['role'], "name": u['name'], "iban": u.get('iban', 'MBANK-00000')})
    return jsonify({"status": "error", "message": "Kullanici Bulunamadi"}), 401

@app.route('/pos')
def pos_page(): return render_template('pos.html')

@app.route('/bank')
def bank_page(): return render_template('bank.html')

@app.route('/admin/money')
def admin_money_page(): return render_template('admin_money.html')

@app.route('/api/transaction/complete', methods=['POST'])
def api_islem_tamamla():
    """Web tabanli POS simulatorunden gelen kart okuma istegi."""
    data = request.json
    kart_id = str(data.get('card_id', ''))
    if not kart_id: return jsonify({"status": "error", "message": "Kart ID eksik"}), 400
    
    # Arduino ile ayni mantigi kullan (S:Isim:Bakiye veya E:Mesaj seklinde doner)
    result = local_complete_transaction(kart_id)
    
    if result.startswith('S:'):
        parts = result.split(':')
        return jsonify({"status": "success", "name": parts[1], "balance": parts[2]})
    else:
        return jsonify({"status": "error", "message": result[2:]})

@app.route('/api/transaction/status', methods=['GET'])
def islem_durumu(): return jsonify(active_transaction)

@app.route('/api/sale/complete', methods=['POST'])
def satis_tamamla():
    global active_transaction
    data = request.json
    p_type = data.get('payment_type')
    amount = float(data.get('final_amount', 0.0))
    cashier = data.get('cashier_id', 'Sistem')
    cart = data.get('cart', [])

    if p_type == 'card':
        active_transaction = {
            "amount": amount, "final_amount": amount, "status": "pending", 
            "cashier": cashier, "cart": cart, "type": "payment"
        }
        return jsonify({"status": "pending"})
    
    # Nakit Satis
    db = db_yukle()
    db['reports']['daily_sales'] += amount
    db['reports']['transactions'].append({
        "time": datetime.now().strftime("%H:%M:%S"), 
        "amount": amount, "cashier": cashier, "payment": "cash"
    })
    for item in cart:
        bc = item['barcode']
        if bc in db['products']: db['products'][bc]['stock'] -= item['qty']
    
    db_kaydet(db)
    log_islem("SATIS", f"NAKIT: {amount} TL", yapan=cashier)
    return jsonify({"status": "success"})

@app.route('/api/bank/load_nfc_start', methods=['POST'])
def nfc_yukleme_baslat():
    global active_transaction
    data = request.json
    amount = float(data.get('amount', 0.0))
    active_transaction = {
        "amount": amount, "final_amount": amount, "status": "pending", 
        "cashier": data.get('cashier_id', 'Sistem'), "type": "load"
    }
    return jsonify({"status": "success"})

@app.route('/api/rapor/gunluk', methods=['GET'])
def rapor_gunluk():
    db = db_yukle()
    r = db['reports']
    return jsonify({
        "total_sales": r.get('daily_sales', 0.0),
        "transaction_count": len(r.get('transactions', [])),
        "customer_count": len([u for u in db['users'].values() if u['role'] == 'customer']),
        "transactions": r.get('transactions', [])[-10:] # Son 10 islem
    })

@app.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    db = db_yukle()
    users = [{"name": u['name'], "points": u.get('points', 0), "tier": u.get('tier', 'Bronze')} for u in db['users'].values() if u['role'] == 'customer']
    users.sort(key=lambda x: x['points'], reverse=True)
    return jsonify(users[:5])

@app.route('/api/products', methods=['GET'])
def urunler_hepsi():
    db = db_yukle()
    return jsonify(db['products'])

@app.route('/api/products/add', methods=['POST'])
def urun_ekle():
    data = request.json
    db = db_yukle()
    bc = str(data.get('barcode'))
    if bc in db['products']: return jsonify({"status": "error", "message": "Bu barkod zaten kayitli"}), 400
    db['products'][bc] = {
        "name": data.get('name'), "price": float(data.get('price')),
        "stock": int(data.get('stock', 0)), "min_stock": int(data.get('min_stock', 10)),
        "category": data.get('category', 'Genel')
    }
    db_kaydet(db)
    return jsonify({"status": "success", "message": "Urun eklendi"})

@app.route('/api/products/update', methods=['POST'])
def urun_guncelle():
    data = request.json
    db = db_yukle()
    bc = str(data.get('barcode'))
    if bc in db['products']:
        db['products'][bc]['stock'] = int(data.get('stock'))
        db_kaydet(db)
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404

@app.route('/api/kart_tanit', methods=['POST'])
def kart_tanit():
    data = request.json
    db = db_yukle()
    cid, name = str(data.get('card_id')), data.get('name')
    short_id = str(data.get('short_id', '')).strip()
    
    if cid in db['cards']: return jsonify({"status": "error", "message": "Kart zaten kayitli"}), 400
    if short_id and short_id in db['cards']: return jsonify({"status": "error", "message": "Kisa kod zaten kullanimda"}), 400
    
    uid = f"USER_{int(time.time())}"
    db['users'][uid] = {"name": name, "role": "customer", "balance": 500, "points": 0, "tier": data.get('tier', 'Bronze')}
    db['cards'][cid] = uid
    if short_id:
        db['cards'][short_id] = uid
        
    db_kaydet(db)
    return jsonify({"status": "success", "message": f"{name} kaydedildi (Kisa Kod: {short_id if short_id else 'Yok'})"})

@app.route('/api/admin/withdraw', methods=['POST'])
def admin_withdraw():
    """Admin para çekme (bakiye azaltma)"""
    data = request.json
    db = db_yukle()
    card_id = str(data.get('card_id'))
    amount = float(data.get('amount', 0))
    
    if card_id not in db['cards']:
        return jsonify({"status": "error", "message": "Kart bulunamadı"}), 404
    
    uid = db['cards'][card_id]
    user = db['users'][uid]
    
    if user['balance'] < amount:
        return jsonify({"status": "error", "message": "Yetersiz bakiye"}), 400
    
    user['balance'] -= amount
    db_kaydet(db)
    log_islem("PARA_CEK", f"{amount} TL çekildi - {user['name']}", yapan="Admin")
    
    return jsonify({
        "status": "success", 
        "message": f"{amount} TL çekildi",
        "new_balance": user['balance']
    })

# --- ONAY SISTEMI ---
@app.route('/api/admin/request_approval', methods=['POST'])
def request_approval():
    data = request.json
    db = db_yukle()
    req = {
        "id": int(time.time()), "type": data.get('type'), "details": data.get('details'),
        "amount": data.get('amount', 0), "cashier": data.get('cashier_id'), "status": "pending"
    }
    db['approvals'].append(req)
    db_kaydet(db)
    return jsonify({"status": "success", "request_id": req['id']})

@app.route('/api/admin/pending_approvals', methods=['GET'])
def pending_approvals():
    db = db_yukle()
    return jsonify([a for a in db['approvals'] if a['status'] == 'pending'])

@app.route('/api/admin/approve', methods=['POST'])
def approve_request():
    data = request.json
    db = db_yukle()
    rid, dec = data.get('request_id'), data.get('decision')
    for a in db['approvals']:
        if a['id'] == rid:
            a['status'] = dec
            db_kaydet(db)
            return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404



@app.route('/api/admin/check_request/<int:rid>', methods=['GET'])
def check_request(rid):
    db = db_yukle()
    for a in db['approvals']:
        if a['id'] == rid: return jsonify({"status": a['status']})
    return jsonify({"status": "not_found"}), 404

# --- A101 SOS MODULU ---
@app.route('/api/stores', methods=['GET'])
def get_stores():
    db = db_yukle()
    return jsonify(db.get('stores', {}))

@app.route('/api/hr/employees', methods=['GET'])
def get_employees():
    db = db_yukle()
    employees = []
    for uid, u in db['users'].items():
        if u['role'] in ['worker', 'cashier', 'stock_manager', 'admin']:
            employees.append({
                "name": u['name'],
                "role": u['role'],
                "tier": u.get('tier', 'Bronze'),
                "points": u.get('points', 0)
            })
    return jsonify(employees)

@app.route('/api/audit/logs', methods=['GET'])
def get_audit_logs():
    # Read last 50 lines of log file
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            return jsonify([line.strip() for line in lines[-50:]])
    except FileNotFoundError:
        return jsonify([])

@app.route('/api/product/<barcode>', methods=['GET'])
def get_product(barcode):
    db = db_yukle()
    product = db['products'].get(barcode)
    if product:
        return jsonify({"status": "success", "product": product})
    return jsonify({"status": "error", "message": "Urun bulunamadi"}), 404

# --- BANKA ISLEMLERI ---
@app.route('/api/bank/transfer', methods=['POST'])
def bank_transfer():
    data = request.json
    db = db_yukle()
    f_iban, t_iban = data.get('from_iban'), data.get('to_iban')
    amt = float(data.get('amount', 0))
    
    sender = next((u for u in db['users'].values() if u.get('iban') == f_iban), None)
    receiver = next((u for u in db['users'].values() if u.get('iban') == t_iban), None)
    
    if not sender: return jsonify({"status": "error", "message": "Gonderici bulunamadi"}), 404
    if not receiver: return jsonify({"status": "error", "message": "Alici bulunamadi"}), 404
    if sender['balance'] < amt: return jsonify({"status": "error", "message": "Yetersiz bakiye"}), 400
    
    sender['balance'] -= amt
    receiver['balance'] += amt
    db_kaydet(db)
    log_islem("TRANSFER", f"{amt} TL: {f_iban} -> {t_iban}", yapan=sender['name'])
    return jsonify({"status": "success"})

@app.route('/api/bank/check_balance', methods=['GET'])
def check_balance():
    card_id = request.args.get('card_id')
    db = db_yukle()
    if card_id in db['cards']:
        u = db['users'][db['cards'][card_id]]
        return jsonify({"status": "success", "name": u['name'], "balance": u['balance']})
    elif card_id in db['users']:
        u = db['users'][card_id]
        return jsonify({"status": "success", "name": u['name'], "balance": u['balance']})
    return jsonify({"status": "error", "message": "Bulunamadi"}), 404

# --- ARDUINO UNLOCK API ---
unlock_queue = []  # Global unlock komutu kuyruğu

@app.route('/api/arduino/unlock', methods=['POST'])
def unlock_arduino():
    """Web'den Arduino kilidini açma komutu gönder"""
    global unlock_queue
    unlock_queue.append(time.time())  # Unlock isteği ekle
    log_islem("ARDUINO_UNLOCK", "Arduino kilidi web'den açılma komutu verildi", yapan="Admin")
    return jsonify({"status": "success", "message": "Unlock komutu tüm Arduino'lara gönderildi"})

# --- ARDUINO DINLEYICI ---
def start_multi_arduino_listener():
    def listen_to_port(port_device):
        global unlock_queue
        print(f" [ARDUINO] Dinleme basladi: {port_device}")
        try:
            with serial.Serial(port_device, 9600, timeout=1) as ser:
                while True:
                    # Unlock komutu kontrolü
                    if unlock_queue:
                        ser.write(b"HATA YOK\n")
                        print(f" [UNLOCK] {port_device} cihazına HATA YOK gönderildi")
                        unlock_queue.pop(0)  # İlk komutu kaldır
                        time.sleep(0.5)
                    
                    # Normal komut okuma
                    line = ser.readline().decode('utf-8').strip()
                    if line:
                        print(f" [ARDUINO-{port_device}] Gelen: {line}")
                        with app.app_context():
                            result = handle_arduino_command(line)
                            ser.write(f"{result}\n".encode('utf-8'))
        except: print(f" [ARDUINO] Baglanti koptu: {port_device}")

    def scanner():
        while True:
            for port in serial.tools.list_ports.comports():
                if any(x in port.description for x in ["Arduino", "CH340", "USB Serial"]):
                    if port.device not in [a.name for a in threading.enumerate()]:
                        threading.Thread(target=listen_to_port, args=(port.device,), name=port.device, daemon=True).start()
            time.sleep(5)
    threading.Thread(target=scanner, daemon=True).start()

def handle_arduino_command(cmd):
    try:
        if ":" in cmd:
            parts = cmd.split(":")
            action = parts[0]
            if action == "REGISTER": return local_register_card(parts[1])
            if action == "LOAD": return local_add_balance(parts[1], 100)
            if action == "GEN_VOUCHER": return local_generate_voucher(float(parts[1]))
            if action == "WITHDRAW": return local_withdraw_balance(parts[1], float(parts[2]))
            if action == "REDEEM_VOUCHER": 
                if len(parts) < 3: return "E:Eksik Veri"
                return local_redeem_voucher(parts[1], parts[2])
        else: return local_complete_transaction(cmd)
    except: return "E:Sistem Hatasi"
    return "E:Gecersiz Komut"

def local_complete_transaction(kart_id):
    global active_transaction
    if active_transaction['status'] != 'pending': return "E:Bekleyen Islem Yok"
    db = db_yukle()
    if kart_id not in db['cards']: return "E:Kart Kayitli Degil"
    uid = db['cards'][kart_id]
    u = db['users'][uid]
    amt = active_transaction['final_amount']
    if active_transaction['type'] == 'load':
        u['balance'] += amt
        log_islem("BAKIYE_YUKLE", f"NFC: {amt} TL", yapan="Arduino")
    else:
        if u['balance'] < amt: return f"E:Yetersiz Bakiye ({int(u['balance'])} TL)"
        u['balance'] -= amt
        u['points'] = u.get('points', 0) + int(amt * 0.1)
        db['reports']['daily_sales'] += amt
        db['reports']['transactions'].append({"time": datetime.now().strftime("%H:%M:%S"), "amount": amt, "cashier": active_transaction['cashier'], "payment": "card", "card_id": kart_id})
        for item in active_transaction.get('cart', []):
            bc = item['barcode']
            if bc in db['products']: db['products'][bc]['stock'] -= item['qty']
        log_islem("SATIS", f"NFC: {amt} TL", yapan="Arduino")
    db_kaydet(db)
    active_transaction['status'] = 'success'
    auth_code = f"{random.randint(1000, 9999)}"
    return f"S:{u['name'].split()[0]}:{int(u['balance'])}:{auth_code}"

def local_register_card(cid):
    db = db_yukle()
    if cid in db['cards']: return "E:Kart Kayitli"
    uid = f"USER_{int(time.time())}"
    db['users'][uid] = {"name": f"Musteri {cid}", "role": "customer", "balance": 500, "points": 0, "tier": "Bronze"}
    db['cards'][cid] = uid
    db_kaydet(db)
    return f"S:Musteri:500"

def local_add_balance(cid, amt):
    db = db_yukle()
    if cid not in db['cards']: return "E:Kart Bulunamadi"
    u = db['users'][db['cards'][cid]]
    u['balance'] += amt
    db_kaydet(db)
    return f"S:{u['name'].split()[0]}:{int(u['balance'])}"

def local_withdraw_balance(cid, amt):
    db = db_yukle()
    if cid not in db['cards']: return "E:Kart Bulunamadi"
    uid = db['cards'][cid]
    u = db['users'][uid]
    
    if u['balance'] < amt: return f"E:Yetersiz Bakiye ({int(u['balance'])} TL)"
    
    u['balance'] -= amt
    log_islem("PARA_CEK", f"Arduino: {amt} TL çekildi - {u['name']}", yapan="Admin")
    db_kaydet(db)
    
    return f"S:{u['name'].split()[0]}:{int(u['balance'])}"

def local_generate_voucher(amt):
    db = db_yukle()
    pin = f"{random.randint(1000, 9999)}"
    while pin in db['vouchers']: pin = f"{random.randint(1000, 9999)}"
    db['vouchers'][pin] = {"amount": amt, "created_at": time.time()}
    db_kaydet(db)
    return f"S:KOD:{pin}"

def local_redeem_voucher(pin, kart_id):
    db = db_yukle()
    if pin not in db['vouchers']: return "E:Gecersiz Kod"
    if kart_id not in db['cards']: return "E:Kart Kayitli Degil"
    
    amount = db['vouchers'][pin]['amount']
    uid = db['cards'][kart_id]
    u = db['users'][uid]
    
    u['balance'] += amount
    del db['vouchers'][pin] # Tek kullanimlik
    
    log_islem("KUPON_YUKLE", f"Pin: {pin}, Tutar: {amount} TL", yapan=u['name'])
    db_kaydet(db)
    auth_code = f"{random.randint(1000, 9999)}"
    return f"S:{u['name'].split()[0]}:{int(u['balance'])}:{auth_code}"

if __name__ == '__main__':
    db_yukle()
    start_multi_arduino_listener()
    app.run(host='0.0.0.0', port=5000, debug=False)