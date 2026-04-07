# Robinhood AI Portfolio Analyzer

An AI-powered portfolio analysis application that connects to your Robinhood brokerage account, imports your holdings and transaction history, and provides intelligent insights into your investments.

## What This Project Does

This is a full-stack application with a FastAPI (Python) backend and a Next.js (TypeScript) frontend. It allows users to create an account, connect their brokerage data through multiple methods, and view their portfolio in a clean dashboard interface.

## What Has Been Built So Far

- **User Authentication** — Registration, login, and logout with JWT-based session management.
- **Email Verification** — 6-digit OTP code sent to the user's email on registration. Codes expire after 15 minutes. In development mode, codes are logged to the terminal console.
- **Account Connection Layer** — Three methods to import brokerage data (see below).
- **Dashboard** — Displays portfolio overview, connected brokers, positions, and summary stats once an account is linked.
- **Broker Management** — Connect, disconnect, and sync broker accounts from the Brokers page.
- **Frontend UI** — Production-quality interface built with Next.js 15, Tailwind CSS, and shadcn/ui components. Includes protected routes, toast notifications, and responsive layout with a sidebar and topbar.
- **Security** — Passwords hashed with bcrypt, broker tokens encrypted with Fernet, CORS configured, and sensitive data excluded from version control.

## Three Methods to Connect Your Brokerage

### 1. Robinhood Direct Login
Connect directly using your Robinhood username and password. The app uses the `robin_stocks` library to authenticate with Robinhood's API and pull your holdings, cost basis, and transaction history. MFA is supported when required by your account.

### 2. Plaid Integration
Plaid provides automatic, secure account linking through its bank-grade infrastructure. When configured with Plaid API credentials, a Plaid Link session opens in the browser to connect your brokerage without sharing your login credentials with the app. Requires server-side Plaid API keys to be set up.

### 3. CSV Import
Upload a CSV export of your portfolio data as a manual fallback. This works with any brokerage — export your holdings from your broker's website, then upload the file through the app. The importer parses ticker symbols, quantities, average cost, and cash balance from the CSV.

## Features

- User registration and login with JWT authentication
- 6-digit OTP email verification for new accounts
- Robinhood API integration for automatic portfolio import
- Plaid integration for secure third-party account linking
- CSV file upload for manual portfolio import
- Dashboard with portfolio value, positions count, unrealized gains, and cash balance
- Broker connection management (connect, sync, disconnect)
- Encrypted storage of broker credentials and tokens
- Responsive UI with dark/light mode support
- Inline feedback for user actions (no external toast popups)
- Protected routes with authentication guard
- Health check endpoint and system status indicator
- Dockerized development environment with bind mounts for live reloading

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy (async), Pydantic, JWT, bcrypt, Fernet encryption
- **Frontend**: Next.js 16, React, TypeScript, Tailwind CSS, shadcn/ui, Zustand, TanStack Query
- **Database**: SQLite (development), PostgreSQL-ready (production)
- **DevOps**: Docker, Docker Compose

## Running the App

### Option 1: Docker (Recommended)

This is the simplest way to run the app — no Python or Node.js installation required on your machine. Just Docker.

1. Make sure [Docker Desktop](https://www.docker.com/products/docker-desktop/) is installed and running.

2. (Optional) Copy `.env.example` to `.env` and fill in your configuration values. The app runs with sensible defaults (SQLite, development mode) if `.env` is absent.

3. Build and start both services:
   ```
   docker compose up --build
   ```

4. Open the app:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs (Swagger): http://localhost:8000/docs

5. **Live reloading**: Source code is bind-mounted into the containers. Edit any file under `app/` (backend) or `frontend/src/` (frontend) and the changes reflect automatically — no rebuild needed.

6. Stop the containers:
   ```
   docker compose down
   ```

7. If you change `requirements.txt` or `package.json` (new dependencies), rebuild:
   ```
   docker compose up --build
   ```

### Option 2: Local Development (without Docker)

1. Set up Python and install dependencies (works with venv, conda, or system Python — just make sure `python` is in your PATH):
   ```
   pip install -r requirements.txt
   ```

2. Install frontend dependencies:
   ```
   cd frontend
   npm install
   ```

3. Copy `.env.example` to `.env` and fill in your configuration values.

4. Start both backend and frontend with a single command:
   ```
   cd frontend
   npm run dev
   ```
   This runs the FastAPI backend on port 8000 and the Next.js frontend on port 3000 concurrently.
