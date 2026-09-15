# UHSR CET Rank Calculator 2026

This project is an independent candidate utility and is not affiliated with UHSR or the Department of Medical Education and Research, Government of Haryana.

## Preview

The configured `Start application` workflow serves the FastAPI backend and the static frontend together on port 5000:

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 5000
```

The public site intentionally starts with the calculator unavailable until a real dataset is imported, validated, reviewed, and published through the unlinked admin page.

## Push workflow

Use the `Push workspace to GitHub` workflow to commit and push the complete workspace to:

```text
https://github.com/TITANICBHAI/uhsr-cet-ranker-2026
```

The workflow reads `GITHUB_PERSONAL_ACCESS_TOKEN` from Replit Secrets. The token is never written to the Git remote URL, source files, or logs. The committed helper is `scripts/push_to_github.sh`; keeping that script in the repository makes the push action available after a future GitHub import.

Optional workflow variables:

- `GITHUB_BRANCH` — target branch, default `main`
- `GITHUB_COMMIT_MESSAGE` — commit message, default `Sync workspace from Replit`

## Cloudflare Pages deployment

The public frontend is intended for:

```text
https://uhsrcetresult.pages.dev
```

Cloudflare Pages serves only the files in `frontend/`. The FastAPI backend must be deployed separately; Cloudflare Pages will not run `backend/main.py`.

Deployment order:

1. Deploy `backend/` to a public HTTPS Python service using:
   `uvicorn main:app --host 0.0.0.0 --port $PORT`
2. Set backend environment values:
   `ADMIN_SECRET`, `DATABASE_URL`, and `ALLOWED_ORIGIN=https://uhsrcetresult.pages.dev`.
3. Copy the backend's public HTTPS URL into `frontend/js/config.js` as `apiBase`.
4. Push the frontend change to GitHub.
5. In Cloudflare: **Workers & Pages → Create application → Pages → Connect to Git → GitHub**, select `TITANICBHAI/uhsr-cet-ranker-2026`, and set:
   - Production branch: `main`
   - Build command: leave blank
   - Build output directory: `frontend`
6. Deploy. Cloudflare will provide `https://uhsrcetresult.pages.dev` if that project name is available. If it assigns another `pages.dev` name, use that actual URL in `frontend/sitemap.xml`, `frontend/robots.txt`, and `ALLOWED_ORIGIN`, then republish.

The first public deployment should remain in the unavailable state until a real dataset is imported and published through the protected admin workflow.