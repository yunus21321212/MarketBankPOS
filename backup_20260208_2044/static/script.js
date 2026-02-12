// --- YAPILANDIRMA ---
const PRODUCTS = [
    { name: "Ekmek", price: 10 },
    { name: "Süt", price: 25 },
    { name: "Yumurta", price: 60 },
    { name: "Çikolata", price: 15 },
    { name: "Su", price: 5 },
    { name: "Kola", price: 30 },
    { name: "Cips", price: 20 },
    { name: "Peynir", price: 120 },
    { name: "Sigara", price: 60 },
    { name: "Poşet", price: 0.50 }
];

let cart = [];
let currentUser = null;

// --- SAYFA YÜKLENDİĞİNDE ---
document.addEventListener("DOMContentLoaded", () => {
    // Eğer Login sayfasındaysak (URL '/')
    if (window.location.pathname === '/') {
        // Login özel işlemleri (yok)
    }
    // Eğer Cashier sayfasındaysak
    else if (window.location.pathname === '/cashier') {
        const storedUser = localStorage.getItem('market_user');
        if (!storedUser) {
            window.location.href = '/'; // Giriş yapılmamışsa at
            return;
        }
        currentUser = JSON.parse(storedUser);
        document.getElementById('cashier-name').innerText = currentUser.name;
        document.getElementById('cashier-role').innerText = currentUser.role;

        renderProducts();
    }
});

// --- LOGIN FONKSİYONLARI ---
async function login() {
    const userId = document.getElementById('user-id').value;
    const msg = document.getElementById('error-msg');

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId })
        });
        const data = await res.json();

        if (data.status === 'success') {
            localStorage.setItem('market_user', JSON.stringify(data));
            window.location.href = '/cashier';
        } else {
            msg.innerText = data.message;
        }
    } catch (e) {
        msg.innerText = "Sunucu Hatası!";
    }
}

function logout() {
    localStorage.removeItem('market_user');
    window.location.href = '/';
}

// --- KASA FONKSİYONLARI ---
function renderProducts() {
    const grid = document.getElementById('product-grid');
    grid.innerHTML = '';
    PRODUCTS.forEach(p => {
        const btn = document.createElement('button');
        btn.className = 'product-btn';
        btn.innerHTML = `
            <strong>${p.name}</strong>
            <span class="price-tag">${p.price} TL</span>
        `;
        btn.onclick = () => addToCart(p);
        grid.appendChild(btn);
    });
}

function addToCart(product) {
    cart.push(product);
    renderCart();
}

function renderCart() {
    const list = document.getElementById('cart-list');
    list.innerHTML = '';
    let total = 0;

    cart.forEach((item, index) => {
        total += item.price;
        const li = document.createElement('li');
        li.innerHTML = `
            <span>${item.name}</span>
            <span>${item.price} TL</span>
        `;
        // Çift tıklayınca silme özelliği eklenebilir
        list.appendChild(li);
    });

    document.getElementById('total-amount').innerText = total.toFixed(2) + " TL";
}

function clearCart() {
    cart = [];
    renderCart();
}

async function startPayment() {
    if (cart.length === 0) return alert("Sepet boş!");

    const total = cart.reduce((sum, item) => sum + item.price, 0);

    // Kasiyer "Ödeme Al" dediğinde POS'u (Android App) tetikliyoruz
    try {
        const res = await fetch('/api/transaction/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                amount: total,
                cashier_id: currentUser.name
            })
        });
        const result = await res.json();

        if (result.status === 'success') {
            // Ödeme POS'a gitti, şimdi sonucunu bekle
            document.getElementById('total-amount').innerText = "POS Bekleniyor...";

            // Polling (Sürekli kontrol) başlat
            const checkInterval = setInterval(async () => {
                try {
                    const statusRes = await fetch('/api/transaction/status');
                    const statusData = await statusRes.json();

                    if (statusData.status === 'success') {
                        clearInterval(checkInterval);
                        alert("✅ Ödeme Başarıyla Alındı!");
                        clearCart();
                        document.getElementById('total-amount').innerText = "0.00 TL"; // Sıfırla
                    } else if (statusData.status === 'failed') {
                        clearInterval(checkInterval);
                        alert("❌ Ödeme Reddedildi!");
                        // Sepeti temizleme, belki tekrar dener
                        const currentTotal = cart.reduce((sum, item) => sum + item.price, 0);
                        document.getElementById('total-amount').innerText = currentTotal.toFixed(2) + " TL";
                    }
                    // 'pending' ise beklemeye devam et
                } catch (e) {
                    console.log("Kontrol hatası: " + e);
                }
            }, 1000); // 1 saniyede bir

        } else {
            alert("Hata: " + result.message);
        }
    } catch (e) {
        alert("Bağlantı Hatası: " + e);
    }
}

// --- MODAL FONKSİYONLARI ---
function showModal(id) {
    document.getElementById(id).style.display = 'block';
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

// Modal dışına tıklayınca kapatma
window.onclick = function (event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = "none";
    }
}

// --- API EKSTRA FONKSİYONLAR ---
async function addBalance() {
    const cardId = document.getElementById('bal-card-id').value;
    const amount = parseFloat(document.getElementById('bal-amount').value);

    if (!cardId || !amount) return alert("Bilgileri doldurun");

    try {
        const res = await fetch('/api/bakiye_ekle', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                card_id: cardId,
                amount: amount,
                cashier_id: currentUser.name
            })
        });
        const result = await res.json();
        alert(result.message || (result.status === 'success' ? 'Yüklendi! Yeni Bakiye: ' + result.new_balance : 'Hata'));
        if (result.status === 'success') closeModal('balance-modal');
    } catch (e) {
        alert("Hata: " + e);
    }
}

async function registerCard() {
    const cardId = document.getElementById('new-card-id').value;
    const name = document.getElementById('new-customer-name').value;
    const balance = parseFloat(document.getElementById('new-initial-bal').value);

    if (!cardId || !name) return alert("Eksik bilgi!");

    try {
        const res = await fetch('/api/kart_tanit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                card_id: cardId,
                name: name,
                initial_balance: balance,
                cashier_id: currentUser.name
            })
        });
        const result = await res.json();
        alert(result.message);
        if (result.status === 'success') closeModal('card-modal');
    } catch (e) {
        alert("Hata: " + e);
    }
}
