# Hosting Smart Jaggery Mart on Railway

Railway runs Python, Node and PostgreSQL, so this project deploys as-is — no
code changes needed. You create three services in one project:

| Service    | What it is                | Root directory |
| ---------- | ------------------------- | -------------- |
| `Postgres` | the database              | —              |
| `backend`  | Flask API                 | `backend`      |
| `frontend` | Express website (public)  | `frontend`     |

**One advantage over Render:** Railway can point the frontend at the backend
automatically with a *reference variable*, so there is no copying-and-pasting
a URL between services.

## Before you start

- Push your code to GitHub (already done).
- Sign up at <https://railway.com> with your GitHub account.

## 1. Create the project and the database

1. Click **New Project**.
2. Choose **Deploy PostgreSQL** (or **Add PostgreSQL** / **Database →
   PostgreSQL**). A service named `Postgres` appears on the canvas.

Leave it alone — it needs no configuration.

## 2. Add the backend service

1. On the project canvas click **New** (or **+ Create**) → **GitHub Repo** →
   pick **Smart-Jaggery-Marketplace**.
2. Open the new service → **Settings**:
   - **Root Directory** → `backend`
   - **Start Command** → `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
   - Rename the service to exactly **`backend`** (Settings → top of the page).
     The name matters — step 3 refers to it.
3. Go to the **Variables** tab and add:

   | Name            | Value                        |
   | --------------- | ---------------------------- |
   | `DATABASE_URL`  | `${{Postgres.DATABASE_URL}}` |
   | `JWT_SECRET`    | a long random string (below) |
   | `SEED_DEMO`     | `true`                       |

   Generate the secret with:

   ```bash
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. **Settings → Networking → Generate Domain.** This gives the backend a public
   address and, importantly, fills in its `RAILWAY_PUBLIC_DOMAIN` variable.

`SEED_DEMO=true` makes the app create its demo accounts on first boot, since a
fresh database has no users at all. It does nothing on later boots.

## 3. Add the frontend service

1. On the canvas click **New** → **GitHub Repo** → the **same** repo again.
2. Open it → **Settings**:
   - **Root Directory** → `frontend`
   - **Start Command** → `node server.js`
   - Rename the service to **`frontend`**.
3. **Variables** tab:

   | Name         | Value                                  |
   | ------------ | -------------------------------------- |
   | `API_BASE`   | `${{backend.RAILWAY_PUBLIC_DOMAIN}}`   |
   | `JWT_SECRET` | `${{backend.JWT_SECRET}}`              |
   | `NODE_ENV`   | `production`                           |

   `RAILWAY_PUBLIC_DOMAIN` is a bare hostname with no `https://` — the app adds
   the scheme itself, so this works as-is.

   `JWT_SECRET` **must** match the backend's, which the reference guarantees.
   `NODE_ENV=production` makes the login cookie `Secure` over HTTPS.

4. **Settings → Networking → Generate Domain.**

**That domain is your public website link** — something like
`https://frontend-production-xxxx.up.railway.app`.

## 4. First login

| Role      | Email                  | Password |
| --------- | ---------------------- | -------- |
| Admin     | admin@jaggery.local    | admin123 |
| Warehouse | staff@jaggery.local    | staff123 |
| Customer  | customer@jaggery.local | cust123  |

**Change the admin password immediately** — the site is public and these
passwords are in your public repository.

## Updating the live site

Push to GitHub and Railway redeploys automatically:

```bash
git add -A && git commit -m "my change" && git push
```

## Things to know about Railway

- **Free trial, then usage-based.** Railway gives new accounts a one-off trial
  credit; after that it bills for usage (a small project is typically a few
  dollars a month). Unlike Render there is no permanently-free tier, but also
  **no 15-minute sleep and no 30-day database deletion**.
- **Uploaded images vanish on redeploy** unless you attach a Volume
  (Service → Settings → **Volumes** → mount at
  `/app/uploads`). Images committed in `backend/uploads` always survive.
- **SMTP is allowed**, so real password-reset email can work here — set
  `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM` on the
  backend. Left unset, email stays in dry-run mode and the app works fine.

## If something goes wrong

- **Build failed** — open the service → **Deployments** → click the failed one
  → read the build log. The last red lines say why.
- **Website loads but every page errors** — `API_BASE` is wrong. Check the
  frontend's Variables tab shows `${{backend.RAILWAY_PUBLIC_DOMAIN}}` and that
  the backend service is really named `backend`.
- **Login works but signs you out immediately** — the two `JWT_SECRET` values
  differ. Re-check the frontend uses `${{backend.JWT_SECRET}}`.
- **Backend crashes on start** — confirm the Postgres service is running and
  `DATABASE_URL` is the reference `${{Postgres.DATABASE_URL}}`, not typed by hand.

## Still want Render instead?

`render.yaml` and [DEPLOY-RENDER.md](DEPLOY-RENDER.md) are still in this repo —
both platforms work, and nothing here breaks the Render setup.
