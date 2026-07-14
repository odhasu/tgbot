# ShopBot

A production-quality Telegram marketplace bot built with **aiogram 3**, **SQLAlchemy (async)**, and **SQLite**. Clean layered architecture (handlers → services → repositories → models) designed to grow into crypto payments, automatic digital delivery, referrals, coupons, and a web dashboard without a rewrite.

## Features

- Auto-registration on `/start` (Telegram ID, username, display name, balance, stats)
- Shop: categories → products → detail → purchase confirmation
- Internal wallet balance, profile, support (links out to a real Telegram contact)
- Section banner images (Shop/Balance/Profile/home) sent as photo headers, no emoji in any bot text or button
- Full admin panel (admin-only): product/category CRUD, user search & balance management, order status changes, broadcast messages, statistics
- Structured logging (console + rotating file) for errors, purchases, admin actions, and registrations
- Alembic migrations for schema evolution

## Requirements

- Python 3.11+ (3.12 recommended)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

## Installation

```bash
cd shopbot
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

```env
BOT_TOKEN=123456789:your-real-bot-token
ADMIN_IDS=111111111,222222222
DATABASE_URL=sqlite+aiosqlite:///data/shopbot.db
LOG_LEVEL=INFO
SUPPORT_CONTACT=@vexaccs
```

## Running the Bot

```bash
source .venv/bin/activate
python bot.py
```

On first run, `bot.py` calls `database.init_db()`, which creates every table automatically — no manual migration step needed to get started. Add at least one category and product through the admin panel ("Admin" in the main menu) before users can buy anything.

### Schema changes (Alembic)

`init_db()` only creates missing tables — it does not alter existing ones. Once you modify a model, use Alembic instead:

```bash
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

## Adding Admins

Admin status is granted by Telegram ID, read from `ADMIN_IDS` in `.env` (comma-separated). It's applied the moment that ID first registers via `/start`. To promote a user later, add their ID to `ADMIN_IDS` and have them send `/start` again, or set `is_admin` directly on their row in `data/shopbot.db`.

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `BOT_TOKEN` | Telegram bot token (required) | — |
| `ADMIN_IDS` | Comma-separated Telegram user IDs granted admin access | (empty) |
| `DATABASE_URL` | SQLAlchemy async DB URL | `sqlite+aiosqlite:///data/shopbot.db` |
| `LOG_LEVEL` | Root logging level | `INFO` |
| `SUPPORT_CONTACT` | Telegram @username linked from the Support screen's "Message Support" button | `@vexaccs` |

## Folder Structure

```
shopbot/
├── bot.py                 # Entrypoint: logging, DB init, Bot/Dispatcher, error handler, polling
├── config.py               # Settings loaded from .env
├── database.py              # Async engine, session factory, Base, init_db()
├── requirements.txt
├── .env.example
├── alembic.ini
├── migrations/              # Alembic environment + versioned schema migrations
├── handlers/                 # Aiogram routers — receive updates, call services only
│   ├── start.py               # /start registration
│   ├── shop.py                 # Browse categories/products, purchase flow
│   ├── balance.py, profile.py, support.py
│   ├── menu.py                 # Home navigation
│   └── admin/                   # Admin-only subtree (IsAdmin-filtered)
│       ├── menu.py, products.py, categories.py
│       ├── users.py, orders.py, stats.py, broadcast.py
├── keyboards/                # Inline keyboard builders
├── middlewares/               # DbSessionMiddleware — injects AsyncSession per update
├── filters/                    # IsAdmin filter
├── services/                    # Business logic (balance checks, stock checks, permissions)
│   ├── user_service.py, shop_service.py, order_service.py, admin_service.py
│   └── exceptions.py             # Typed domain errors handlers catch for friendly messages
├── repositories/                  # All SQL lives here — never in handlers or services
├── models/                         # SQLAlchemy ORM models (User, Category, Product, Order)
├── states/                         # FSM state groups for multi-step admin flows
├── utils/                          # logger.py, formatting.py, telegram.py (photo/text render helpers), banners.py (section banner images)
├── assets/banners/                 # Static section banner images (vex/shop/balance/topup/profile)
├── data/                            # SQLite database file (gitignored)
└── logs/                            # Rotating log files (gitignored)
```

## Architecture Rules

- **Handlers never touch SQL or business rules.** They parse the update, call a service, and render a keyboard/message.
- **Services own transactions.** Each service method commits its own unit of work and raises typed exceptions (`services/exceptions.py`) on business-rule violations (insufficient balance, out of stock, not found, etc.) instead of returning error codes.
- **Repositories are the only place SQL/SQLAlchemy queries are written.**
- A global error handler in `bot.py` catches anything unhandled, logs it, and replies with a friendly message — the bot never crashes on an update.

## Roadmap

The architecture already isolates the pieces these will need — new services/repositories/handlers slot in without touching existing modules:

- Crypto payment processing
- Automatic digital product delivery (already has a `delivery_type` field: manual vs. automatic)
- Support ticket system
- Referral program
- Coupons / discount codes
- Web dashboard (the service layer is transport-agnostic — a REST/FastAPI layer could reuse it directly)
