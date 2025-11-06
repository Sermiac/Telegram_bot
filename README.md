# Telegram Bot

A Telegram bot that helps users manage and query product information efficiently.

## Features

- List all available products.
- Get the price of a product by name.
- Calculate total cost based on quantity.
- Notify a designated Telegram group about requested products.

## Setup

1. **Clone the repository**:
```bash
git clone https://github.com/Sermiac/telegram_bot.git
cd telegram_bot
```

2. **Create a .env file:**
```bash
BOT_TOKEN=your_telegram_bot_token
GROUP_ID=your_telegram_group_id
SHEET1_URL=your_google_sheet_url_1
SHEET2_URL=your_google_sheet_url_2
```

3. **Install dependencies (example for Python):**
```bash
pip install -r requirements.txt
```

4. **Run the bot:**
```bash
python3 bot.py
```

## Usage

/start – Default mode.

/precios – Prices mode.
<product_name> – Returns the price of a product.

/cuentas Accounting mode.
<product_name> <quantity> – Calculates prices based on ammount of products.

Notifications are sent automatically to the group defined in GROUP_ID.

## Security
Do not commit .env or credentials.json to public repositories.

Store all sensitive data in .env and include it in .gitignore.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License
This project is open-source. See the LICENSE file for details.