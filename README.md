# UzStar & Premium Bot

Telegram bot for selling Telegram Stars, Premium subscriptions, and digital gifts in Uzbekistan (UZS).

## Features

- **Financial Integration**: Support for Click, Payme, Uzum, Alif payment methods
- **Virtual Wallet**: Users can top up and use balance for instant purchases
- **Product Logic**: Stars, Premium subscriptions, and gift cards with restrictions
- **Referral System**: Unique referral links with rewards
- **User Dashboard**: Transaction history and statistics
- **Uzbek Language**: Full Uzbek interface

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a Telegram bot and get the token from @BotFather

3. Configure environment variables in `.env` file:
   - Set `BOT_TOKEN` to your bot token
   - Set `WEBAPP_URL` to your deployed web app URL
   - Configure payment provider credentials

4. Run the bot:
   ```bash
   python main.py
   ```

## Database

The bot uses SQLite by default. Database tables are created automatically on first run.

## Web App Mini App

The bot now launches a Telegram Web App for shopping. Users can browse Stars, Premium, gifts, and wallet top-up options inside the mini app.

## Payment Integration

This implementation includes placeholders for payment providers. In production:

1. Implement actual API calls for each provider
2. Set up webhooks for payment callbacks
3. Handle real payment statuses

## Currency Conversion

Prices are stored in USD and converted to UZS using CBU.uz exchange rates.

## Referral System

Users get unique referral codes. When a referred user makes a purchase, the referrer receives a percentage of the transaction amount.

## Security

- Use HTTPS for webhooks
- Validate all incoming data
- Store sensitive data securely
- Implement rate limiting

## Deployment

For production deployment:

1. Use a proper database (PostgreSQL recommended)
2. Set up proper logging
3. Configure webhooks instead of polling
4. Use environment variables for all secrets
5. Implement monitoring and alerts