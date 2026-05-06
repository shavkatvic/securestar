const tg = window.Telegram?.WebApp;
if (tg) {
  tg.expand();
  tg.ready();
}

const products = {
  stars: [
    { key: 'stars_50', label: '50 ⭐️', price: '1.99 USD' },
    { key: 'stars_100', label: '100 ⭐️', price: '3.99 USD' },
    { key: 'stars_500', label: '500 ⭐️', price: '19.99 USD' }
  ],
  premium: [
    { key: 'premium_monthly', label: 'Oylik Premium', price: '4.99 USD' },
    { key: 'premium_yearly', label: 'Yillik Premium', price: '49.99 USD' }
  ],
  gifts: [
    { key: 'gift_small', label: 'Kichik Sovgʻa', price: '2.99 USD' },
    { key: 'gift_medium', label: 'Oʻrtacha Sovgʻa', price: '4.99 USD' },
    { key: 'gift_large', label: 'Katta Sovgʻa', price: '9.99 USD' }
  ]
};

function showSection(section) {
  const content = document.getElementById('content');
  let html = '';

  if (section === 'wallet') {
    html += '<div class="card"><h2>Hamyon</h2>';
    html += '<div class="product"><span>10,000 UZS</span><button onclick="sendTopup(10000, \"payme\")">Payme</button></div>';
    html += '<div class="product"><span>25,000 UZS</span><button onclick="sendTopup(25000, \"payme\")">Payme</button></div>';
    html += '<div class="product"><span>50,000 UZS</span><button onclick="sendTopup(50000, \"payme\")">Payme</button></div>';
    html += '<p>Uzum yoki Alif uchun botga murojaat qiling.</p>';
    html += '</div>';
  } else {
    html += `<div class="card"><h2>${section === 'stars' ? 'Stars' : section === 'premium' ? 'Premium' : 'Sovgʻalar'}</h2>`;
    products[section].forEach(item => {
      html += `<div class="product"><span>${item.label} - ${item.price}</span><button onclick="showMethods('${item.key}')">Tanlash</button></div>`;
    });
    html += '</div>';
  }

  content.innerHTML = html;
}

function showMethods(productKey) {
  const content = document.getElementById('content');
  const title = productKey.replace('_', ' ').toUpperCase();
  let html = `<div class="card"><h2>${title}</h2><p>To'lov usulini tanlang:</p>`;
  html += `<button onclick="sendPurchase('${productKey}', 'payme')">Payme</button>`;
  html += `<button class="secondary" onclick="sendPurchase('${productKey}', 'click')">Click</button>`;
  html += `<button class="secondary" onclick="sendPurchase('${productKey}', 'uzum')">Uzum</button>`;
  html += `<button class="secondary" onclick="sendPurchase('${productKey}', 'alif')">Alif</button>`;
  html += `<button class="secondary" onclick="sendPurchase('${productKey}', 'wallet')">Hamyondan</button>`;
  html += `<button class="small" onclick="showSection('${productKey.split('_')[0]}')">🔙 Orqaga</button>`;
  html += '</div>';
  content.innerHTML = html;
}

function sendPurchase(product, method) {
  const payload = { action: 'purchase', product, method };
  if (tg) {
    tg.sendData(JSON.stringify(payload));
    tg.close();
  } else {
    alert('Mini app Telegram ichida ishlaydi.');
  }
}

function sendTopup(amount, method) {
  const payload = { action: 'topup', amount, method };
  if (tg) {
    tg.sendData(JSON.stringify(payload));
    tg.close();
  } else {
    alert('Mini app Telegram ichida ishlaydi.');
  }
}
