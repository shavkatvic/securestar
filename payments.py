import requests
import uuid
from config import *
from database import get_db, Transaction, User
from sqlalchemy.orm import Session

class PaymentProvider:
    def __init__(self, name, api_key, merchant_id):
        self.name = name
        self.api_key = api_key
        self.merchant_id = merchant_id

    def generate_payment_link(self, amount, description, user_id):
        # This is a placeholder. In real implementation, call the provider's API
        transaction_id = str(uuid.uuid4())
        # Simulate deep link
        link = f"{self.name.lower()}://pay?amount={amount}&merchant={self.merchant_id}&desc={description}&transaction={transaction_id}"
        return link, transaction_id

    def check_payment_status(self, transaction_id):
        # Placeholder for checking payment status
        # In real implementation, query the provider's API
        return "success"  # or "pending", "failed"

class PaymeProvider(PaymentProvider):
    def __init__(self):
        super().__init__("Payme", PAYME_API_KEY, PAYME_MERCHANT_ID)

class ClickProvider(PaymentProvider):
    def __init__(self):
        super().__init__("Click", CLICK_API_KEY, CLICK_MERCHANT_ID)

class UzumProvider(PaymentProvider):
    def __init__(self):
        super().__init__("Uzum", UZUM_API_KEY, UZUM_MERCHANT_ID)

class AlifProvider(PaymentProvider):
    def __init__(self):
        super().__init__("Alif", ALIF_API_KEY, ALIF_MERCHANT_ID)

# Instances
payme = PaymeProvider()
click = ClickProvider()
uzum = UzumProvider()
alif = AlifProvider()

providers = {
    'payme': payme,
    'click': click,
    'uzum': uzum,
    'alif': alif,
}

def get_exchange_rate():
    # Fetch USD to UZS rate from CBU.uz
    try:
        response = requests.get(EXCHANGE_API_URL)
        data = response.json()
        usd_rate = next(item['Rate'] for item in data if item['Ccy'] == 'USD')
        return float(usd_rate)
    except:
        return 12600  # Fallback rate

def usd_to_uzs(amount_usd):
    rate = get_exchange_rate()
    return amount_usd * rate

def create_payment(user_id, product_type, product_details, amount_usd, payment_method, db: Session):
    amount_uzs = usd_to_uzs(amount_usd)
    provider = providers.get(payment_method)
    if not provider:
        return None, "Invalid payment method"

    link, transaction_id = provider.generate_payment_link(amount_uzs, f"{product_type}: {product_details}", user_id)

    # Save transaction to DB
    transaction = Transaction(
        user_id=user_id,
        product_type=product_type,
        product_details=product_details,
        amount_usd=amount_usd,
        amount_uzs=amount_uzs,
        payment_method=payment_method,
        transaction_id=transaction_id,
        status='pending'
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return link, transaction_id

def process_payment_callback(transaction_id, status):
    db = get_db()
    transaction = db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()
    if transaction:
        transaction.status = status
        db.commit()
        if status == 'success':
            # Update user balance or activate product
            # This will be handled in the main bot logic
            pass
    db.close()

def wallet_payment(user_id, amount_uzs, db: Session):
    # Check if user has enough balance
    user = db.query(User).filter(User.telegram_id == user_id).first()
    if user and user.wallet_balance >= amount_uzs:
        user.wallet_balance -= amount_uzs
        return True
    return False