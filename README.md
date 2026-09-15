# UHSR CET Rank Calculator 2026

An independent candidate utility for looking up UHSR CET 2026 records and displaying an **Estimated Merit Position** only after a real dataset has been imported, validated, and published.

This repository intentionally does **not** claim affiliation with UHSR, the Department of Medical Education and Research, or the Government of Haryana. It does not contain official imagery or real candidate data.

## Stack

- `frontend/` — plain HTML5, CSS3, and vanilla JavaScript; suitable for Cloudflare Pages
- `backend/` — Python 3.12, FastAPI, Pydantic, and SQLAlchemy; suitable for Railway
- `plan/` — the supplied planning pack and source notes

## Run locally

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export ADMIN_SECRET=local-development-secret
uvicorn main:app --reload
```

Serve the static frontend from another terminal:

```bash
python -m http.server 3000 --directory frontend
```

The public site starts in the truthful unavailable state. No synthetic dataset is bundled or exposed.

## Deployment shape

Deploy `frontend/` as a static site at `https://uhsrcetresult.pages.dev` and `backend/` as a separate FastAPI service. Set `ADMIN_SECRET`, `DATABASE_URL`, and `ALLOWED_ORIGIN=https://uhsrcetresult.pages.dev` in the backend host's secret/environment configuration. Never commit them. After the backend has a public HTTPS URL, set that URL as `apiBase` in `frontend/js/config.js` before the final frontend publish.

The GitHub Actions workflow runs on pushes and pull requests. It performs Python compilation and frontend integrity checks without needing a secret. The repository itself is published with the secure GitHub token workflow from the Replit workspace; the token is never written into this repository.

## Important data rule

The calculator must remain unavailable for an exam until its source provenance, import validation, ranking semantics, and manual smoke tests have been reviewed by an authorized operator. See `plan/05_DATA_ACTIVATION_RUNBOOK_1789482516318.md`.