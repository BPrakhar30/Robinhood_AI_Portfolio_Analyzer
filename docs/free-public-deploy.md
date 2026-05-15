# Free Public Deployment

This path deploys the app publicly without requiring paid subscriptions and
keeps AI API keys empty until you choose to enable them.

## Target Stack

- Frontend: Cloudflare Pages free tier, public `*.pages.dev` URL.
- Backend and MCP: one Render Free Web Service running the backend Dockerfile.
- Database: Supabase Free Postgres.
- Email: generic SMTP. Public registration stays disabled until SMTP delivery
  is proven.
- AI: keys are blank at first. AI screens should show a not-configured state.

## 1. Prepare Secrets

Generate production secrets locally:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use different values for `SECRET_KEY`, `JWT_SECRET_KEY`, and `ENCRYPTION_KEY`.

## 2. Create Supabase Free Postgres

Create a free Supabase project and copy both database URLs:

- Runtime async URL: `postgresql+asyncpg://...?...sslmode=require`
- Migration sync URL: `postgresql://...?...sslmode=require`

The app strips `sslmode=require` from the asyncpg runtime URL and passes SSL
through driver settings, while Alembic keeps the sync URL as-is.

## 3. Deploy Backend On Render Free

Create a Render Web Service from this repo and use Docker.

Set the root directory to `Robinhood_AI_Portfolio_Analyzer` if deploying from
the parent workspace.

The Dockerfile command runs:

```bash
python -m scripts.start_production
```

That command applies Alembic migrations, seeds the demo user when enabled,
starts MCP on localhost, and starts FastAPI on Render's `$PORT`.

Backend environment:

```bash
APP_ENV=production
DEBUG=false
FRONTEND_URL=https://your-cloudflare-project.pages.dev
DATABASE_URL=postgresql+asyncpg://...
DATABASE_URL_SYNC=postgresql://...
MCP_SERVER_URL=http://127.0.0.1:8765/mcp
SECRET_KEY=...
JWT_SECRET_KEY=...
ENCRYPTION_KEY=...
ENABLE_PUBLIC_REGISTRATION=false
SEED_DEMO_USER=true
DEMO_USER_EMAIL=you@example.com
DEMO_USER_PASSWORD=generate-a-long-password
RESET_DEMO_USER_PASSWORD=false
GOOGLE_API_KEY=
OPENAI_API_KEY=
OPENROUTER_API_KEY=
ENABLE_PLAID=false
ENABLE_FINNHUB=false
LOGFIRE_TOKEN=
```

After deploy, verify:

```bash
curl https://your-render-service.onrender.com/health
```

## 4. Deploy Frontend On Cloudflare Pages

Create a Cloudflare Pages project for the `frontend` directory.

Build settings:

```bash
npm ci
npm run build
```

Environment:

```bash
NEXT_PUBLIC_API_URL=https://your-render-service.onrender.com
NEXT_PUBLIC_ENABLE_PLAID=false
```

After the first Pages deploy, copy the `*.pages.dev` URL back into Render as
`FRONTEND_URL`, then redeploy the backend so CORS uses the real frontend origin.

## 5. Public Smoke Test

Open the Cloudflare Pages URL in an incognito browser on a different network.

Verify:

- The landing page loads over HTTPS.
- Login works with `DEMO_USER_EMAIL` and `DEMO_USER_PASSWORD`.
- Protected pages load without CORS errors.
- `/health` returns healthy JSON from the public Render URL.
- Dashboard, brokers, stocks, markets, and macro pages render empty states or
  public market data.
- CSV import works.
- Assistant UI does not crash while AI keys are empty. It should show that AI
  is not configured.
- Plaid, Finnhub, Logfire, and AI keys are not required for startup.
- Data persists after the Render service sleeps and wakes.

## 6. Enable Public Registration Later

Public registration requires real email delivery. Use the existing SMTP
settings with a no-paid-subscription path:

- Open-source path: run Postfix, Mailu, or docker-mailserver on a user-controlled
  Linux host and configure `MX`, `SPF`, `DKIM`, and `DMARC`.
- Staging only: Mailpit/MailHog can test flows but do not deliver public email.

When SMTP is proven with a real inbox:

```bash
SMTP_HOST=...
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_FROM_EMAIL=noreply@your-domain.example
SMTP_USE_TLS=true
ENABLE_PUBLIC_REGISTRATION=true
```

Redeploy backend and test register, verify email, forgot password, and reset
password from the public frontend.

## Free-Tier Limits

Free services can sleep, cold-start, pause inactive projects, or enforce small
storage and bandwidth limits. This is acceptable for a public demo or beta, but
not for a high-traffic production finance app.
