# Transferring the Customer Records project to another computer

This guide covers moving the project and running it on a new Windows computer
**without opening cmd or typing commands** (you just double-click scripts).

---

## What you MUST copy (the essentials)

Copy the **entire project folder** `customer\` — but you do **not** need the
virtual environment. To transfer efficiently, copy the following files/folders:

| Item                        | Why it's needed                                     |
|-----------------------------|-----------------------------------------------------|
| `manage.py`                 | Django's command runner                             |
| `config/`                   | Settings, URLs, WSGI/ASGI                           |
| `accounts/` `customers/` `documents/` `notifications/` `reports/` `salespersons/` `security_cheques/` `audit/` `templates/` `static/` `tests/` | All your application code |
| `requirements.txt`          | List of Python packages to install                  |
| `db.sqlite3`                | **Your database** (all your data lives here)        |
| `media/`                    | Uploaded logos, documents, images                   |
| `.env`                      | Environment settings (DEBUG, secret key, etc.)      |
| `setup.bat`                 | One-time installer for the new computer             |
| `start.bat` `start_virtual.bat` | Double-click launchers                          |

## What you should EXCLUDE (do not copy — they get rebuilt)

| Item            | Why it's excluded                                             |
|-----------------|---------------------------------------------------------------|
| `venv/`         | Virtual environment — machine-specific, rebuilt by `setup.bat`|
| `__pycache__/`  | Python bytecode cache — regenerated automatically             |
| `staticfiles/`  | Collected static files — regenerated                          |
| `.pytest_cache/` `.coverage` | Test artifacts — not needed for running               |

> **Tip:** The easiest transfer method is to **zip the whole `customer\` folder**
> (works fine even with venv inside, it's just larger) and copy + extract on the
> new machine. The `setup.bat` will recreate the venv cleanly.

---

## On the NEW computer — step by step (no cmd typing)

1. **Install Python** on the new computer (only once, if not already):
   - Download from https://www.python.org/downloads/
   - ✔ IMPORTANT: tick **"Add Python to PATH"** during installation.
   - Any recent 3.10+ version works.

2. **Copy** the project folder (the ZIP you made) onto the new computer and
   extract it.

3. **Double-click `setup.bat`** — this runs ONCE. It will:
   - Create the virtual environment (`venv/`)
   - Install all dependencies from `requirements.txt`
   - Run database migrations (adds any new columns, e.g. the logo field)

4. **Double-click `start.bat`** — this runs the server every time after that:
   - Opens a window showing "Server starting..."
   - Automatically applies any pending database migrations and **refreshes
     your "Expiry Alerts" tab** (so up-to-date expiry alerts appear).
   - Open your browser at `http://localhost:8000`
   - Press **Ctrl+C** in that window to stop the server.

> **Alternative:** `start_virtual.bat` runs the server in its own separate window
> so your current window stays free.

---

## Important notes

- **Python must be installed** on the new computer — Django is a Python app, so
  it can't run without the interpreter. There is no "one .exe" for Django.
- **Keep `db.sqlite3` and `media/`** with the code — otherwise you lose your data
  and uploaded files.
- If you ever move the project folder to a different path on the same machine,
  the launchers still work because they use `%~dp0` (their own location).
- To allow other devices on the same network to connect, the server runs on
  `0.0.0.0:8000`; use the host machine's LAN IP instead of `localhost` when
  connecting from another device (set `ALLOWED_HOSTS` in `.env` accordingly).
