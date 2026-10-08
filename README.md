# MINISO Staff Performance Dashboard

This project contains one app: the pink MINISO staff dashboard in `web/`.
It is a browser-only demo. Accounts and dashboard data are stored in the
current browser and are not shared across devices or backed up on a server.

## Run locally

On Windows, double-click `run.bat`, then open <http://localhost:8000>.
Python 3 is needed only to serve the static files locally.

## Deploy to Render

The root `render.yaml` configures the project as a static site that publishes
`web/`. In Render, create or update a Blueprint from this repository and sync
the Blueprint. If the existing Python web service cannot change to a static
site, create the static site from the Blueprint and use its URL.

Register an account from the sign-in page. The dashboard's Reset Demo Data
button restores sample data in the current browser.
