# Hosting Smart Jaggery Mart on Render (free)

The whole site — PostgreSQL database, Flask API and Express website — deploys
from this repo's [render.yaml](render.yaml) blueprint. Total time: about 10
minutes, most of it waiting for builds.

## What you need

- A GitHub repo for this project — you already have one:
  <https://github.com/SoeThuraNaing974/Smart-Jaggery-Marketplace>
  (Step 0 below pushes the deploy setup to it.)
- A free account at <https://render.com> — click **Get Started**, sign up
  **with your GitHub account** (that also connects your repos).

## Step 0 — push the deploy setup to GitHub

Render builds from GitHub, so the hosting changes must be pushed first.

**Command 1** — stop tracking things that should never be in the repo. This
only removes them from git; **every file stays on your PC untouched**:

```bash
git rm -r --cached --ignore-unmatch frontend/node_modules backend/.env frontend/.env cloudflared.exe "backend/**/__pycache__"
```

**Command 2** — commit and push. This stages **only** the hosting files, so
any other work you have in progress is left alone:

```bash
git add .gitignore DEPLOY-RENDER.md README-SETUP.txt SETUP.bat START.bat render.yaml backend/app.py backend/seed.py frontend/lib/api.js frontend/package-lock.json && git commit -m "Make the project deployable on Render" && git push
```

Why command 1 matters: `cloudflared.exe` alone is 52 MB, and Render clones the
whole repo on every single deploy. Dropping it plus `node_modules` takes the
repo from 1741 tracked files to under 300, so builds start much faster.

## Deploy — step by step

1. In the Render dashboard click **New +** (top right) → **Blueprint**.

2. Find **Smart-Jaggery-Marketplace** in the repo list and click **Connect**.
   Render reads `render.yaml` and shows what it will create:
   `jaggery-db` (database), `jaggery-backend` (API), `smart-jaggery` (website).

3. Render asks for a value for **API_BASE** — you can't know it yet, so just
   type `x` and continue. Click **Apply / Deploy Blueprint** and wait until
   the services finish building (5–10 minutes; the database and backend must
   go green first).

4. Open the **jaggery-backend** service and copy its public URL from the top
   of the page — it looks like
   `https://jaggery-backend-xxxx.onrender.com`.

5. Open the **smart-jaggery** service → **Environment** tab → edit
   **API_BASE** → paste the backend URL → **Save Changes**.
   The frontend redeploys itself (about a minute).

6. Open the **smart-jaggery** service's own URL — for example
   `https://smart-jaggery-xxxx.onrender.com`. That's your live website. 🎉

## First login

The first boot seeded demo accounts (because `SEED_DEMO=true`):

| Role      | Email                  | Password |
| --------- | ---------------------- | -------- |
| Admin     | admin@jaggery.local    | admin123 |
| Warehouse | staff@jaggery.local    | staff123 |
| Customer  | customer@jaggery.local | cust123  |

**The site is public — log in as admin and change these passwords** if the
link will be shared beyond your demo.

## Updating the live site later

Just push to GitHub — Render redeploys automatically on every push to `main`:

```bash
git add -A && git commit -m "my change" && git push
```

## Security clean-up — please read before sharing the link

Your GitHub repo is **public**. Two things are currently exposed there.

### 1. Real user data in committed database backups

These tracked files contain **real email addresses and bcrypt password
hashes** (8–9 hashes, 6–7 real emails) and anyone can read them:

- `jaggery_db_backup.sql`
- `backend/uploads/backup_20260603_023050.sql`
- `backend/uploads/backup_20260606_200334.sql`
- `backend/uploads/backup_20260606_203051.sql`
- `backend/uploads/backup_before_clear.sql`

`.gitignore` now stops *future* app-generated backups from being committed,
but these are already in the repo **and in its history**, so removing them
now would not erase them. The realistic fixes, best first:

1. **Make the repo private** (instructions at the bottom of this section) —
   one click, removes public access to all of it.
2. If anyone else's real account is in there, tell them to change their
   password, since a hash can be attacked offline.

To at least stop them being in future commits:

```bash
git rm --cached backend/uploads/backup_*.sql
```

(`jaggery_db_backup.sql` is deliberately kept — `SETUP.bat` restores from it.)

### 2. The JWT secret

`backend/.env` was committed, so the JWT secret it contains (`64be4551…`) is
readable by anyone and stays in the history even after the Step 0 commit
stops tracking the file.

Your **hosted** site is not affected: Render generates its own fresh secret
(`generateValue: true` in `render.yaml`). Only your local setup uses the
exposed one. To retire it, generate a new secret and put the *same* value in
both local `.env` files:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the result as `JWT_SECRET=` in **both** `backend\.env` and
`frontend\.env` (they must match), then restart the app. You will be logged
out of your local site once — log back in and you are done.

### 3. Making the repo private (fixes both at once)

Because both problems also live in the git *history*, the simplest complete
fix is to stop the repo being public:

GitHub → your repo → **Settings** → **General** → scroll to the bottom →
**Change repository visibility** → **Make private**.

Render still builds and deploys private repos on the free plan, so your live
site keeps working exactly the same.

## Free-plan facts (important!)

- **Sleep:** after 15 minutes with no visitors a service goes to sleep; the
  next visitor waits ~1 minute while it wakes up. **Open the site a few
  minutes before you present it.**
- **Database expiry:** the free PostgreSQL database is **deleted 30 days
  after creation** (you get a 14-day grace period to upgrade). Before demo
  day, either recreate it fresh, or export your data (the admin backup page
  in the app can download a SQL backup), or upgrade the db to a paid plan.
- **Uploads:** images uploaded on the live site disappear on the next
  deploy/restart. Images committed in `backend/uploads` always survive.
  A permanent disk needs the paid plan (see the note in `render.yaml`).
- **Email:** Render's free plan blocks SMTP ports, so password-reset /
  notification emails stay in dry-run mode (the app handles this fine).

## If something goes wrong

- **Backend shows "Deploy failed"** — open the service → **Logs** tab; the
  last red lines say why. Most common: database not ready yet → click
  **Manual Deploy → Deploy latest commit** to retry.
- **Website loads but every page errors** — API_BASE is wrong. Re-check
  step 4–5: it must be the *backend* service's URL.
- **Login works but kicks you out** — the two services have different
  JWT_SECRET values. Blueprint deploys set it automatically; if you created
  services by hand, copy the backend's JWT_SECRET to the frontend.
