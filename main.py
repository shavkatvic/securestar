import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters
from database import get_db, User, Transaction, Gift, FragmentInventory
from payments import create_payment, wallet_payment, usd_to_uzs, providers
from config import BOT_TOKEN, PRODUCT_PRICES, MESSAGES, PROVIDER_TOKENS, WEBAPP_URL
import uuid
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STAR_RATE_UZS = 200
STAR_PACKAGES_UZS = {
    'stars_100': 20000,
    'stars_150': 30000,
    'stars_250': 50000,
    'stars_350': 70000,
    'stars_500': 100000,
    'stars_750': 150000,
    'stars_1000': 200000,
    'stars_1500': 300000,
    'stars_2500': 500000,
    'stars_5000': 1000000,
    'stars_10000': 2000000,
}

def get_star_price(product_key, custom_count=None):
    if product_key == 'stars_custom':
        return max(custom_count or 0, 50) * STAR_RATE_UZS
    return STAR_PACKAGES_UZS.get(product_key, 0)


def format_star_name(product_key, custom_count=None):
    if product_key == 'stars_custom':
        return f"{custom_count} Stars"
    return product_key.replace('_', ' ').title()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = get_db()
    db_user = db.query(User).filter(User.telegram_id == str(user.id)).first()
    if not db_user:
        referral_code = str(uuid.uuid4())[:8]
        db_user = User(
            telegram_id=str(user.id),
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referral_code=referral_code
        )
        db.add(db_user)
        db.commit()

    keyboard = [
        [InlineKeyboardButton("🛍 Mini App", web_app=WebAppInfo(WEBAPP_URL))],
        [InlineKeyboardButton(MESSAGES['stars'], callback_data='stars')],
        [InlineKeyboardButton(MESSAGES['premium'], callback_data='premium')],
        [InlineKeyboardButton(MESSAGES['gifts'], callback_data='gifts')],
        [InlineKeyboardButton(MESSAGES['wallet'], callback_data='wallet')],
        [InlineKeyboardButton(MESSAGES['history'], callback_data='history')],
        [InlineKeyboardButton(MESSAGES['stats'], callback_data='stats')],
        [InlineKeyboardButton(MESSAGES['referral_link'], callback_data='referral')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(MESSAGES['welcome'], reply_markup=reply_markup)
    db.close()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = str(query.from_user.id)
    db = get_db()

    if data == 'stars':
        keyboard = [
            [InlineKeyboardButton("100 ⭐️ - 20,000 UZS", callback_data='buy_stars_100')],
            [InlineKeyboardButton("150 ⭐️ - 30,000 UZS", callback_data='buy_stars_150')],
            [InlineKeyboardButton("250 ⭐️ - 50,000 UZS", callback_data='buy_stars_250')],
            [InlineKeyboardButton("350 ⭐️ - 70,000 UZS", callback_data='buy_stars_350')],
            [InlineKeyboardButton("500 ⭐️ - 100,000 UZS", callback_data='buy_stars_500')],
            [InlineKeyboardButton("750 ⭐️ - 150,000 UZS", callback_data='buy_stars_750')],
            [InlineKeyboardButton("1000 ⭐️ - 200,000 UZS", callback_data='buy_stars_1000')],
            [InlineKeyboardButton("1500 ⭐️ - 300,000 UZS", callback_data='buy_stars_1500')],
            [InlineKeyboardButton("2500 ⭐️ - 500,000 UZS", callback_data='buy_stars_2500')],
            [InlineKeyboardButton("5000 ⭐️ - 1,000,000 UZS", callback_data='buy_stars_5000')],
            [InlineKeyboardButton("10000 ⭐️ - 2,000,000 UZS", callback_data='buy_stars_10000')],
            [InlineKeyboardButton("⭐️ Maxsus buyurtma", callback_data='buy_stars_custom')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Stars tanlang:", reply_markup=reply_markup)

    elif data.startswith('buy_stars_'):
        count = data.split('_')[2]
        if count == 'custom':
            await query.edit_message_text("Iltimos, kamida 50 Stars miqdorini yozing.")
            db.close()
            return
        price_uzs = STAR_PACKAGES_UZS.get(f'stars_{count}', 0)
        keyboard = [
            [InlineKeyboardButton("Payme", callback_data=f'pay_payme_stars_{count}')],
            [InlineKeyboardButton("Click", callback_data=f'pay_click_stars_{count}')],
            [InlineKeyboardButton("Uzum", callback_data=f'pay_uzum_stars_{count}')],
            [InlineKeyboardButton("Alif", callback_data=f'pay_alif_stars_{count}')],
            [InlineKeyboardButton("Hamyondan", callback_data=f'pay_wallet_stars_{count}')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='stars')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"{count} Stars - {price_uzs:.0f} UZS\nTo'lov usulini tanlang:", reply_markup=reply_markup)

    elif data.startswith('pay_'):
        parts = data.split('_')
        method = parts[1]
        product = parts[2]
        count_or_period = parts[3] if len(parts) > 3 else ''
        product_key = f"{product}_{count_or_period}" if count_or_period else product

        if product == 'topup':
            price_uzs = int(count_or_period)
            price_usd = 0
        elif product == 'stars':
            price_uzs = STAR_PACKAGES_UZS.get(product_key, 0)
            price_usd = 0
        else:
            price_usd = PRODUCT_PRICES.get(product_key, 0)
            price_uzs = usd_to_uzs(price_usd)

        if method == 'wallet':
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if wallet_payment(user_id, price_uzs, db):
                product_name = f"{count_or_period} {product}" if count_or_period else product
                await process_purchase(user_id, product_key, product_name, price_usd, price_uzs, 'wallet', db, context, query.message.chat_id)
                emoji = "⭐️" if "stars" in product_key else "💎" if "premium" in product_key else "🎁"
                await query.edit_message_text(MESSAGES['payment_success'].format(product=product_name, emoji=emoji))
            else:
                await query.edit_message_text(MESSAGES['insufficient_balance'])
        elif method in ['payme', 'click'] and method in PROVIDER_TOKENS and PROVIDER_TOKENS[method]:
            product_title = f"Telegram {product_key.replace('_', ' ').title()}"
            await context.bot.send_invoice(
                chat_id=query.message.chat_id,
                title=product_title,
                description="Xaridni tasdiqlash uchun tugmani bosing.",
                payload=f"PAYMENT_{product_key}_{user_id}",
                provider_token=PROVIDER_TOKENS[method],
                currency="UZS",
                prices=[LabeledPrice("Narxi", int(price_uzs * 100))],
                start_parameter="bot-purchase-process"
            )
        else:
            product_name = f"{count_or_period} {product}" if count_or_period else product
            link, transaction_id = create_payment(user_id, product, product_name, price_usd, method, db)
            keyboard = [[InlineKeyboardButton("To'lovni amalga oshirish", url=link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(f"To'lov uchun {method.upper()} ilovasiga o'ting:", reply_markup=reply_markup)

    elif data == 'premium':
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user.active_premium:
            await query.edit_message_text(MESSAGES['premium_active'])
            return

        keyboard = [
            [InlineKeyboardButton("Oylik - $4.99", callback_data='buy_premium_monthly')],
            [InlineKeyboardButton("Yillik - $49.99", callback_data='buy_premium_yearly')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Premium tanlang:", reply_markup=reply_markup)

    elif data.startswith('buy_premium_'):
        period = data.split('_')[2]
        price_usd = PRODUCT_PRICES[f'premium_{period}']
        price_uzs = usd_to_uzs(price_usd)
        keyboard = [
            [InlineKeyboardButton("Payme", callback_data=f'pay_payme_premium_{period}')],
            [InlineKeyboardButton("Click", callback_data=f'pay_click_premium_{period}')],
            [InlineKeyboardButton("Uzum", callback_data=f'pay_uzum_premium_{period}')],
            [InlineKeyboardButton("Alif", callback_data=f'pay_alif_premium_{period}')],
            [InlineKeyboardButton("Hamyondan", callback_data=f'pay_wallet_premium_{period}')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='premium')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Premium {period} - {price_uzs:.0f} UZS\nTo'lov usulini tanlang:", reply_markup=reply_markup)

    elif data == 'gifts':
        keyboard = [
            [InlineKeyboardButton("Kichik - $2.99", callback_data='buy_gift_small')],
            [InlineKeyboardButton("O'rtacha - $4.99", callback_data='buy_gift_medium')],
            [InlineKeyboardButton("Katta - $9.99", callback_data='buy_gift_large')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Sovg'a tanlang:", reply_markup=reply_markup)

    elif data.startswith('buy_gift_'):
        size = data.split('_')[2]
        price_usd = PRODUCT_PRICES[f'gift_{size}']
        price_uzs = usd_to_uzs(price_usd)
        keyboard = [
            [InlineKeyboardButton("Payme", callback_data=f'pay_payme_gift_{size}')],
            [InlineKeyboardButton("Click", callback_data=f'pay_click_gift_{size}')],
            [InlineKeyboardButton("Uzum", callback_data=f'pay_uzum_gift_{size}')],
            [InlineKeyboardButton("Alif", callback_data=f'pay_alif_gift_{size}')],
            [InlineKeyboardButton("Hamyondan", callback_data=f'pay_wallet_gift_{size}')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='gifts')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"Sovg'a {size} - {price_uzs:.0f} UZS\nTo'lov usulini tanlang:", reply_markup=reply_markup)

    elif data == 'wallet':
        user = db.query(User).filter(User.telegram_id == user_id).first()
        star_balance = getattr(user, 'star_balance', 0)
        keyboard = [
            [InlineKeyboardButton("To'ldirish", callback_data='topup')],
            [InlineKeyboardButton(f"Balans: {user.wallet_balance:.0f} UZS", callback_data='balance')],
            [InlineKeyboardButton(f"⭐️ Star balansi: {star_balance}", callback_data='balance')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='back')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Hamyon:", reply_markup=reply_markup)

    elif data == 'topup':
        keyboard = [
            [InlineKeyboardButton("10,000 UZS", callback_data='topup_10000')],
            [InlineKeyboardButton("25,000 UZS", callback_data='topup_25000')],
            [InlineKeyboardButton("50,000 UZS", callback_data='topup_50000')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='wallet')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Qancha to'ldirmoqchisiz:", reply_markup=reply_markup)

    elif data.startswith('topup_'):
        amount = int(data.split('_')[1])
        keyboard = [
            [InlineKeyboardButton("Payme", callback_data=f'pay_payme_topup_{amount}')],
            [InlineKeyboardButton("Click", callback_data=f'pay_click_topup_{amount}')],
            [InlineKeyboardButton("Uzum", callback_data=f'pay_uzum_topup_{amount}')],
            [InlineKeyboardButton("Alif", callback_data=f'pay_alif_topup_{amount}')],
            [InlineKeyboardButton("🔙 Orqaga", callback_data='topup')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(f"{amount} UZS to'ldirish\nTo'lov usulini tanlang:", reply_markup=reply_markup)

    elif data == 'history':
        transactions = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.created_at.desc()).limit(10).all()
        text = "Oxirgi tranzaksiyalar:\n"
        for t in transactions:
            text += f"{t.created_at.strftime('%d.%m.%Y')} | {t.product_type} | {t.amount_uzs:.0f} UZS | {t.status}\n"
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif data == 'stats':
        user = db.query(User).filter(User.telegram_id == user_id).first()
        total_deposits = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.product_type == 'topup', Transaction.status == 'success').with_entities(Transaction.amount_uzs).all()
        total_expenses = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.product_type != 'topup', Transaction.status == 'success').with_entities(Transaction.amount_uzs).all()
        deposits = sum(t[0] for t in total_deposits)
        expenses = sum(t[0] for t in total_expenses)
        star_balance = getattr(user, 'star_balance', 0)
        text = f"Star balansi: {star_balance} ⭐\nJami depozitlar: {deposits:.0f} UZS\nJami xarajatlar: {expenses:.0f} UZS\nTaklif qilganlar: {user.referral_count}"
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif data == 'referral':
        user = db.query(User).filter(User.telegram_id == user_id).first()
        link = f"https://t.me/{context.bot.username}?start={user.referral_code}"
        text = f"Sizning taklif havolangiz:\n{link}\n\nHar bir muvaffaqiyatli xariddan keyin referrerga 5 Stars bonus beriladi."
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup)

    elif data == 'back':
        await start(update, context)

    db.close()

async def process_purchase(user_id, product_key, product_name, price_usd, price_uzs, payment_method, db, context, chat_id):
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if not user:
        return

    transaction = db.query(Transaction).filter(
        Transaction.user_id == user.id,
        Transaction.product_type == product_key.split('_')[0],
        Transaction.status == 'pending'
    ).order_by(Transaction.created_at.desc()).first()

    if transaction is None:
        transaction = Transaction(
            user_id=user.id,
            product_type=product_key,
            product_details=product_name,
            amount_usd=0,
            amount_uzs=price_uzs,
            payment_method=payment_method,
            status='success'
        )
        db.add(transaction)
    else:
        transaction.status = 'success'

    if product_key.startswith('topup'):
        user.wallet_balance += price_uzs
        db.commit()
        return

    if any(tag in product_key for tag in ['stars', 'gift', 'premium']):
        item = db.query(FragmentInventory).filter(
            FragmentInventory.product_type == product_key,
            FragmentInventory.is_sold == False
        ).first()

        if item:
            item.is_sold = True
            if 'premium' in product_key:
                user.active_premium = True
                if 'monthly' in product_key:
                    user.premium_expiry = datetime.datetime.utcnow() + datetime.timedelta(days=30)
                else:
                    user.premium_expiry = datetime.datetime.utcnow() + datetime.timedelta(days=365)

            if context and chat_id:
                await context.bot.send_message(
                    chat_id,
                    f"✅ Xarid muvaffaqiyatli!\n\nSizning Fragment havolangiz: {item.fragment_link}"
                )
        else:
            if context and chat_id:
                await context.bot.send_message(
                    chat_id,
                    "⚠️ Hozirda ushbu mahsulot omborda tugagan. Iltimos, admin bilan bog'laning."
                )

    if user.referred_by:
        referrer = db.query(User).filter(User.telegram_id == user.referred_by).first()
        if referrer:
            referrer.star_balance = getattr(referrer, 'star_balance', 0) + 5
            referrer.referral_count += 1

    db.commit()

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data_text = update.message.web_app_data.data
    try:
        payload = json.loads(data_text)
    except json.JSONDecodeError:
        await update.message.reply_text("Noto'g'ri ma'lumot yuborildi.")
        return

    user_id = str(update.message.from_user.id)
    db = get_db()

    action = payload.get('action')
    if action == 'purchase':
        product_key = payload.get('product')
        method = payload.get('method')
        custom_count = int(payload.get('count', 0)) if payload.get('count') else None

        if product_key == 'stars_custom':
            if not custom_count or custom_count < 50:
                await update.message.reply_text("Kamida 50 Stars buyurtma qilishingiz kerak.")
                db.close()
                return
            price_uzs = get_star_price(product_key, custom_count)
            product_name = format_star_name(product_key, custom_count)
        elif product_key.startswith('stars'):
            price_uzs = get_star_price(product_key)
            product_name = format_star_name(product_key)
        else:
            price_usd = PRODUCT_PRICES.get(product_key, 0)
            price_uzs = usd_to_uzs(price_usd)
            product_name = product_key.replace('_', ' ').title()

        if method == 'wallet':
            if wallet_payment(user_id, price_uzs, db):
                await process_purchase(user_id, product_key, product_name, 0, price_uzs, 'wallet', db, context, update.message.chat_id)
                emoji = "⭐️" if "stars" in product_key else "💎" if "premium" in product_key else "🎁"
                await update.message.reply_text(MESSAGES['payment_success'].format(product=product_name, emoji=emoji))
            else:
                await update.message.reply_text(MESSAGES['insufficient_balance'])
        elif method in ['payme', 'click'] and method in PROVIDER_TOKENS and PROVIDER_TOKENS[method]:
            product_title = f"Telegram {product_name}"
            await context.bot.send_invoice(
                chat_id=update.message.chat_id,
                title=product_title,
                description="Xaridni tasdiqlash uchun tugmani bosing.",
                payload=f"PAYMENT_{product_key}_{user_id}",
                provider_token=PROVIDER_TOKENS[method],
                currency="UZS",
                prices=[LabeledPrice("Narxi", int(price_uzs * 100))],
                start_parameter="bot-purchase-process"
            )
        else:
            await update.message.reply_text("Iltimos, Payme yoki Click uchun mini appdan foydalaning.")
        db.close()
        return

    elif action == 'topup':
        amount = int(payload.get('amount', 0))
        method = payload.get('method')
        if method in ['payme', 'click'] and method in PROVIDER_TOKENS and PROVIDER_TOKENS[method]:
            await context.bot.send_invoice(
                chat_id=update.message.chat_id,
                title="Hamyon to'ldirish",
                description=f"{amount} UZS hamyoningizga to'ldirish",
                payload=f"PAYMENT_topup_{amount}_{user_id}",
                provider_token=PROVIDER_TOKENS[method],
                currency="UZS",
                prices=[LabeledPrice("To'lov", amount * 100)],
                start_parameter="bot-purchase-process"
            )
        else:
            link, transaction_id = create_payment(user_id, 'topup', f"Topup {amount} UZS", 0, method, db)
            await update.message.reply_text(f"To'lovni amalga oshirish uchun havola: {link}")

    elif action == 'info':
        info_type = payload.get('type')
        if info_type == 'history':
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                transactions = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.created_at.desc()).limit(10).all()
                text = "Oxirgi tranzaksiyalar:\n"
                for t in transactions:
                    text += f"{t.created_at.strftime('%d.%m.%Y')} | {t.product_type} | {t.amount_uzs:.0f} UZS | {t.status}\n"
                await update.message.reply_text(text)
            else:
                await update.message.reply_text("Foydalanuvchi topilmadi.")
        elif info_type == 'stats':
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                total_deposits = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.product_type == 'topup', Transaction.status == 'success').with_entities(Transaction.amount_uzs).all()
                total_expenses = db.query(Transaction).filter(Transaction.user_id == user.id, Transaction.product_type != 'topup', Transaction.status == 'success').with_entities(Transaction.amount_uzs).all()
                deposits = sum(t[0] for t in total_deposits)
                expenses = sum(t[0] for t in total_expenses)
                await update.message.reply_text(f"Jami depozitlar: {deposits:.0f} UZS\nJami xarajatlar: {expenses:.0f} UZS\nTaklif qilganlar: {user.referral_count}")
            else:
                await update.message.reply_text("Foydalanuvchi topilmadi.")
        elif info_type == 'referral':
            user = db.query(User).filter(User.telegram_id == user_id).first()
            if user:
                link = f"https://t.me/{context.bot.username}?start={user.referral_code}"
                await update.message.reply_text(f"Sizning taklif havolangiz:\n{link}\n\nHar bir muvaffaqiyatli xariddan keyin referrerga 5 Stars bonus beriladi.")
            else:
                await update.message.reply_text("Foydalanuvchi topilmadi.")
        else:
            await update.message.reply_text("Noto'g'ri so'rov turi.")
    else:
        await update.message.reply_text("Noto'g'ri harakat kodi yuborildi.")

    db.close()

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    payload = query.invoice_payload
    if payload.startswith("PAYMENT_"):
        # Extract product_key and user_id from payload
        parts = payload.split("_")
        product_key = f"{parts[1]}_{parts[2]}" if len(parts) > 3 else parts[1]
        user_id = parts[-1]
        
        # Verify the user and product
        db = get_db()
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if user:
            await query.answer(ok=True)
        else:
            await query.answer(ok=False, error_message="Foydalanuvchi topilmadi.")
        db.close()
    else:
        await query.answer(ok=False, error_message="Noto'g'ri to'lov ma'lumotlari.")

async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    if not payload.startswith("PAYMENT_"):
        return

    parts = payload.split("_")
    product_key = f"{parts[1]}_{parts[2]}" if len(parts) > 3 else parts[1]
    user_id = parts[-1]

    db = get_db()
    price_uzs = payment.total_amount / 100  # Convert from tiyin to UZS
    price_usd = price_uzs / usd_to_uzs(1)  # Approximate USD conversion
    product_name = product_key.replace('_', ' ').title()

    await process_purchase(user_id, product_key, product_name, price_usd, price_uzs, 'telegram_invoice', db, context, update.message.chat_id)
    db.close()
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    application.run_polling()

if __name__ == '__main__':
    main()