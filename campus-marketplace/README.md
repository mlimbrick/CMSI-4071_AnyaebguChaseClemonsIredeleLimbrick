# Campus Marketplace

## Features
- Responsive customer storefront with search, category filters, campus filters, and listing details
- Student registration and login with `.edu` email format check (not actual email ownership verification)
- JWT authentication, password hashing, customer/vendor roles
- Vendor storefront profile editor and vendor dashboard
- Create, edit, hide, and delete vendor listings
- SQLite persistence with SQLAlchemy; PostgreSQL supported via DATABASE_URL and a PostgreSQL driver
- Six clearly labeled example listings shown in the frontend to illustrate the intended marketplace; they are not real vendors and cannot be edited

## Run backend

Requires Python 3.10+.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

## Run frontend

Requires Node.js 20+.

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Keep both terminals running.

## Try it
1. Register a **vendor** account with a sample `.edu` address and a password of 8+ characters.
2. Open **Vendor dashboard**, update your business profile, and publish a listing.
3. Return to **Explore** to find the listing, search for it, and filter by category.
4. Log out and register a **customer** account to browse listings.

## Scope and limitations
This is a development prototype, **not production ready**. `.edu` addresses are checked by suffix but are **not verified by email**. Do not use real passwords. Set `SECRET_KEY` to a long, random value before any deployment, enforce HTTPS, configure appropriate CORS origins, add email verification, migrations, tests, rate limiting, monitoring, image upload validation, and deployment infrastructure. The example listing images load from Unsplash and require internet access. The database is SQLite by default, not hosted PostgreSQL. Booking, payments, messaging, reviews, notifications, and admin moderation are not implemented because they are outside the Week 9 accomplishments.

## m4rk3t design update

The interface follows the supplied wireframes with Georgia serif typography and this palette:
`#780000`, `#C1121F`, `#FDF0D5`, `#003049`, and `#669BBC`.

Implemented screens include the landing page, login/sign-up dialogs, Discover with search and filters, My m4rk3t, public business profiles, service details, profile editing, and the vendor studio with service creation/editing. Navigation currently switches views inside the single-page app; these are not separate URL routes.

Registration supports an optional graduation year. Existing prototype databases receive an additive nullable graduation-year column on backend startup. Remember me keeps the session in local storage; unchecked sessions use session storage. Customers and vendors can edit their name and bio; vendors can also edit their business name.

Appointments/bookings have empty states. Followers, following, and reviews show unavailable counts until those systems exist. No bookings, reviews, or social activity are fabricated. Example businesses are labeled and support visual exploration only.

Recommended next pages and supporting features:
- Password recovery and reset, with a real email delivery service.
- School email verification and verification status.
- Booking availability, booking confirmation, and appointment details/cancellation.
- Vendor availability management and incoming booking requests.
- Reviews, followers/following, and notification preferences once their backend models exist.
