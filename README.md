# Smart Jaggery Mart

An online jaggery marketplace with three roles — **Admin**, **Warehouse
staff** and **Customer** — covering batches and stock, perishability and
expiry warnings, orders with pickup or delivery, promotions, subscriptions,
reviews and reporting. English and Burmese (မြန်မာ) interface.

| Part     | Stack                            | Port |
| -------- | -------------------------------- | ---- |
| Backend  | Python Flask + PostgreSQL (API)  | 5000 |
| Frontend | Node.js Express + EJS (website)  | 3000 |

## Put it online (free)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/SoeThuraNaing974/Smart-Jaggery-Marketplace)

Clicking the button opens Render with this repo already selected. It reads
[`render.yaml`](render.yaml) and creates the database, the API and the website
together. You will be asked to sign in to Render first (free, sign up with
GitHub).

Two things to know while it runs:

- When Render asks for **API_BASE**, type `x` — you cannot know the real value
  until the backend has deployed once.
- Afterwards, copy the **jaggery-backend** URL and paste it into the
  **smart-jaggery** service's `API_BASE` environment variable.

Full walkthrough, demo logins, free-plan limits and troubleshooting:
**[DEPLOY-RENDER.md](DEPLOY-RENDER.md)**

## Run it on your own PC

Double-click **`SETUP.bat`** once, then **`START.bat`** whenever you want the
site. Needs Python, Node.js and PostgreSQL installed first — see
[README-SETUP.txt](README-SETUP.txt).

## Demo logins

| Role      | Email                  | Password |
| --------- | ---------------------- | -------- |
| Admin     | admin@jaggery.local    | admin123 |
| Warehouse | staff@jaggery.local    | staff123 |
| Customer  | customer@jaggery.local | cust123  |

Change these before sharing a public link.
