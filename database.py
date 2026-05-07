from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    wallet_balance = Column(Float, default=0.0)
    star_balance = Column(Integer, default=0)
    referral_code = Column(String, unique=True)
    referred_by = Column(String)  # telegram_id of referrer
    referral_count = Column(Integer, default=0)
    active_premium = Column(Boolean, default=False)
    premium_expiry = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user")
    gifts = relationship("Gift", back_populates="user")

class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    product_type = Column(String, nullable=False)  # stars, premium, gift, topup
    product_details = Column(Text)  # JSON string with details
    amount_usd = Column(Float)
    amount_uzs = Column(Float, nullable=False)
    payment_method = Column(String)  # payme, click, uzum, alif, wallet
    status = Column(String, default='pending')  # pending, success, failed
    transaction_id = Column(String)  # external payment ID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="transactions")

class Gift(Base):
    __tablename__ = 'gifts'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    claim_code = Column(String, unique=True, nullable=False)
    gift_type = Column(String, nullable=False)
    value = Column(Float, nullable=False)
    claimed = Column(Boolean, default=False)
    claimed_by = Column(String)  # telegram_id
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    claimed_at = Column(DateTime)

    user = relationship("User", back_populates="gifts")

class FragmentInventory(Base):
    __tablename__ = 'fragment_inventory'
    id = Column(Integer, primary_key=True)
    product_type = Column(String)  # 'premium_monthly', 'stars_100', etc.
    fragment_link = Column(String, unique=True)  # The URL from Fragment
    is_sold = Column(Boolean, default=False)

# Database setup
engine = create_engine('sqlite:///telegrambot.db', echo=False)
Base.metadata.create_all(engine)

if engine.dialect.name == 'sqlite':
    with engine.connect() as conn:
        result = conn.execute("PRAGMA table_info(users)").fetchall()
        existing_columns = [row[1] for row in result]
        if 'star_balance' not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN star_balance INTEGER DEFAULT 0")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()