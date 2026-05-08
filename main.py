import logging
import datetime
import uuid
import json
from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup, 
    LabeledPrice, 
    WebAppInfo, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    ContextTypes, 
    PreCheckoutQueryHandler, 
    MessageHandler, 
    filters
)

# Domain Specific Imports
from database import get_db, User, Transaction, FragmentInventory
from payments import wallet_payment, usd_to_uzs
from config import BOT_TOKEN, PRODUCT_PRICES, MESSAGES, PROVIDER_TOKENS, WEBAPP_URL

# Logging Setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants as per user requirements
STAR_RATE_UZS = 199.99  # 100 Stars = 19,999 UZS
STAR_PACKAGES_UZS = {
    'stars_50': 9999,
    'stars_100': 19999,
    'stars_150': 29999,
    'stars_250': 49999,
    'stars_350': 69999,
    'stars_500': 99999,
    'stars_750': 149999,
    'stars_1000': 199999,
    'stars_1500': 299999,
    'stars_2500': 499999,
    'stars_5000': 999999,
    'stars_10000': 1999999,
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entry point for StarUzb. 
    Eliminates redundant inline menus to prevent 'Double Menu' bug.
    """
    user = update.effective_user
    db = get_db()
    
    # Check/Create User
    db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()
    if not db_user:
        referral_code = str(uuid.uuid4())[:8]
        # Check if started with a referral link
        referred_by = None
        if context.args:
            referred_by = context.args[0] # Assuming args[0] is the referrer's code

        db_user = User(
            telegram_id=str(user.id),
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referral_code=referral_code,
            referred_by=referred_by,
            wallet_balance=0,
            star_balance=0
        )
        db.add(db_user)
        db.commit()

    # Determine Language
    lang = user.language_code if user.language_code in ['ru', 'uz'] else 'en'
    welcome_text = MESSAGES.get(lang, MESSAGES['en'])['welcome'].format(name=user.first_name)

    # Clean UI: Only One Big Button to launch the StarUzb Experience
    # This prevents the 'Two Menu' issue by keeping the chat interface empty.
    keyboard = [
        [KeyboardButton(text="🚀 StarUzb Store", web_app=WebAppInfo(url=WEBAPP_URL))]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"<b>Welcome to StarUzb, {user.first_name}!</b>\n\n"
        f"{welcome_text}\n\n"
        "🛡 <i>Safe, Fast, and Professional Telegram Services.</i>",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )
    db.close()

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles data sent back from the Mini App.
    This is where the 'Backend' logic for the purchase flow lives.
    """
    data_text = update.message.web_app_data.data
    try:
        payload = json.loads(data_text)
    except json.JSONDecodeError:
        return

    user_id = str(update.message.from_user.id)
    db = get_db()
    action = payload.get('action')

    if action == 'purchase':
        product_key = payload.get('product') # e.g., 'stars_100' or 'premium_12'
        method = payload.get('method')       # 'payme', 'click', or 'wallet'
        target_user = payload.get('target', 'myself')
        recipient_username = payload.get('recipient_username', '')

        # Calculate Price
        if product_key.startswith('stars'):
            price_uzs = STAR_PACKAGES_UZS.get(product_key, 0)
            if product_key == 'stars_custom':
                count = int(payload.get('count', 0))
                price_uzs = count * (19999/100) # Maintain the 100=19,999 ratio
            product_name = f"Telegram {product_key.replace('_', ' ').title()}"
        else:
            # Premium Pricing
            price_usd = PRODUCT_PRICES.get(product_key, 0)
            price_uzs = usd_to_uzs(price_usd)
            product_name = f"Telegram {product_key.replace('_', ' ').title()}"

        # 1. Handle Wallet Payment
        if method == 'wallet':
            if wallet_payment(user_id, price_uzs, db):
                await process_purchase(user_id, product_key, product_name, price_uzs, 'wallet', db, context, update.message.chat_id)
            else:
                await update.message.reply_text("❌ Balansingiz yetarli emas.")
        
        # 2. Handle Native Invoices (Payme/Click via Bot API)
        elif method in ['payme', 'click']:
            provider_token = PROVIDER_TOKENS.get(method)
            if provider_token:
                await context.bot.send_invoice(
                    chat_id=update.message.chat_id,
                    title=f"StarUzb | {product_name}",
                    description=f"Purchase for {recipient_username if target_user == 'friend' else 'Yourself'}",
                    payload=f"SUB_{product_key}_{user_id}",
                    provider_token=provider_token,
                    currency="UZS",
                    prices=[LabeledPrice("To'lov", int(price_uzs * 100))],
                    start_parameter="staruzb-purchase"
                )

    db.close()

async def process_purchase(user_id, product_key, product_name, price_uzs, method, db, context, chat_id):
    """
    Finalizes the transaction in the database and notifies the user.
    """
    user = db.query(User).filter(User.telegram_id == user_id).first()
    
    # Create Success Transaction
    new_tx = Transaction(
        user_id=user.id,
        product_type=product_key,
        amount_uzs=price_uzs,
        payment_method=method,
        status='success',
        created_at=datetime.datetime.utcnow()
    )
    db.add(new_tx)

    # Logic for Stars/Premium Assignment
    if "stars" in product_key:
        # If it's a direct star top-up for the user
        star_count = int(product_key.split('_')[1]) if '_' in product_key else 0
        user.star_balance += star_count
    
    # Logic for Referrer Bonus (5 Stars)
    if user.referred_by:
        referrer = db.query(User).filter(User.referral_code == user.referred_by).first()
        if referrer:
            referrer.star_balance += 5
            # Optional: Notify referrer

    db.commit()
    await context.bot.send_message(chat_id, f"✅ <b>{product_name}</b> xaridi muvaffaqiyatli yakunlandi!", parse_mode="HTML")

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Telegram requires an answer within 10 seconds of a user clicking 'Pay'."""
    query = update.pre_checkout_query
    # Here you would check stock/inventory if needed
    await query.answer(ok=True)

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered after a successful Telegram Invoice payment."""
    payment = update.message.successful_payment
    payload = payment.invoice_payload # SUB_stars_100_USERID
    parts = payload.split('_')
    
    product_key = f"{parts[1]}_{parts[2]}"
    user_id = parts[3]
    price_uzs = payment.total_amount / 100

    db = get_db()
    await process_purchase(user_id, product_key, product_key, price_uzs, 'invoice', db, context, update.message.chat_id)
    db.close()

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    print("StarUzb Bot is Running...")
    application.run_polling()

if __name__ == '__main__':
    main()
