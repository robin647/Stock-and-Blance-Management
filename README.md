# Mahir Sherwani — Showroom Stock & Sales Management System

A centralized system for managing daily stock and sales/balance across 5 showrooms:
Mahadi Zone-1, Mahadi Zone-2, Mahadi Zone-3, Mahadi Zone-4, and Mahir Sherwani.

- **Admin** manages showrooms, products, and views reports across all showrooms.
- **Showroom User** logs in and can only see/update their own showroom's daily stock and balance.

## Tech stack

- Backend: Django, Django REST Framework, PostgreSQL, JWT (SimpleJWT), Gunicorn, WhiteNoise
- Frontend: React (Vite), React Router, Axios, Tailwind CSS, Recharts
- Database: **PostgreSQL only** (local and production)

---

## 1. Local development (without Docker)

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: set DATABASE_URL to point at your local PostgreSQL instance

# Make sure PostgreSQL is running and the database/user in .env exist, e.g.:
#   createuser mahir_user --pwprompt
#   createdb mahir_showroom -O mahir_user

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`.

### Frontend

```bash
cd frontend
cp .env.example .env   # VITE_API_URL=http://localhost:8000/api
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

---

## 2. Local development with Docker

```bash
docker compose up --build
```

This starts:
- `db` — PostgreSQL 16
- `backend` — Django + Gunicorn on port 8000 (migrations run automatically on startup)
- `frontend` — React build served by nginx on port 3000

Then create an admin user inside the running backend container:

```bash
docker compose exec backend python manage.py createsuperuser
```

Visit `http://localhost:3000`.

---

## 3. First-time setup after deployment (either method)

1. Log in to `/admin/` (Django admin) with the superuser you created, or use the API.
2. As Admin, create the 5 showrooms (Mahadi Zone-1 … Mahir Sherwani).
3. Create product categories (Panjabi, Pajama, Shirt, Shoe, …) and products.
4. From the app's **Showrooms** page, create a login (username/password) for each showroom — this automatically ties that user to their showroom with the `showroom_user` role.
5. Give the credentials to each showroom to start logging daily stock and balance.

---

## 4. Deploying to Render

Render needs three pieces: a PostgreSQL database, a backend web service, and a frontend static site.

### Step 1 — PostgreSQL database

1. Render dashboard → **New** → **PostgreSQL**.
2. Choose a name (e.g. `mahir-showroom-db`) and region.
3. Once created, copy the **Internal Database URL** — you'll use it as `DATABASE_URL` for the backend service.

### Step 2 — Backend web service

1. Render dashboard → **New** → **Web Service** → connect your GitHub repo.
2. Root directory: `backend`
3. Runtime: Docker (it will use `backend/Dockerfile` automatically), **or** if not using Docker:
   - Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - Start command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`
4. Environment variables:

   | Key | Value |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `config.settings.production` |
   | `SECRET_KEY` | (generate a long random string) |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | `your-backend-service.onrender.com` |
   | `DATABASE_URL` | (Internal Database URL from Step 1) |
   | `CORS_ALLOWED_ORIGINS` | `https://your-frontend-site.onrender.com` |

5. Deploy. Once live, run migrations if they didn't run automatically (Render Shell tab):
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

### Step 3 — Frontend static site

1. Render dashboard → **New** → **Static Site** → same repo.
2. Root directory: `frontend`
3. Build command: `npm install && npm run build`
4. Publish directory: `dist`
5. Environment variable:

   | Key | Value |
   |---|---|
   | `VITE_API_URL` | `https://your-backend-service.onrender.com/api` |

6. Add a rewrite rule so client-side routing works: **Redirects/Rewrites** → source `/*`, destination `/index.html`, action `Rewrite`.

### Step 4 — Connect them

- Update the backend's `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS` to match the final Render URLs once both services are live (Render assigns the `.onrender.com` subdomain on first deploy, so you may need one redeploy after both services exist).

No secrets or API keys are hardcoded anywhere in this codebase — everything sensitive is read from environment variables (`.env` locally, Render's Environment tab in production).

---

## 5. Project structure

```
backend/    Django REST API (see backend/apps/*)
frontend/   React SPA (see frontend/src)
docker-compose.yml   Local multi-service dev environment
```

Key business rules enforced server-side (not just in the UI):
- `Closing Stock = Opening + Received - Sold + Return`, cannot go negative.
- Yesterday's closing stock/balance automatically becomes today's opening — the frontend never sends `opening_qty` / `opening_balance`.
- `Total Sale = Cash Sale + Card Sale`; `Closing Balance = Opening + Cash - Expense - Salary - Deposit` (card sale is excluded from the cash closing balance).
- One stock entry per (showroom, product, date) and one balance entry per (showroom, date) — enforced by database unique constraints.
- A showroom user's `showroom_id` is always taken from their own JWT/account on the server, never trusted from the request body — so a tampered frontend request cannot write to another showroom.

## 6. Environment variable reference

See `backend/.env.example` and `frontend/.env.example` for the full list.

## 7. Stock Adjustments and Wholesale

The Admin Panel now includes **Product Stock Adjustment**, **Wholesale Parties**, **Wholesale Sales / New Invoice**, **Wholesale Returns**, **All Parties Summary**, and **Wholesale Reports**. Product codes are optional for existing products and unique when supplied.

Stock adjustments set an exact quantity at either Factory or one selected Showroom. Every adjustment stores its previous/new quantity, signed difference, reason, user, and timestamp; other inventory locations are not changed. Existing daily and monthly showroom reports include showroom adjustment deltas.

Wholesale invoices are immutable after creation. Their product quantities are deducted transactionally from the selected factory/showroom stock. Follow-on payments and item-level returns are separate immutable records. A return restores stock to the invoice's original location. Invoice outstanding due is kept nonnegative; return value beyond amounts still owed is recorded as a separate party/invoice credit. Invoice numbers are unique.

Payments remain explicitly allocated to one invoice, matching the existing invoice-level account model; a payment cannot exceed that invoice's outstanding due. The party statement lists each sale by sale date, each payment by payment date, and each return by return date. Its debit-positive running balance starts with the full account balance before the selected start date; sales increase it and payments/returns reduce it. Any negative closing balance is shown separately as party credit. Return amounts must match the original sale unit price and cannot exceed the unreturned quantity/value. Optional API `Idempotency-Key` headers make payment and return retries safe. Parties are deactivated rather than hard-deleted.

Wholesale routes include `/api/wholesale/parties/` (search with `?search=`), `/api/wholesale/parties/{id}/history/` (date/type/bill/product filters and pagination), `/api/wholesale/parties/{id}/statement/export/`, `/api/wholesale/invoices/`, `/api/wholesale/payments/`, `/api/wholesale/returns/`, `/api/wholesale/summary/`, and `/api/wholesale/summary/export/`. All financial endpoints require an authenticated Admin account.

### Easy Wholesale Sales Management

The separate **Easy Wholesale Sales Management** page offers Sales, Payments, and Returns histories using existing parties. Its APIs are `/api/wholesale/easy/sales/`, `/api/wholesale/easy/payments/`, and `/api/wholesale/easy/returns/` (GET lists and POST creates; finalized transactions are immutable). Easy payments are party-level ledger transactions and do not require or modify an invoice. Easy returns can be financial-only, or linked to an Easy sale to validate remaining quantity and restore stock at that sale's original selected location. A standalone physical return changes stock only when an Admin explicitly selects a product and destination. A sale only moves inventory when an Admin explicitly selects a catalog product and factory/showroom location; product-name-only and product-free sales are financial-only.

All Easy transactions are included once in the existing selected-party statement and All Parties Summary. Easy events retain their own date and transaction type. Existing invoice-linked Wholesale Sales, payments, and returns remain on their original APIs and screens.

Apply the new migrations `wholesale.0003_easywholesalesale_easywholesalereturn_and_more`, `wholesale.0004_easywholesalestockmovement`, and `wholesale.0005_easywholesalestockmovement_easy_stock_move_matches_transaction_and_more` with the standard `python manage.py migrate` step before deploying the new routes. These are forward-only additions and preserve existing invoice, payment, return, party, and stock data.

### Apply migrations

Run against a reachable local PostgreSQL database before starting the app:

```bash
cd backend
python manage.py migrate
```

The additive migrations are `products.0002_product_code`, `inventory.0004_stockadjustment`, `wholesale.0001_initial`, and `wholesale.0002_wholesaleparty_contact_person_and_more`. They do not reset or rewrite existing product, showroom, or stock records. Existing product codes remain `NULL` until an Admin assigns them.

### Verify locally

```bash
cd backend
python manage.py check
python manage.py test apps.inventory.tests apps.wholesale.tests
cd ../frontend
npm run build
```

Wholesale API routes are under `/api/wholesale/`; all management, invoice, payment, return, summary, and export endpoints are Admin-only and use the existing JWT authentication.

### Deploy to Render

Deploy the backend and frontend as usual, ensuring `DATABASE_URL` points at the existing Render PostgreSQL database. Before serving traffic on the new code, run `python manage.py migrate` once from the Render Shell (or use the configured release/build migration step). Then deploy the frontend build. Do not run `flush`, drop tables, or reset the database; no data reset is needed. The existing build may warn that the frontend JavaScript bundle exceeds Vite's default 500 kB advisory threshold; the build still completes successfully.
