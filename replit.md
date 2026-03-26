# QRPay — GCash & Maya Payment Link App

## Overview
A Flask web app for creating shareable QR payment links for GCash and Maya. Users can create payment links, accept payments with proof of payment upload, and admins can verify transactions.

## Architecture
- **Backend**: Python/Flask (app factory pattern)
- **Frontend**: Static HTML/CSS/JS served by Flask from the `frontend/` directory
- **Database**: SQLite by default (configurable via `DATABASE_URL` env var for PostgreSQL)
- **Auth**: JWT via Flask-JWT-Extended
- **Payments**: PayMongo integration
- **Rate limiting**: Flask-Limiter (in-memory by default)

## Project Structure
```
run.py              # App entry point
app/
  __init__.py       # App factory (create_app)
  config.py         # Configuration classes
  extensions.py     # Flask extensions (db, jwt, limiter)
  models/           # SQLAlchemy models (user, payment_link, qr_wallet, transaction, upload)
  routes/           # Blueprint routes (auth, payments, uploads, qr_wallets, transactions)
  services/         # Business logic services
  utils/            # Helpers (security, validation)
frontend/
  index.html        # Landing page
  login.html        # Login page
  dashboard.html    # User dashboard
  payment.html      # Payment page (/pay/<slug>)
  assets/           # CSS and JS
uploads/            # File storage for QR codes and payment proofs
```

## Running
The app runs via the "Start application" workflow using `python run.py` on port 5000.

## API Endpoints
- `POST /api/auth/login` — Login
- `POST /api/auth/register` — Register
- `GET /api/auth/me` — Current user (JWT required)
- `POST /api/auth/change-password` — Change password (JWT required)
- `/api/payments/*` — Payment link management
- `/api/uploads/*` — File upload handling
- `/api/qr-wallets/*` — QR wallet management
- `/api/transactions/*` — Transaction history

## Environment Variables
Set these as Replit secrets:
- `DATABASE_URL` — PostgreSQL URL (defaults to SQLite if not set)
- `SECRET_KEY` — Flask secret key
- `JWT_SECRET_KEY` — JWT signing secret
- `PAYMONGO_SECRET_KEY` — PayMongo secret key
- `PAYMONGO_PUBLIC_KEY` — PayMongo public key
- `PAYMONGO_WEBHOOK_SECRET` — PayMongo webhook secret

## Default Admin Account
On first run, a default admin is created:
- Email: `admin@gcashpay.com`
- Password: `admin123`
**Change this password immediately in production.**

## Migration Notes
- Migrated from Vercel (serverless Python) to Replit (persistent Flask server)
- Removed all Vercel-specific `/tmp` storage workarounds
- App now runs persistently on port 5000, host 0.0.0.0
