# GitHub Pages phone test

The Pages workflow is `.github/workflows/dashboard-pages.yml`. It builds only
the dashboard static assets, not backend code or local configuration.

## Backend prerequisite

Phone browsers connect directly to Modal. The prepared backend accepts a separate
DASHBOARD_TOKEN for GET /v1/dashboard/sessions and enables GET/Authorization CORS
for https://noahbkivel.github.io. The key cannot POST Mod events. The Mod's existing
token and localhost proxy continue to work as before.

Creation of the persistent read-only key was blocked by automatic approval review.
Explicit user approval is required before the agent can create Modal Secret
vision-dashboard-read and redeploy the backend. That step is NOT complete yet.
Do not redeploy this prepared backend until the Secret exists. No production
access was changed by the blocked attempt; the existing deployed API still works.

After approval, the key is saved only in ignored Noah/backend/dashboard-access.local.json
and Modal Secret vision-dashboard-read. It is never placed in the repo, Pages
build, workflow variables, URL, or browser request to GitHub. The hosted app asks
for it at first open and remembers it for that tab via sessionStorage. Wrong key:
reload and try again. Closing the tab may require entering it again.

## Enable Pages

1. Open https://github.com/NoahBKivel/HackBU-NoahDavid/settings/pages .
2. Under Build and deployment, set Source to GitHub Actions.
3. No template or branch folder is needed; the workflow is already in the repo.
4. Open the repository Actions tab and choose Deploy VISION dashboard.
5. Click Run workflow, select main, then Run workflow. Wait for the green check.
6. Open https://noahbkivel.github.io/HackBU-NoahDavid/ on your phone.
7. Paste the read-only dashboard key when prompted. Live data appears after the
   initial backend read, then updates about once per second.

No laptop/localhost server is needed for the hosted site. The Mod must still be
running and configured to send events to Modal. Browsing does not invoke inference.
Future dashboard pushes to main trigger the workflow automatically. The first
push can fail while Pages is disabled; rerun the workflow after enabling Pages.

Troubleshooting: a site 404 usually means deployment is not complete or the URL
is missing /HackBU-NoahDavid/. Access-key rejection requires the read-only key,
not a GitHub token. Connection unavailable means check the backend prerequisite,
Pages origin/CORS, deployment and network. ?preview=1 displays synthetic samples
only; omit it for the real Mod data.

Source: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
