============================================================
  SMART JAGGERY MART - SETUP GUIDE
============================================================

An online jaggery marketplace with three roles:
Admin, Warehouse staff and Customer.

  Backend  : Python Flask + PostgreSQL  (API on port 5000)
  Frontend : Node.js Express + EJS      (website on port 3000)


------------------------------------------------------------
 1. INSTALL THESE FIRST (one time only)
------------------------------------------------------------

  * Python 3.11 or newer   https://www.python.org/downloads/
      - tick "Add python.exe to PATH" during installation

  * Node.js LTS            https://nodejs.org/

  * PostgreSQL 16          https://www.postgresql.org/download/windows/
      - remember the password you choose for the "postgres" user
      - the default port 5432 is fine


------------------------------------------------------------
 2. RUN THE SETUP (one time only)
------------------------------------------------------------

  Double-click:  SETUP.bat

  It checks the programs above, installs all packages,
  creates the "jaggery_db" database, writes the .env
  configuration files and loads the data.

  When asked, choose:
    1 = fresh demo data (recommended for a new machine)
    2 = restore the full backup (jaggery_db_backup.sql)

  It is safe to run SETUP.bat again if something fails.


------------------------------------------------------------
 3. RUN THE WEBSITE
------------------------------------------------------------

  Double-click:  START.bat

  Two windows open (Backend + Frontend), then the browser
  opens http://localhost:3000 automatically.

  To stop the website, close those two windows.


------------------------------------------------------------
 DEMO LOGINS (when you chose fresh demo data)
------------------------------------------------------------

  Admin     : admin@jaggery.local     /  admin123
  Warehouse : staff@jaggery.local     /  staff123
  Customer  : customer@jaggery.local  /  cust123


------------------------------------------------------------
 NOTES
------------------------------------------------------------

  * All configuration lives in backend\.env and frontend\.env
    (SETUP.bat creates them; .env.example shows the format).

  * Product images are stored in backend\uploads.

  * TO PUT THE SITE ONLINE (a real public link, free):
    see DEPLOY-RENDER.md - it walks through hosting the
    whole thing on render.com in about 10 minutes.

  * To share the site temporarily through a tunnel instead,
    download cloudflared.exe from
    https://github.com/cloudflare/cloudflared/releases
    and place it in this folder (it is not included in this
    package because of its size).

============================================================
