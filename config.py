import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv('BOT_TOKEN')

# Web App
WEBAPP_URL = os.getenv('WEBAPP_URL', 'https://shavkatvic.github.io/securestar/')
WEBAPP_START_PARAM = os.getenv('WEBAPP_START_PARAM', 'uzstar-miniapp')

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///telegrambot.db')

# Payment Providers
PAYME_API_KEY = os.getenv('PAYME_API_KEY')
PAYME_MERCHANT_ID = os.getenv('PAYME_MERCHANT_ID')
CLICK_API_KEY = os.getenv('CLICK_API_KEY')
CLICK_MERCHANT_ID = os.getenv('CLICK_MERCHANT_ID')
UZUM_API_KEY = os.getenv('UZUM_API_KEY')
UZUM_MERCHANT_ID = os.getenv('UZUM_MERCHANT_ID')
ALIF_API_KEY = os.getenv('ALIF_API_KEY')
ALIF_MERCHANT_ID = os.getenv('ALIF_MERCHANT_ID')

# Get these from @BotFather -> /mybots -> [Your Bot] -> Payments
PROVIDER_TOKENS = {
    'payme': os.getenv('PAYME_BOTFATHER_TOKEN'),  # e.g., 38121234:LIVE:12345
    'click': os.getenv('CLICK_BOTFATHER_TOKEN'),
}

# Fragment Settings
# Note: For Stars, you usually provide them via @BotFather or a manual transfer.
# For Gifts, store the URLs of the gifts you've already bought on Fragment.
FRAGMENT_GIFT_STORAGE = "fragment_inventory"  # Name of your table for pre-bought gift links

# Referral Reward (percentage or fixed amount)
REFERRAL_REWARD_PERCENT = 10  # 10% of transaction
REFERRAL_FIXED_REWARD = 5000  # UZS

# Product Prices (in USD, will be converted to UZS)
PRODUCT_PRICES = {
    'stars_50': 1.99,
    'stars_100': 3.99,
    'stars_500': 19.99,
    'premium_monthly': 4.99,
    'premium_yearly': 49.99,
    'gift_small': 2.99,
    'gift_medium': 4.99,
    'gift_large': 9.99,
}

# Uzbek Language Messages
MESSAGES = {
    'welcome': "Xush kelibsiz! Tanlang:",
    'stars': "⭐️ Stars",
    'premium': "💎 Premium",
    'gifts': "🎁 Sovg'alar",
    'wallet': "💳 Hamyon",
    'premium_active': "Sizda faol Premium obunasi mavjud. Muddat tugashini kuting yoki do'stingizga sovg'a qiling!",
    'payment_success': "To'lov muvaffaqiyatli! {product} faollashtirildi. {emoji}",
    'insufficient_balance': "Hamyonda yetarli mablag' yo'q. Iltimos, to'ldiring.",
    'payment_failed': "To'lov amalga oshmadi. Qayta urinib ko'ring yoki boshqa to'lov usulini tanlang.",
    'top_up': "Hamyonni to'ldirish",
    'history': "Tarix",
    'stats': "Statistika",
    'referral_link': "Taklif havolasi",
}