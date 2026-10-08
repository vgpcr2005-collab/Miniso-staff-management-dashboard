# MINISO Staff Performance Dashboard

This full-stack app combines the MINISO staff dashboard in `web/` with a
Python HTTP API and SQLite database. Accounts, sales, targets, staff, and
incentive rules are stored on the server and are separated by account.
Passwords are hashed on the server, and signed-in sessions use an HttpOnly
cookie.

## Run locally

Install Python 3.10 or newer, then double-click `run.bat` and open
<http://localhost:8000>. The server uses only Python's standard library, so
there are no package installation steps. It creates
`data/miniso-dashboard.sqlite3` automatically; the database is excluded from
Git. Stop the server with Ctrl+C in its console.

## Deploy to Render

The root `render.yaml` configures a Python web service and a persistent disk
mounted at `/var/data`. In Render, create or update a Blueprint from this
repository and sync the Blueprint. Persistent disks require a paid Render
service. The database file is stored at `/var/data/miniso-dashboard.sqlite3`
so it survives service restarts and deploys.

Register an account from the sign-in page. Each new account starts with sample
dashboard data; the Reset Demo Data button restores those defaults for the
currently signed-in account. Accounts and records from the old browser-only
demo are not automatically imported; create a server account and re-enter any
data that needs to be kept.
