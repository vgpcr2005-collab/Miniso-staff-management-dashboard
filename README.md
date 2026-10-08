# MINISO Staff Performance Dashboard

This full-stack app combines the MINISO staff dashboard in `web/` with a
Python HTTP API and SQLite database. Staff, sales, targets, attendance, and
incentive rules are shared within a company. Company data is isolated from
other companies. Passwords are hashed on the server, and signed-in sessions
use an HttpOnly cookie.

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

Register an account from the sign-in page to create a company and its first
administrator. Existing accounts and their data are migrated into separate
companies on server startup. The Reset Demo Data button restores sample data
for the entire company, so it is available only to administrators and
managers. Administrators and managers can generate invitations from the Staff
Directory; managers can invite staff only. Staff accounts have read-only
access to company records and reports.

## Company accounts and API

Company and data routes require the same-origin session cookie.
`/api/register`, `/api/login`, `/api/logout`, and `/api/session` are the
authentication routes. An administrator or manager can create a one-time
invitation:

```http
POST /api/company/invitations
Content-Type: application/json

{"role":"staff","expiresInHours":24}
```

The response contains the invitation token; share it securely with the new
member because it is returned only once. Managers can invite staff only.
Registration with an invitation joins that company:

```json
{"name":"Alex Lee","username":"alex_lee","password":"at-least-eight-characters","inviteToken":"<token>"}
```

Without an invitation, registration creates a new company. Roles are
`admin`, `manager`, and `staff`: administrators and managers can edit data;
managers can invite staff; staff can view dashboard data and reports but
cannot change it.

The API also provides:

- `GET /api/company/members` and `GET /api/company/invitations` for
  administrators and managers.
- `GET /api/staff` and `GET /api/sales` to list company records.
- `POST /api/staff`, `PUT /api/staff/{id}`, and `DELETE /api/staff/{id}`.
- `POST /api/sales`, `PUT /api/sales/{id}`, and `DELETE /api/sales/{id}`.
- `GET /api/reports/monthly?month=YYYY-MM` for company sales, units, targets,
  achievement percentages, and incentives.

The existing `GET /api/state` and `PUT /api/state` endpoints remain available
for the dashboard. Staff deletion is rejected while sales, targets, or
attendance records refer to that staff member.
