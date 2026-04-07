# Robinhood AI Portfolio Analyzer

An AI-powered portfolio analysis application that connects to your Robinhood brokerage account, imports your holdings and transaction history, and provides intelligent insights into your investments.

## What Has Been Built

- **User Authentication** — Registration, login, email verification (6-digit OTP), and JWT-based sessions. Passwords hashed with bcrypt.
- **Account Deletion** — Users can permanently delete their account and all associated data from Settings or the topbar menu, with confirmation dialog.
- **Robinhood Direct Connection** — Two-step MFA flow (SMS, email, TOTP, and push notification) using `robin_stocks` internals. Includes 15-second countdown for push approval, auto-trigger, and inline status feedback.
- **CSV Import** — Manual fallback: upload a CSV export from any brokerage to import positions.
- **Plaid Integration (backend only)** — Backend adapter, endpoints, and service layer are complete. Frontend wiring (Plaid Link widget) is planned for a future release.
- **Dashboard** — Portfolio overview, connected brokers, positions, unrealized gains, and cash balance.
- **Broker Management** — Connect, sync, and disconnect broker accounts. Encrypted token storage with Fernet.
- **Settings** — Profile info, system diagnostics, logout, and account deletion (danger zone).
- **Dockerized Dev Environment** — `docker compose up --build` runs everything with bind mounts for live reloading.
- **Responsive UI** — Next.js 16, Tailwind CSS, shadcn/ui, dark/light mode, protected routes, sidebar + topbar layout.

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy (async), Pydantic, JWT, bcrypt, Fernet encryption
- **Frontend**: Next.js 16, React, TypeScript, Tailwind CSS, shadcn/ui, Zustand, TanStack Query
- **Database**: SQLite (development), PostgreSQL-ready (production)
- **DevOps**: Docker, Docker Compose

## Running the App

### Option 1: Docker (Recommended)

1. Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. (Optional) Copy `.env.example` to `.env` and configure. Runs with defaults if absent.
3. Build and start:
   ```
   docker compose up --build
   ```
4. Open:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Swagger Docs: http://localhost:8000/docs
5. Source code is bind-mounted — edit files and changes reflect automatically.
6. Stop: `docker compose down`
7. Rebuild after dependency changes: `docker compose up --build`

### Option 2: Local Development

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Install frontend dependencies:
   ```
   cd frontend && npm install
   ```
3. Copy `.env.example` to `.env` and configure.
4. Start both services:
   ```
   cd frontend && npm run dev
   ```
   Runs FastAPI on port 8000 and Next.js on port 3000 concurrently.
