# Cloudflare deployment guide

This project is a static GitHub Pages / Cloudflare Pages frontend backed by an
optional Cloudflare Worker and D1 database. The frontend already contains the
ranked dataset in `frontend/js/static-data.js`, so the public lookup works
without a backend API. The Markdown files are the source of truth for
regenerating it.

## 1. Regenerate the data from Markdown

The reviewed source is:

```text
source/cet-2026-ug-source.md
```

It contains the 18,967 rows in the order printed by the supplied PDF. To
rebuild the ranked Markdown and the browser dataset:

```bash
python scripts/rank_markdown.py \
  source/cet-2026-ug-source.md \
  --ranked-output source/cet-2026-ug-ranked.md \
  --frontend-output frontend/js/static-data.js \
  --public-output frontend/data/cet-2026-ug-ranked.md
```

The ranking is:

1. Percentage, descending
2. Marks, descending
3. Date of birth, descending (younger first)
4. Exact ties share a competition rank

`ABSENT` and `NE/UMC` remain in the Markdown source and are placed after
numeric results. The generated frontend data is intentionally compact and
contains no API credentials.

If a new PDF is received, first create the source Markdown:

```bash
python scripts/pdf_to_markdown.py \
  path/to/result.pdf \
  source/cet-2026-ug-source.md \
  --public-output frontend/data/cet-2026-ug-source.md
```

Then run the ranking command above and review both Markdown files before
publishing.

## 2. Publish the frontend on Cloudflare Pages

1. Push the repository to GitHub.
2. In Cloudflare, open **Workers & Pages → Create application → Pages →
   Connect to Git**.
3. Select this repository and use:
   - Production branch: `main`
   - Build command: leave blank
   - Build output directory: `frontend`
4. Deploy the site.
5. If Cloudflare assigns a URL different from the configured Pages URL, update
   `frontend/sitemap.xml`, `frontend/robots.txt`, and the Worker
   `ALLOWED_ORIGIN` value before the next deployment.

The static frontend does not need a secret or external service. It loads
`frontend/js/static-data.js` directly and searches the dataset in the browser.
The two Markdown files are also copied to `frontend/data/`, so they are
included in the Pages deployment for inspection and future reuse. The browser
uses the generated JavaScript bundle for fast, offline-safe lookup; changing
Markdown requires rerunning the generation command before publishing.

## 3. Optional Worker + D1 API deployment

Use this path when the dataset should be served from D1 instead of bundled in
the frontend.

Create a D1 database and replace the placeholder ID in
`worker/wrangler.toml`:

```bash
cd worker
npx wrangler d1 create uhsr-cet-ranker
npx wrangler d1 execute uhsr-cet-ranker --remote --file=schema.sql
```

Export the same Markdown source into a reviewed SQL file:

```bash
cd backend
python export_d1.py \
  --exam bsc-nursing \
  --input ../source/cet-2026-ug-source.md \
  --output ../worker/dataset.sql \
  --json-output ../worker/dataset.json \
  --ranking-mode ENGINE \
  --ranking-version UNVERIFIED-percentage-marks-younger-dob-2026 \
  --dob-order desc \
  --tie-policy allow \
  --source-reference source/cet-2026-ug-source.md
```

Review the JSON validation report. Do not import a file if validation fails.
After review:

```bash
cd ../worker
npx wrangler d1 execute uhsr-cet-ranker --remote --file=dataset.sql
npx wrangler secret put ADMIN_SECRET
npx wrangler deploy
```

Set the deployed Worker URL in `frontend/js/config.js` as `apiBase` if the
frontend and Worker use different origins. For a static-only deployment, leave
`apiBase` empty and keep the generated static dataset enabled.

## 4. GitHub Pages option

The repository includes `.github/workflows/pages.yml`. In GitHub:

1. Open **Settings → Pages**.
2. Set the source to **GitHub Actions**.
3. Push to `main`.

The workflow publishes the `frontend/` directory directly. This is separate
from Cloudflare Pages; choose one public frontend host and use its actual URL
in the sitemap, robots file, and Worker CORS setting.

## 5. Safety checks before going live

- Confirm the source row count is 18,967.
- Confirm the ranked Markdown begins with the highest Percentage.
- Confirm a younger candidate wins when Percentage and marks are equal.
- Confirm exact ties share a rank and the next rank skips correctly.
- Search a few roll numbers against the official PDF.
- Keep the official-result disclaimer visible.
- Never commit `ADMIN_SECRET` or any other secret.
