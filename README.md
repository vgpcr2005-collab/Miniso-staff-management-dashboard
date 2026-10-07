# MINISO Staff Performance & Incentive Management System

This is a Java desktop application for managing staff sales performance and incentive calculations in a retail environment.

## Features


## Run the project

From the project root:

```bash
javac -d out src/miniso/*.java
java -cp out miniso.MinisoApp
```

## Project idea

The application focuses on the problem of tracking individual staff performance and calculating incentives automatically instead of doing it manually.

The key formula used is:

Target Achievement = (Total Sales / Target) × 100

## Important note

The project is built using Java Swing, which is a standard Java GUI library suitable for desktop applications.
## MINISO Staff Performance Management System

A role-based browser application for staff sales, targets, performance, incentive approvals, and reports. The web app uses a local Python HTTP server and SQLite database; it runs without installing third-party packages.

## Start the application

1. Install Python 3.10 or newer.
2. Double-click `run.bat`, or run `python app_server.py` from this folder.
3. Open <http://localhost:8000> in a browser.

The SQLite database is created at `data/miniso.sqlite3` on first launch. Keep the server terminal open while using the website. The older Java Swing prototype is still under `src/miniso`; the browser application is the upgraded version.

## Local demo accounts

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `admin123` |
| Manager | `manager` | `manager123` |
| Staff | `harsha` | `staff123` |

Other sample staff accounts: `rahul`, `priya`, and `ankit`, each with password `staff123`.

These credentials are for a local demonstration only. Change/remove demo accounts and use HTTPS, secure cookie settings, and managed secrets before deploying to a network or public server.

## Role access

- **Admin:** manage staff accounts and daily targets, configure reward tiers, review team results and reports. Staff IDs are generated automatically.
- **Manager:** view the dashboard and leaderboard, approve incentives, generate and export reports.
- **Staff:** enter sales and view their own target, achievement, incentive, and performance history.

Permissions are enforced by the server for each data-changing or report request, not only by hiding page controls.

## Incentive calculation

Achievement is calculated as `(period sales / period target) × 100`. Period targets are calculated from each staff member's daily target multiplied by the calendar days in the selected month or quarter. The highest eligible rule provides the fixed reward for that reporting period. Default tiers are 70% → ₹500, 90% → ₹1,000, 100% → ₹2,000, 110% → ₹3,500, and 120% → ₹5,000.

Reports support calendar months and quarters. CSV is downloaded directly; PDF output uses the browser's print dialog, where **Save as PDF** is available.

## Database tables

`staff`, `targets`, `sales`, `incentive_rules`, and `incentive_approvals` are stored in SQLite. Staff passwords are stored as PBKDF2-HMAC-SHA256 hashes. Authenticated sessions use an HttpOnly, SameSite cookie.

## Java prototype

The original Swing classes remain in `src/miniso` and can still be compiled separately with `javac -d out src/miniso/*.java`. Its file-based storage is not used by the web app.
