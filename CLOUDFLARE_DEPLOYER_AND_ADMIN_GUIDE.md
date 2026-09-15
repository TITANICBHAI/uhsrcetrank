# UHSR CET Rank Calculator
# Deployer, Publisher, and Admin Guide

This guide explains how to take this repository from an imported project to a
working Cloudflare Pages + Worker + D1 deployment, and how to safely prepare,
sort, review, publish, replace, and unpublish candidate datasets.

It is written for someone who is new to the Cloudflare dashboard.

## Read this first

This application has two different operating paths:

1. **Local preparation path**
   - The source PDF/Markdown is reviewed and converted locally.
   - The Python importer validates the data.
   - The Python ranking engine calculates or preserves merit positions.
   - A SQL file is generated for Cloudflare D1.

2. **Production Cloudflare path**
   - Cloudflare D1 stores the reviewed dataset.
   - The Cloudflare Worker serves the public API.
   - Cloudflare Pages serves the static website.
   - The Worker only serves records that have been explicitly published.

The production Worker does **not** parse Markdown and does **not** calculate a
candidate's position during a public lookup. Do not upload a raw PDF or
Markdown file to D1 and expect it to work. Always use the exporter first.

The public site is intentionally unavailable until a dataset is imported,
reviewed, and published. That is the safe default.

---

## 1. What each person can do

### Deployer

The deployer is responsible for the technical setup:

- connect the GitHub repository to Cloudflare Pages;
- create the Cloudflare D1 database;
- apply the database schema;
- configure the Worker database binding;
- deploy the Worker;
- add the Worker `ADMIN_SECRET`;
- configure the allowed frontend origin;
- set the frontend API URL;
- deploy or redeploy the Pages site;
- check that the public website and API are reachable.

The deployer should not publish candidate data without completing the data
review steps below.

### Publisher or data operator

The publisher is responsible for the dataset release:

- obtain the official source document;
- preserve the original source;
- convert it to Markdown without losing rows or columns;
- choose the correct CET examination;
- choose the correct ranking mode;
- run the importer and exporter;
- inspect the validation report;
- verify the ordering and sample records;
- import the generated SQL into D1;
- keep the new dataset unpublished while reviewing it;
- publish only after the release gate passes;
- perform public smoke tests.

### Admin

The admin controls the production dataset state:

- list imported datasets;
- view validation reports;
- publish a validated dataset;
- unpublish the active dataset;
- delete an unpublished dataset.

The admin does **not** manually edit individual candidate rows in the public
database. If a row or position is wrong, create a corrected source, generate a
new dataset, validate it, and publish the corrected version.

---

## 2. What is already in this repository

Important project locations:

| Path | Purpose |
| --- | --- |
| `frontend/` | Static Cloudflare Pages website |
| `frontend/js/config.js` | Public Worker URL configuration |
| `frontend/admin.html` | Admin page intended for the local FastAPI compatibility flow |
| `backend/` | Local importer, validator, ranking engine, and PDF/report code |
| `backend/export_d1.py` | Converts reviewed Markdown into a D1 SQL import |
| `worker/` | Cloudflare Worker API |
| `worker/schema.sql` | D1 schema |
| `worker/wrangler.toml` | Worker name, D1 binding, and allowed origin |
| `plan/05_DATA_ACTIVATION_RUNBOOK_1789482516318.md` | Detailed data review runbook |

The current production architecture is:

```text
Candidate browser
       |
       +--> Cloudflare Pages: frontend/
       |
       +--> Cloudflare Worker: /api/*
                              |
                              +--> Cloudflare D1
```

The current Worker admin API supports:

```text
GET    /admin/datasets
GET    /admin/datasets/{id}/validation
POST   /admin/datasets/{id}/publish
POST   /admin/datasets/{id}/unpublish
DELETE /admin/datasets/{id}
```

The production Worker does not currently provide a raw Markdown upload
endpoint. Production imports are performed with Wrangler and the generated
SQL file.

---

## 3. Requirements before deployment

You need:

- a Cloudflare account;
- permission to create Workers, Pages, and D1 resources;
- access to the GitHub repository;
- Node.js and npm;
- Wrangler, which is included as a development dependency in `worker/`;
- the project checked out locally;
- a real source dataset before publishing results.

Do not invent a dataset for testing production. The application should remain
unavailable until real data passes review.

### Install project dependencies locally

From the repository root:

```bash
cd worker
npm install
cd ../backend
python -m pip install -r requirements.txt
cd ..
```

If this environment is Replit, the Python and Node modules are already
declared in the project configuration, but the commands above are still useful
on a separate local computer.

### Log in to Cloudflare from Wrangler

Run:

```bash
cd worker
npx wrangler login
```

A browser window will open. Sign in to Cloudflare and approve Wrangler.
Return to the terminal after authorization succeeds.

Check the connection with:

```bash
npx wrangler whoami
```

Do not put an API token in this repository or in a command that will be saved
in shell history.

---

## 4. Prepare the candidate source before Cloudflare

Do this for one CET exam at a time. Never combine separate examinations into
one dataset.

### 4.1 Create a private activation folder

Keep original source files and review records outside the public frontend:

```text
activation/
├── originals/
├── converted/
├── reports/
├── verification/
└── notes/
```

Record:

- official source URL;
- document title;
- retrieval date and time;
- exam and academic year;
- original file checksum;
- whether the source is text-based or scanned;
- conversion or OCR tool and version;
- operator name;
- any official serial number, order, or rank column.

Do not upload the original PDF or a raw OCR file directly to the public site.

### 4.2 Convert the source to Markdown

The importer expects a Markdown table containing candidate records. Preserve:

- the table header;
- candidate rows;
- page boundaries when possible;
- official serial/order values;
- blank values where the source is blank;
- the original spelling of names and roll numbers.

For scanned documents, use OCR and manually inspect at least:

- the first page;
- a middle page;
- the last page;
- pages with repeated headers;
- pages containing unusual names, dates, categories, or missing values.

Never assume that a file is correct simply because it parses.

### 4.3 Decide how positions will be determined

Use this order of preference:

1. **Published source order**
   - Use this when the official source includes a merit serial, rank, or
     position column.
   - Every candidate must have a usable `published_order`.
   - This is the preferred production mode.

2. **Verified ranking rule**
   - Use this only when the source explicitly documents the ordering rule or
     the ordering has been verified against the complete published sequence.

3. **Do not publish**
   - If the ordering cannot be established reliably, keep that exam
     unavailable.

The current fallback ranking configuration is:

```text
percentile descending
score descending
date of birth ascending
```

That configuration is intentionally marked `UNVERIFIED` in the code. It must
not be presented as an official rank merely because it looks reasonable.

If a tie remains unresolved, the importer blocks publication rather than
inventing a position.

### 4.4 Generate and validate the D1 import

From the `backend/` directory, run a command like this:

```bash
cd backend
python export_d1.py \
  --exam bsc-nursing \
  --input ../activation/converted/bsc-nursing.md \
  --output ../activation/reports/bsc-nursing.sql \
  --json-output ../activation/reports/bsc-nursing.json \
  --year 2026 \
  --version 2026-bsc-nursing-v1 \
  --ranking-mode PRECOMPUTED \
  --ranking-version UG-2026 \
  --source-reference "Official source URL or document reference" \
  --notes "Reviewed by operator on YYYY-MM-DD"
```

Supported values for `--exam` are:

```text
bsc-nursing
bpt
paramedical
pb-bsc-nursing
msc-nursing
mpt
npcc
```

Use `PRECOMPUTED` only when every candidate has an official published order.
Use `ENGINE` only when the configured ranking criteria have been verified.

The exporter writes:

- a `.sql` file for D1;
- an optional `.json` validation and inspection report;
- a non-zero exit code and no SQL file when validation fails.

Inspect the JSON report before continuing. Look for:

- total candidate count;
- validation status;
- blocking errors;
- warnings;
- duplicate rows;
- malformed dates;
- missing ranking fields;
- unresolved ties;
- unexpected row-count differences.

Do not continue when the exporter exits non-zero.

---

## 5. Create the Cloudflare D1 database

You can do this from the dashboard or Wrangler. The dashboard is easier for a
first-time Cloudflare user.

### 5.1 Create D1 from the Cloudflare dashboard

1. Open [https://dash.cloudflare.com/](https://dash.cloudflare.com/).
2. Select the correct Cloudflare account.
3. In the left navigation, open **Workers & Pages**.
4. Find **D1**. Depending on the current dashboard layout, it may appear under
   the Workers & Pages resource list or under **Storage & Databases**.
5. Select **Create database**.
6. Enter this database name:

   ```text
   uhsr-cet-ranker
   ```

7. Create the database.
8. Open the new database and copy its **Database ID**.

Keep the database ID private from public website code. It belongs in
`worker/wrangler.toml`, not in `frontend/`.

### 5.2 Add the database ID to the Worker configuration

Open `worker/wrangler.toml` and replace:

```toml
database_id = "REPLACE_WITH_D1_DATABASE_ID"
```

with the real ID from the Cloudflare dashboard.

Do not change the binding name:

```toml
binding = "DB"
```

The Worker code expects the database to be available as `env.DB`.

### 5.3 Apply the schema

From the `worker/` directory:

```bash
cd worker
npx wrangler d1 execute uhsr-cet-ranker --remote --file=schema.sql
```

The `--remote` flag is important. Without it, Wrangler may operate against a
local development database instead of the production D1 database.

You should apply the schema once before importing the first dataset.

Verify that the tables exist:

```bash
npx wrangler d1 execute uhsr-cet-ranker --remote \
  --command="SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;"
```

You should see at least:

```text
candidates
datasets
```

---

## 6. Create and deploy the Cloudflare Worker

The Worker is the production API. It reads D1 and exposes public lookup routes
plus protected admin routes.

### 6.1 Deploy the Worker once

From `worker/`:

```bash
npx wrangler deploy
```

Wrangler will print a Worker URL similar to:

```text
https://uhsr-cet-ranker-api.<your-subdomain>.workers.dev
```

Save this URL. It becomes the frontend API base URL later.

### 6.2 Add the admin secret

The admin secret protects dataset listing, validation, publishing, unpublishing,
and deletion.

Using Wrangler:

```bash
npx wrangler secret put ADMIN_SECRET
```

When prompted, paste a long random secret. The value will not be shown back to
you.

Alternatively, use the dashboard:

1. Open **Workers & Pages**.
2. Select the Worker named `uhsr-cet-ranker-api`.
3. Open **Settings**.
4. Find **Variables and Secrets**.
5. Select **Add**.
6. Choose **Secret**.
7. Set the variable name to:

   ```text
   ADMIN_SECRET
   ```

8. Enter the secret value.
9. Select **Deploy**.

Never put this value in GitHub, `frontend/js/config.js`, a URL, or a Markdown
file.

### 6.3 Configure the allowed frontend origin

The Worker configuration currently contains:

```toml
[vars]
ALLOWED_ORIGIN = "https://uhsrcetresult.pages.dev"
```

Replace that value with the real Pages URL if Cloudflare assigns a different
hostname. For example:

```toml
[vars]
ALLOWED_ORIGIN = "https://your-pages-project.pages.dev"
```

After changing `wrangler.toml`, deploy again:

```bash
npx wrangler deploy
```

If you later attach a custom domain to Pages, use the final public domain as
`ALLOWED_ORIGIN` and redeploy the Worker.

---

## 7. Deploy the frontend to Cloudflare Pages

Cloudflare Pages serves the files in `frontend/`. There is no frontend build
framework in this project.

### 7.1 Connect GitHub to Pages

1. Open the Cloudflare dashboard.
2. Select **Workers & Pages**.
3. Select **Create application**.
4. Choose **Pages**.
5. Choose **Connect to Git**.
6. Choose **GitHub**.
7. Authorize Cloudflare if asked.
8. Select the repository for this project.
9. Select **Begin setup**.

Use these build settings:

| Setting | Value |
| --- | --- |
| Production branch | `main` |
| Root directory | repository root |
| Build command | `exit 0` |
| Build output directory | `frontend` |

If the dashboard allows the build command to be blank, `exit 0` is still safe
for this static project and makes the intent explicit.

10. Select **Save and Deploy**.
11. Wait for the first deployment to finish.
12. Open the assigned `pages.dev` URL.

At this point the page may load but API-backed lookup will not work until the
frontend API URL is configured.

### 7.2 Point the frontend at the Worker

Open:

```text
frontend/js/config.js
```

Change:

```javascript
apiBase: window.UHSR_API_BASE || "",
```

to the Worker URL:

```javascript
apiBase: window.UHSR_API_BASE || "https://uhsr-cet-ranker-api.<your-subdomain>.workers.dev",
```

Use the exact HTTPS URL printed by Wrangler. Do not add a trailing slash.

Commit and push this change to the production branch. Cloudflare Pages should
automatically create a new deployment:

```bash
git add frontend/js/config.js worker/wrangler.toml
git commit -m "Configure production Cloudflare API"
git push origin main
```

Open the new Pages deployment and test:

```text
https://your-pages-project.pages.dev/
https://your-pages-project.pages.dev/methodology.html
https://your-pages-project.pages.dev/faq.html
```

### 7.3 Optional custom domain

After the `pages.dev` site works:

1. Open the Pages project in Cloudflare.
2. Open **Custom domains**.
3. Select **Set up a custom domain**.
4. Enter the domain.
5. Follow Cloudflare's DNS instructions.
6. Wait for the certificate and domain status to become active.
7. Update `ALLOWED_ORIGIN` in `worker/wrangler.toml` to the custom HTTPS
   domain.
8. Redeploy the Worker.
9. Update `frontend/sitemap.xml` and `frontend/robots.txt` if they still
   reference the old Pages hostname.

---

## 8. Import a production dataset

The exporter creates an unpublished dataset. This is intentional.

From the repository's `worker/` directory:

```bash
npx wrangler d1 execute uhsr-cet-ranker --remote \
  --file=../activation/reports/bsc-nursing.sql
```

Verify the imported dataset:

```bash
npx wrangler d1 execute uhsr-cet-ranker --remote \
  --command="SELECT id, cet_exam, version, ranking_mode, ranking_algorithm_version, candidate_count, validation_status, is_published FROM datasets ORDER BY id DESC;"
```

The new row should have:

```text
is_published = 0
```

Check candidate count:

```bash
npx wrangler d1 execute uhsr-cet-ranker --remote \
  --command="SELECT dataset_id, COUNT(*) AS imported_candidates, MIN(merit_position) AS first_position, MAX(merit_position) AS last_position FROM candidates GROUP BY dataset_id ORDER BY dataset_id DESC;"
```

For a precomputed dataset, also check that positions are populated:

```bash
npx wrangler d1 execute uhsr-cet-ranker --remote \
  --command="SELECT COUNT(*) AS missing_positions FROM candidates WHERE dataset_id = <DATASET_ID> AND merit_position IS NULL;"
```

Replace `<DATASET_ID>` with the actual number. The expected result is zero.

Do not edit the generated SQL manually after validation. If something is
wrong, correct the source or importer inputs and generate a new SQL file.

---

## 9. Review and publish a dataset

### 9.1 Store the admin secret in the current terminal session

Use a hidden prompt so the secret is not displayed:

```bash
read -s CLOUDFLARE_ADMIN_SECRET
export CLOUDFLARE_ADMIN_SECRET
printf '\n'
```

Do not echo the variable and do not commit it.

### 9.2 List datasets through the protected Worker API

Replace `WORKER_URL` with the Worker URL:

```bash
curl -sS \
  -H "X-Admin-Secret: $CLOUDFLARE_ADMIN_SECRET" \
  "https://WORKER_URL/admin/datasets"
```

The response includes each dataset's ID, exam, version, candidate count,
validation status, and whether it is published.

You can also inspect these records in the Cloudflare D1 dashboard:

1. Open **Workers & Pages**.
2. Open **D1**.
3. Select `uhsr-cet-ranker`.
4. Open the **Console** or **Browse** view.
5. Run read-only SQL queries against `datasets` and `candidates`.

Use the Worker admin API for publish state changes so the application applies
its safety rules consistently.

### 9.3 View the validation report

```bash
curl -sS \
  -H "X-Admin-Secret: $CLOUDFLARE_ADMIN_SECRET" \
  "https://WORKER_URL/admin/datasets/DATASET_ID/validation"
```

Replace `DATASET_ID` with the imported dataset ID.

Do not publish if the report contains unresolved blocking errors. Warnings must
be understood and documented before publication.

### 9.4 Publish

Only publish after completing the release checklist in Section 10:

```bash
curl -sS -X POST \
  -H "X-Admin-Secret: $CLOUDFLARE_ADMIN_SECRET" \
  "https://WORKER_URL/admin/datasets/DATASET_ID/publish"
```

The Worker will:

1. verify that the dataset validation status is `PASS` or
   `PASS_WITH_WARNINGS`;
2. unpublish any older dataset for the same CET exam;
3. publish the selected dataset.

Publishing is public. Treat this request like a production release.

### 9.5 Confirm that the exam is now active

```bash
curl -sS "https://WORKER_URL/api/datasets/active"
```

The published exam should appear in the response.

Refresh the Pages website. The exam selector and search fields should now be
enabled for that exam.

---

## 10. Mandatory release checklist

Before publishing an exam, confirm all of the following:

- [ ] The source came from the intended official source.
- [ ] The original source is preserved privately.
- [ ] The source URL, date, checksum, and operator are recorded.
- [ ] The correct CET examination was selected.
- [ ] The correct academic year was selected.
- [ ] The candidate count is plausible.
- [ ] Duplicate roll numbers were reviewed.
- [ ] Conflicting duplicate records were resolved.
- [ ] Names, scores, dates, and categories were visually sampled.
- [ ] The first, middle, and last source pages were checked.
- [ ] Every candidate has a resolved merit position.
- [ ] The ordering is official or has been verified.
- [ ] Any warning in the validation report is understood.
- [ ] Three or more known roll numbers were checked manually.
- [ ] A nonexistent roll number returns `not_found`.
- [ ] The dataset is still unpublished before the final approval.
- [ ] An authorized operator approved the release.

If any item is uncertain, keep the dataset unpublished. An unavailable result is
safer than an invented result.

---

## 11. How sorting and arranging work

There is no general-purpose drag-and-drop sorting screen in the production
Cloudflare dashboard for this application. The order is created before import.

### Preferred: official published order

If the source includes an official serial or merit order:

1. Preserve that column in the Markdown source.
2. Ensure every row has a valid published order.
3. Export with `--ranking-mode PRECOMPUTED`.
4. Review the generated JSON report.
5. Import the generated SQL.
6. Confirm that `merit_position` follows the published order.

The exporter automatically treats a dataset as precomputed when all imported
rows contain a published order.

### Configured engine order

The code also supports an engine-based order using ranking criteria such as:

- percentile descending;
- score descending;
- date of birth ascending;
- date of birth descending;
- published order.

Do not select or describe an engine ranking as official unless the rule is
documented and verified against the source. The repository's current default
configuration is explicitly unverified.

### Correcting a sort or position

Do not directly update positions in D1 as a quick fix. Instead:

1. Identify the source or transformation error.
2. Correct the private Markdown conversion or importer input.
3. Generate a new `.sql` and `.json` report.
4. Review the new report.
5. Import the new SQL as a separate unpublished dataset.
6. Test the new dataset.
7. Publish the corrected dataset.

Publishing the corrected dataset automatically unpublishes the older dataset
for that same exam, while leaving the older row available for audit.

---

## 12. Updating, unpublishing, and deleting

### Publish a corrected version

This is the normal correction workflow:

1. Generate a new version, for example
   `2026-bsc-nursing-v2`.
2. Import it into D1.
3. Verify its candidate count and positions.
4. Review its validation report.
5. Publish the new dataset.

The Worker deactivates the previous dataset for the same exam during publish.

### Unpublish an exam

Use this when the public result is known to be wrong or the source has been
withdrawn:

```bash
curl -sS -X POST \
  -H "X-Admin-Secret: $CLOUDFLARE_ADMIN_SECRET" \
  "https://WORKER_URL/admin/datasets/DATASET_ID/unpublish"
```

After unpublishing, the frontend should return to the unavailable state for
that exam.

### Delete an imported dataset

Only unpublished datasets can be deleted:

```bash
curl -sS -X DELETE \
  -H "X-Admin-Secret: $CLOUDFLARE_ADMIN_SECRET" \
  "https://WORKER_URL/admin/datasets/DATASET_ID"
```

Do not delete an old published dataset immediately after replacing it. Keep it
until the correction is understood and the incident record is complete.

---

## 13. Public smoke test after publishing

Use the actual Pages URL and test:

1. Open the home page.
2. Confirm the correct exam appears in the selector.
3. Search for a candidate near the beginning of the source.
4. Search for a candidate from the middle.
5. Search for a candidate near the end.
6. Check the displayed position and candidates-ahead count.
7. Check the dataset version.
8. Check the ranking method and disclaimer.
9. Check nearby candidates.
10. Check candidates-above pagination.
11. Try a nonexistent roll number.
12. Try an invalid roll number.
13. Generate or print the unofficial report.
14. Confirm the official-result link works.
15. Confirm no admin diagnostics or secrets are visible.

Useful public API checks:

```bash
curl -sS "https://WORKER_URL/api/health"
curl -sS "https://WORKER_URL/api/datasets/active"
curl -sS "https://WORKER_URL/api/search?cet_exam=bsc-nursing&roll_no=KNOWN_ROLL_NUMBER"
```

Use only a known test roll number from the reviewed source.

---

## 14. Troubleshooting

### The website loads but says the result is unavailable

Check:

1. The dataset was imported into the remote D1 database.
2. `is_published` is `1`.
3. The exam value matches exactly, such as `bsc-nursing`.
4. The frontend `apiBase` points to the Worker URL.
5. The Worker can access the D1 binding.

### The admin API returns `401 Unauthorized`

Check:

- the header name is exactly `X-Admin-Secret`;
- the secret matches the Worker secret;
- the request is sent to the Worker URL, not the Pages URL;
- the Worker was redeployed after the secret was configured.

Never put the secret in the URL.

### Publishing returns `422`

The Worker is refusing to publish a dataset whose validation status is not
`PASS` or `PASS_WITH_WARNINGS`. View the validation report and regenerate the
dataset after fixing the source or ranking problem.

### The browser reports a CORS error

Check that `ALLOWED_ORIGIN` in `worker/wrangler.toml` exactly matches the
frontend origin:

```text
https://your-pages-project.pages.dev
```

Do not include a trailing slash. Redeploy the Worker after changing it.

### Pages deploys but shows a blank or incomplete site

Check the Pages build settings:

- build command: `exit 0`;
- build output directory: `frontend`;
- production branch: `main`;
- repository root is not incorrectly set to `frontend/` while also using
  `frontend` as the output directory.

### D1 says the table does not exist

Apply the schema to the remote database:

```bash
npx wrangler d1 execute uhsr-cet-ranker --remote --file=schema.sql
```

Then verify the tables with the query in Section 5.3.

### The importer reports unresolved ties

Do not resolve the tie by assigning a random roll-number order. Confirm the
official tie rule or keep the exam unavailable until the ordering can be
defended.

---

## 15. Security rules

- Never commit `ADMIN_SECRET`.
- Never put `ADMIN_SECRET` in frontend JavaScript.
- Never place secrets in GitHub Actions logs, URLs, screenshots, or issue
  comments.
- Treat candidate names, roll numbers, dates of birth, and scores as sensitive
  data.
- Give Cloudflare users only the permissions they need.
- Do not assume that `admin.html` is private because it has `noindex`.
  Authentication is enforced by the API, not by the page being hidden.
- Use HTTPS for Pages and Worker URLs.
- Keep private source documents and operator reports outside the public
  `frontend/` directory.
- Keep old datasets for audit until a correction is understood.
- If correctness is uncertain, unpublish rather than guessing.

---

## 16. Quick repeatable release procedure

For each new or corrected exam dataset:

```text
1. Obtain and preserve the official source.
2. Convert it to reviewed Markdown.
3. Decide PRECOMPUTED versus verified ENGINE ranking.
4. Run backend/export_d1.py.
5. Stop if validation fails.
6. Inspect the JSON report.
7. Import the generated SQL into remote D1.
8. Confirm the dataset is unpublished.
9. Check counts, positions, and sample records.
10. View the protected validation report.
11. Publish through the protected Worker endpoint.
12. Run public smoke tests.
13. Record the release decision and source version.
```

## Official Cloudflare references

Cloudflare changes dashboard labels periodically. If a button is not in the
same place, search the Cloudflare dashboard for the resource name.

- Pages Git integration:  
  https://developers.cloudflare.com/pages/get-started/git-integration/
- Pages build configuration:  
  https://developers.cloudflare.com/pages/configuration/build-configuration/
- D1 documentation:  
  https://developers.cloudflare.com/d1/
- Wrangler D1 commands:  
  https://developers.cloudflare.com/d1/wrangler-commands/
- Worker secrets:  
  https://developers.cloudflare.com/workers/configuration/secrets/
- Worker deployment:  
  https://developers.cloudflare.com/workers/wrangler/commands/workers/