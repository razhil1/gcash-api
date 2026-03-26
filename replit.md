# QRPay — GCash & Maya Payment Link App

## Overview
A Flask web app for creating shareable QR payment links for GCash and Maya. Users create payment links, customers pay and upload proof, admins verify transactions. Also includes a public REST API for programmatic payment link creation.

## Architecture
- **Backend**: Python/Flask (app factory pattern)
- **Frontend**: Static HTML/CSS/JS served by Flask from the `frontend/` directory
- **Database**: SQLite by default (configurable via `DATABASE_URL` env var for PostgreSQL)
- **Auth**: JWT via Flask-JWT-Extended
- **Rate limiting**: Flask-Limiter (in-memory by default)

## Project Structure
```
run.py              # App entry point
app/
  __init__.py       # App factory (registers all blueprints)
  config.py         # Configuration classes
  extensions.py     # Flask extensions (db, jwt, limiter)
  models/           # SQLAlchemy models
    user.py         # User model (role: user/admin)
    payment_link.py # Payment links
    qr_wallet.py    # QR wallet (GCash/Maya)
    transaction.py  # Payment transactions
    upload.py       # File uploads (proof images)
    api_key.py      # API keys (qrp_ prefix)
  routes/           # Blueprint routes
    auth.py         # /api/auth/* (login, register, me, change-password)
    payments.py     # /api/payments/* (public payment page data)
    uploads.py      # /api/uploads/* (proof upload)
    qr_wallets.py   # /api/qr-wallets/*
    transactions.py # /api/transactions/* (legacy)
    user.py         # /api/user/* (stats, transactions, payment-links, wallets)
    admin.py        # /api/admin/* (stats, users, transactions, links, revenue chart)
    api_keys.py     # /api/keys/* (CRUD for API keys)
    public_api.py   # /api/v1/* (public REST API with Bearer token auth)
  utils/            # Helpers (security, validation)
frontend/
  index.html        # Landing page (black bg, Spline 3D, stats, API section)
  login.html        # Login page
  dashboard.html    # User dashboard (Transactions, Links, Wallets, API Keys, Settings)
  admin.html        # Admin panel (sidebar: Overview, Users, Transactions, Links, Wallets)
  payment.html      # Customer payment page (/pay/<slug>)
  assets/
    css/style.css   # Global design system
    js/api.js       # API client (all endpoints)
    js/utils.js     # Shared UI utilities
uploads/            # File storage for QR codes and payment proofs
```

## Running
The app runs via the "Start application" workflow using `python run.py` on port 5000.

## API Endpoints

### Auth
- `POST /api/auth/login`
- `POST /api/auth/register`
- `GET /api/auth/me`
- `POST /api/auth/change-password`

### User (JWT required)
- `GET /api/user/stats` — Stats + revenue_by_day chart data
- `GET /api/user/transactions`
- `GET/POST /api/user/payment-links`
- `PUT/DELETE /api/user/payment-links/<id>`
- `GET /api/user/wallets`

### Admin (JWT + admin role required)
- `GET /api/admin/stats`
- `GET /api/admin/users` (search, role filter, pagination)
- `POST /api/admin/users/<id>/toggle`
- `PUT /api/admin/users/<id>/role`
- `GET /api/admin/transactions` (status/search filter)
- `POST /api/admin/transactions/<id>/review` (approve/reject)
- `GET /api/admin/revenue/chart?days=N`
- `GET /api/admin/payment-links`

### API Keys (JWT required)
- `GET/POST /api/keys`
- `DELETE /api/keys/<id>`
- `PUT /api/keys/<id>/name`

### Public REST API (Bearer token: qrp_... key)
- `GET /api/v1/me`
- `GET/POST /api/v1/links`
- `GET/DELETE /api/v1/links/<slug>`

## Environment Variables
Set these as Replit secrets:
- `DATABASE_URL` — PostgreSQL URL (defaults to SQLite if not set)
- `SECRET_KEY` — Flask secret key
- `JWT_SECRET_KEY` — JWT signing secret

## Default Admin Account
On first run, a default admin is created:
- Email: `admin@gcashpay.com`
- Password: `admin123`

**Change this password immediately in production.**

## Features Implemented
- Black homepage with Spline 3D background (WebGL — works in real browsers)
- Stats section + Developer API showcase section on homepage
- User dashboard with 5 tabs: Transactions, Payment Links, QR Wallets, API Keys, Settings
- Admin panel (`/admin`) with sidebar navigation and full CRUD
- Public REST API at `/api/v1/` with API key authentication
- API key generation, listing, revocation from dashboard
- Change password from Settings tab
