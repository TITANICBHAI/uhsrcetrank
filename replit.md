# UHSR CET Rank Calculator 2026

This project is an independent candidate utility and is not affiliated with UHSR or the Department of Medical Education and Research, Government of Haryana.

## Preview

The configured `Start application` workflow serves the FastAPI backend and the static frontend together on port 5000:

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 5000
```

The local preview intentionally starts with the calculator unavailable until a real dataset is imported, validated, reviewed, and published. Use the local FastAPI compatibility admin flow for preview data; production uses `backend/export_d1.py`, Wrangler, and protected Worker actions.

## Push workflow

Use the `Push workspace to GitHub` workflow to commit and push the complete workspace to:

```text
https://github.com/TITANICBHAI/uhsrcetrank
```

The workflow reads `GITHUB_PERSONAL_ACCESS_TOKEN` from Replit Secrets. The token is never written to the Git remote URL, source files, or logs. The committed helper is `scripts/push_to_github.sh`; keeping that script in the repository makes the push action available after a future GitHub import.

Optional workflow variables:

- `GITHUB_BRANCH` — target branch, default `main`
- `GITHUB_COMMIT_MESSAGE` — commit message, default `Sync workspace from Replit`

## Cloudflare Pages + Worker + D1 deployment

The public frontend is intended for:

```text
https://uhsrcetresult.pages.dev
```

The reproducible data inputs are `source/cet-2026-ug-source.md` and
`source/cet-2026-ug-ranked.md`. Regenerate the browser dataset after editing
the source with:

```bash
python scripts/rank_markdown.py source/cet-2026-ug-source.md \
  --ranked-output source/cet-2026-ug-ranked.md \
  --frontend-output frontend/js/static-data.js \
  --public-output frontend/data/cet-2026-ug-ranked.md
```

See `CLOUDFLARE_DEPLOYMENT_GUIDE.md` for the complete Pages and optional
Worker + D1 deployment steps.

Cloudflare Pages serves only the files in `frontend/`. The production API is `worker/`, backed by Cloudflare D1. `backend/` is retained for local Markdown processing, validation, and the reusable ranking engine; production lookup does not depend on FastAPI.

Deployment order:

1. Create a D1 database, apply `worker/schema.sql`, and put its ID in `worker/wrangler.toml`.
2. Process source files locally with `cd backend && python export_d1.py ...`; import the generated SQL with Wrangler. The exporter blocks malformed or unsafe datasets.
3. Set the Worker `ADMIN_SECRET` secret and `ALLOWED_ORIGIN=https://uhsrcetresult.pages.dev`.
4. Deploy `worker/` with `npx wrangler deploy`.
5. Set the Worker public HTTPS URL in `frontend/js/config.js` as `apiBase`.
6. Push the frontend change to GitHub.
7. In Cloudflare: **Workers & Pages → Create application → Pages → Connect to Git → GitHub**, select `TITANICBHAI/uhsrcetrank`, and set:
   - Production branch: `main`
   - Build command: leave blank
   - Build output directory: `frontend`
8. Deploy. Cloudflare will provide `https://uhsrcetresult.pages.dev` if that project name is available. If it assigns another `pages.dev` name, use that actual URL in `frontend/sitemap.xml`, `frontend/robots.txt`, and `ALLOWED_ORIGIN`, then republish.

The first public deployment should remain in the unavailable state until a real dataset is imported, validated, reviewed, and published. Candidate lookup, nearby candidates, candidates-above pagination, and browser-side report printing are all implemented in the frontend/Worker boundary.