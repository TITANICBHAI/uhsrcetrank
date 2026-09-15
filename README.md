# UHSR CET Rank Calculator 2026

An independent candidate utility for looking up UHSR CET 2026 records and displaying an **Estimated Merit Position** only after a real dataset has been imported, validated, and published.

This repository intentionally does **not** claim affiliation with UHSR, the Department of Medical Education and Research, or the Government of Haryana. It does not contain official imagery or real candidate data.

## Stack

- `frontend/` — plain HTML5, CSS3, and vanilla JavaScript; suitable for Cloudflare Pages
- `backend/` — local-only Python 3.12 importer, validation system, and reusable ranking engine
- `worker/` — Cloudflare Worker API and D1 schema for published data
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

## Cloudflare production path

Production does not depend on the old FastAPI service:

1. Apply `worker/schema.sql` to a Cloudflare D1 database.
2. Process and validate source Markdown locally:

   ```bash
   cd backend
   python export_d1.py --exam bsc-nursing --input ../source.md \
     --output ../worker/dataset.sql --json-output ../worker/dataset.json \
     --ranking-mode PRECOMPUTED --ranking-version UG-2026
   ```

   The exporter stops without writing SQL when validation fails. Review the JSON report and
   source before importing.
3. Import the generated SQL with Wrangler:

   ```bash
   cd worker
   npx wrangler d1 execute uhsr-cet-ranker --remote --file=dataset.sql
   ```

4. Publish the reviewed dataset using the protected admin API or a D1 operator workflow.
5. Deploy `worker/` with Wrangler and deploy `frontend/` as the Cloudflare Pages output.

The Worker only validates query parameters and performs indexed D1 reads. It never parses
the raw source file, ranks candidates during a lookup, or exposes D1 credentials.

## Deployment shape

Deploy `frontend/` as a static site at `https://uhsrcetresult.pages.dev` and `worker/` as the API. Set the Worker `ADMIN_SECRET` secret and `ALLOWED_ORIGIN=https://uhsrcetresult.pages.dev`; never commit either value. Set the Worker HTTPS URL as `apiBase` in `frontend/js/config.js` before the final frontend publish, or leave it empty when Pages and the API are routed under the same origin.

The GitHub Actions workflow runs on pushes and pull requests. It performs Python compilation and frontend integrity checks without needing a secret. The repository itself is published with the secure GitHub token workflow from the Replit workspace; the token is never written into this repository.

## Important data rule

The calculator must remain unavailable for an exam until its source provenance, import validation, ranking semantics, and manual smoke tests have been reviewed by an authorized operator. See `plan/05_DATA_ACTIVATION_RUNBOOK_1789482516318.md`. The first public deployment should remain unavailable until a real dataset is imported, validated, reviewed, and published.