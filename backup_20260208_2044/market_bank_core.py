import json
import os
import time

import logging

from datetime import datetime

from flask import Flask, request, jsonify, render_template


# --- AYARLAR ---

DB_FILE = "market_bank_db.json"
LOG_FILE = "transaction_log.txt"

# Statik ve Template yollarını tam yol olarak belirle (Çalıştırma konumundan bağımsız olması için)
base_dir = os.path.abspath(os.path.dirname(__file__))
static_dir = os.path.join(base_dir, 'static')
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, static_folder=static_dir, template_folder=template_dir)

# --- WEB DASHBOARD ROUTES ---

@app.route('/')
def index():
    """Serve the Premium Web Dashboard"""
    return render_template('index.html')

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    """Top Community Spenders by Points"""
    db = db_yukle()
    all_users = db.get('users', {})
    # Filter customers and sort by points
    sorted_users = sorted(
        [{"name": u['name'], "points": u.get('points', 0), "tier": u.get('tier', 'Bronze')} 
         for u in all_users.values() if u.get('role') == 'customer'],
        key=lambda x: x['points'], reverse=True
    )
    return jsonify(sorted_users[:10])


# --- VERİTABANI YÖNETİMİ ---

def db_yukle():

    if not os.path.exists(DB_FILE):

        # Varsayılan Veritabani

        varsayilan_db = {
            "users": {
                "ADMIN_U": {"name": "Süper Admin", "role": "admin", "balance": 999999, "limit": 999999, "points": 0, "tier": "Platinum"},
                "WORKER_1": {"name": "Kasiyer Ahmet", "role": "worker", "balance": 0, "limit": 0, "points": 0, "tier": "Bronze"}
            },
            "cards": {
                "000000": "ADMIN_U"
            },
            "products": {
                "8690504000018": {"name": "Ekmek", "price": 10.0, "stock": 100},
                "8690504000025": {"name": "Süt", "price": 25.0, "stock": 50},
                "8690504000032": {"name": "Yumurta (30lu)", "price": 120.0, "stock": 20}
            },
            "reports": {
                "daily_sales": 0.0,
                "monthly_sales": 0.0,
                "transactions": []
            },
            "community": {
                "leaderboard": [] # Top spenders/points earners
            }
        }

        with open(DB_FILE, 'w', encoding='utf-8') as f:

            json.dump(varsayilan_db, f, ensure_ascii=False, indent=4)

        return varsayilan_db
    

    with open(DB_FILE, 'r', encoding='utf-8') as f:

        return json.load(f)


def db_kaydet(db):

    with open(DB_FILE, 'w', encoding='utf-8') as f:

        json.dump(db, f, ensure_ascii=False, indent=4)


def log_islem(islem_tipi, detay, yapan="Sistem"):

    zaman = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log_mesaji = f"[{zaman}] [{islem_tipi}] {yapan}: {detay}\n"

    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_mesaji)
    
    # Konsola da bas (Kullanıcının terminalde görmesi için)
    print(f" >>> {log_mesaji.strip()}")


# (Eski GUI Template'leri - Varsa Kullanılabilir)
# @app.route('/login_page')
# def index_page():
#     return render_template('login.html')

# @app.route('/cashier')
# def cashier_page():
#     return render_template('cashier.html')


# --- API ENDPOINTS ---


@app.route('/api/login', methods=['POST'])

def login():

    """Kasiyer/Admin Girişi"""

    data = request.json

    user_id = data.get('user_id')

    db = db_yukle()

    if user_id in db['users']:
        user = db['users'][user_id]
        print(f" [LOGIN] {user['name']} ({user['role']}) giriş yaptı.")
        log_islem("GIRIS", f"{user['name']} sisteme giriş yaptı.", yapan=user['name'])
        return jsonify({"status": "success", "role": user['role'], "name": user['name']})

    return jsonify({"status": "error", "message": "Kullanıcı bulunamadı"}), 401


@app.route('/api/odeme', methods=['POST'])

def odeme_al():

    """Satış İşlemi (Karttan Bakiye Düşer)"""

    data = request.json

    kart_id = data.get('card_id')

    tutar = data.get('amount')

    kasiyer = data.get('cashier_id', 'Bilinmeyen')


    db = db_yukle()
    

    if kart_id not in db['cards']:

        return jsonify({"status": "error", "message": "KART TANIMSIZ"}), 404
    

    user_id = db['cards'][kart_id]

    user = db['users'][user_id]


    if user['balance'] >= tutar:

        user['balance'] -= tutar

        db_kaydet(db)

        log_islem("SATIS", f"{tutar} TL harcama yapıldı. Kart: {kart_id}", yapan=kasiyer)

        return jsonify({"status": "success", "new_balance": user['balance'], "message": "ÖDEME ONAYLANDI"})
    else:

        log_islem("RED", f"Yetersiz Bakiye ({user['balance']} < {tutar}). Kart: {kart_id}", yapan=kasiyer)

        return jsonify({"status": "error", "message": "YETERSİZ BAKİYE"}), 402


@app.route('/api/bakiye_ekle', methods=['POST'])

def bakiye_ekle():

    """Bakie Yükleme"""

    data = request.json

    kart_id = data.get('card_id')

    tutar = data.get('amount')

    kasiyer = data.get('cashier_id')


    # Güvenlik Limiti (Çalışan için)

    if tutar > 500: 
        pass


    db = db_yukle()

    if kart_id not in db['cards']:

        return jsonify({"status": "error", "message": "Kart Bulunamadı"}), 404


    user_id = db['cards'][kart_id]

    db['users'][user_id]['balance'] += tutar

    db_kaydet(db)
    

    log_islem("BAKIYE_EKLEME", f"{tutar} TL yüklendi. Kart: {kart_id}", yapan=kasiyer)

    return jsonify({"status": "success", "new_balance": db['users'][user_id]['balance']})


@app.route('/api/kart_tanit', methods=['POST'])

def kart_tanit():

    """Yeni Müşteri Kartı Tanımlama"""

    data = request.json

    kart_id = data.get('card_id')

    isim = data.get('name')

    bakiye = data.get('balance', 0) # 'initial_balance' yerine 'balance' kullanıldı

    kasiyer = data.get('cashier_id', 'Sistem') # Varsayılan kasiyer eklendi

    tier = data.get('tier', 'Bronze') # Yeni: Özel Kart Seviyesi
    

    db = db_yukle()

    if kart_id in db['cards']:

        return jsonify({"status": "error", "message": "BU KART ZATEN KAYITLI"}), 400 # Hata mesajı güncellendi
    

    new_user_id = f"USER_{int(time.time())}" # Benzersiz ID için time.time() kullanıldı
    

    db['users'][new_user_id] = {
        "name": isim,
        "role": "customer",

        "balance": bakiye,

        "limit": 0, # Yeni kartlar için limit 0 olarak ayarlandı
        "points": 0, # Yeni: Puan sistemi
        "tier": tier # Yeni: Kart seviyesi
    }

    db['cards'][kart_id] = new_user_id

    db_kaydet(db)
    

    log_islem("KART_TANITMA", f"Yeni Müşteri: {isim} ({new_user_id})", yapan=kasiyer)

    return jsonify({"status": "success", "message": "Kart Başarıyla Tanımlandı"})

# --- KULLANICI YÖNETİMİ ---

@app.route('/api/kullanicilar', methods=['GET'])
def kullanici_liste():
    db = db_yukle()
    return jsonify(db['users'])

@app.route('/api/kullanici_ekle', methods=['POST'])
def kullanici_ekle():
    data = request.json
    user_id = data.get('user_id')
    name = data.get('name')
    role = data.get('role', 'worker')
    
    db = db_yukle()
    db['users'][user_id] = {"name": name, "role": role, "balance": 0, "limit": 0}
    db_kaydet(db)
    return jsonify({"status": "success"})

# --- ÜRÜN YÖNETİMİ (ADMİN) ---

@app.route('/api/urunler', methods=['GET'])
def urunleri_getir():
    db = db_yukle()
    return jsonify(db.get('products', {}))

@app.route('/api/urun_ekle', methods=['POST'])
def urun_ekle():
    data = request.json
    barcode = data.get('barcode')
    name = data.get('name')
    price = data.get('price')
    stock = data.get('stock', 0)
    
    db = db_yukle()
    db['products'][barcode] = {"name": name, "price": price, "stock": stock}
    db_kaydet(db)
    log_islem("URUN_EKLE", f"Ürün eklendi: {name} ({barcode})")
    return jsonify({"status": "success"})

@app.route('/api/urun_sil', methods=['POST'])
def urun_sil():
    barcode = request.json.get('barcode')
    db = db_yukle()
    if barcode in db['products']:
        del db['products'][barcode]
        db_kaydet(db)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Ürün bulunamadı"})

# --- RAPORLAMA ---

@app.route('/api/rapor/gunluk', methods=['GET'])
def rapor_gunluk():
    db = db_yukle()
    customers = [u for u in db['users'].values() if u.get('role') == 'customer']
    return jsonify({
        "total_sales": db['reports'].get('daily_sales', 0),
        "transaction_count": len(db['reports'].get('transactions', [])),
        "customer_count": len(customers)
    })


# --- POS SENKRONİZASYON (KASA <-> ANDROID) ---

active_transaction = {"amount": 0.0, "status": "idle", "cashier": None}


@app.route('/api/transaction/start', methods=['POST'])

def baslat_islem():

    """Kasa: Ödeme Bekliyor"""

    global active_transaction

    data = request.json

    tutar = data.get('amount')

    kasiyer = data.get('cashier_id')
    

    active_transaction = {"amount": tutar, "status": "pending", "cashier": kasiyer}

    return jsonify({"status": "success", "message": "POS bekleniyor..."})


@app.route('/api/transaction/status', methods=['GET'])

def islem_durumu():

    """POS: Ödeme Var mı?"""

    return jsonify(active_transaction)


@app.route('/api/transaction/reset', methods=['POST'])
def reset_islem():
    """Manuel Reset"""
    global active_transaction
    active_transaction = {"amount": 0.0, "status": "idle", "cashier": None}
    return jsonify({"status": "success", "message": "İşlem sıfırlandı."})


@app.route('/api/transaction/complete', methods=['POST'])

def tamamla_islem():

    """POS: Kart Okutuldu ve Ödeme Yapılıyor"""

    global active_transaction

    data = request.json

    kart_id = data.get('card_id')
    

    if active_transaction['status'] != 'pending':

        return jsonify({"status": "error", "message": "Aktif ödeme yok!"}), 400


    tutar = active_transaction['amount']
    

    db = db_yukle()

    if kart_id not in db['cards']:

        return jsonify({"status": "error", "message": "KART TANIMSIZ"}), 404
    

    user_id = db['cards'][kart_id]

    user = db['users'][user_id]


    if user['balance'] >= tutar:

        user['balance'] -= tutar

        # Puan Kazanımı (Harcama başına %10 puan)
        kazanilan_puan = int(tutar * 0.1)
        user['points'] += kazanilan_puan

        # Seviye Atlama Kontrolü (Örn: 1000 puanda Gold)
        if user['points'] > 1000: user['tier'] = "Gold"
        elif user['points'] > 500: user['tier'] = "Silver"

        # Raporları Güncelle
        db['reports']['daily_sales'] += tutar
        db['reports']['transactions'].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "amount": tutar,
            "cashier": active_transaction['cashier'],
            "card_id": kart_id,
            "points_earned": kazanilan_puan
        })

        db_kaydet(db)

        log_islem("SATIS", f"{tutar} TL harcama yapıldı. Kart: {kart_id}", yapan=active_transaction['cashier'])
        

        active_transaction = {"amount": 0.0, "status": "success", "cashier": None}

        return jsonify({"status": "success", "new_balance": user['balance'], "message": "ÖDEME ONAYLANDI"})
    else:

        log_islem("RED", f"Yetersiz Bakiye ({user['balance']} < {tutar}). Kart: {kart_id}", yapan=active_transaction['cashier'])

        active_transaction = {"amount": 0.0, "status": "failed", "cashier": None}
        jls_extract_var = jsonify({"status": "error", "message": "YETERSİZ BAKİYE"}), 402
        return jls_extract_var


if __name__ == '__main__':

    print("MarketBank Sunucusu Başlatılıyor...")

    db_yukle()
    

    # HTTPS Ayarları

    # 'adhoc' sertifikası kullanarak HTTPS başlatmayı dene.

    # Eğer 'pyopenssl' yoksa hata verebilir, bu durumda sadece HTTP çalışsın.
    try:

        print("HTTPS Sunucusu Başlatılıyor (adhoc sertifika)...")

        app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')

    except Exception as e:

        print(f"HTTPS BAŞLATILAMADI: {e}")

        print("HTTP modunda başlatılıyor. (pip install pyopenssl ile HTTPS deneyin)")

        app.run(host='0.0.0.0', port=5000, debug=True)

