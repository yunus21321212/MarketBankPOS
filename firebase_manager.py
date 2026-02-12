import requests
import json
import time

# --- MOD SEÇİMİ ---
# 'local' -> Bilgisayarın IP'sine bağlanır (İnternet gerekmez, hızlıdır)
# 'firebase' -> Firebase bulutuna bağlanır (İnternet gerekir, her yerden çalışır)
CONNECTION_MODE = 'firebase' 

# --- YEREL AĞ AYARLARI ---
SERVER_IP = "192.168.1.144" 
SERVER_PORT = "5000"

# --- FIREBASE AYARLARI ---
# Gönderdiğin config'e göre oluşturuldu:
FIREBASE_PROJECT_ID = "poetic-harmony-422517-k3"
FIREBASE_URL = f"https://{FIREBASE_PROJECT_ID}-default-rtdb.firebaseio.com"

class FirebaseManager:
    def __init__(self):
        if CONNECTION_MODE == 'local':
            self.base_url = f"http://{SERVER_IP}:{SERVER_PORT}/api"
        else:
            self.base_url = FIREBASE_URL

    def put_transaction(self, amount, status="pending", cashier=None):
        """İşlem durumunu günceller."""
        if CONNECTION_MODE == 'local':
            # Yerel ağ üzerinden Flask server'a bağlanan eski mantık
            if status == "success":
                try:
                    data = {"card_id": "000000", "amount": amount, "cashier_id": "POS_MOBILE"}
                    requests.post(f"{self.base_url}/transaction/complete", json=data)
                    return True
                except: return False
            elif status == "pending":
                try:
                    data = {"amount": amount, "cashier_id": cashier if cashier else "Unknown"}
                    requests.post(f"{self.base_url}/transaction/start", json=data)
                    return True
                except: return False
        else:
            # Firebase Modu: Eski çalışan stabil mantık
            data = {
                "amount": amount,
                "status": status,
                "cashier": cashier,
                "timestamp": time.time()
            }
            try:
                url = f"{self.base_url}/current_transaction.json"
                response = requests.put(url, json=data)
                return response.status_code == 200
            except: return False
        return False

    def get_transaction(self):
        """Mevcut işlemi okur."""
        try:
            if CONNECTION_MODE == 'local':
                url = f"{self.base_url}/transaction/status"
            else:
                url = f"{self.base_url}/current_transaction.json"
            
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def reset_transaction(self):
        return self.put_transaction(0, "idle", None)
