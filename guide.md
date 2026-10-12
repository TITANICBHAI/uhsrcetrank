# Round 2 Nursing Allotments: Source, Extraction, Verification, and Publishing Guide

This guide records how the CET-2026 Round 2 B.Sc. Nursing allotment browser and its data were prepared, how to reproduce the extraction, and how the published files were checked.

## 1. Context used

No subagents were used. The work was based on the project files and the attached source PDF:

- `attached_assets/264_1791820346097.pdf` — the supplied 214-page provisional Round 2 allotment PDF.
- `frontend/nursing-allotments.html`, `frontend/js/nursing-allotments.js`, `frontend/css/nursing-allotments.css`, and `frontend/data/bsc-nursing-allotments-2026-27.json` — the existing Round 1 browser. These provided the established college picker, search and score filters, pagination, mobile-card pattern, and optional college ordering.
- `README.md`, `replit.md`, `.replit`, and `scripts/push_to_github.sh` — project run, dependency, and GitHub push instructions.

The PDF identifies the Department of Medical Education and Research, Haryana, and describes a provisional UG seat-allotment list after grievance redressal for CET-2026, Round 2, dated **12.10.2026**. It contains **3,390** candidate rows, printed source serials 1–3,390, and 14 columns:

1. Source serial
2. CET roll number
3. CET score
4. Qualifying-exam percentage
5. Date of birth
6. Candidate name
7. Previous-round institute
8. Previous-round course
9. Previous-round category
10. Previous-round remark
11. Round 2 allotted institute
12. Round 2 allotted course
13. Round 2 allotted category
14. Round 2 remark

The source serial is the serial printed in the PDF. It is not recalculated or described as a merit rank.

## 2. Set up the local Python environment

The converter uses PyMuPDF. The independent comparison uses `pdfplumber`; both are covered by the backend requirements.

```bash
uv venv .venv --python python3.12
uv pip install --python .venv/bin/python -r backend/requirements.txt
```

Use `.venv/bin/python` for the commands below. The source PDF is in `attached_assets/`, which is ignored by Git and is not uploaded by the push workflow.

## 3. Inspect the PDF layout

The PDF pages are A4 and rotated 90 degrees. The rows are ruled tables rather than a plain paragraph list, and institute/remark values can wrap across lines.

The extraction process rendered and visually checked representative pages at the beginning, middle, and end of the document. The converter can reproduce those review samples:

```bash
.venv/bin/python scripts/convert_nursing_round2.py \
  attached_assets/264_1791820346097.pdf \
  --render-samples .agents/outputs/nursing-round2
```

The run creates rendered page images and extracted page text in the specified review directory. Remove that generated directory after inspection if the images are no longer needed.

## 4. Extract and filter the records

Run the geometry-aware extractor to create both the Markdown source table and the website JSON:

```bash
.venv/bin/python scripts/convert_nursing_round2.py \
  attached_assets/264_1791820346097.pdf \
  --markdown source/nursing-round2-allotments-2026-27.md \
  --json frontend/data/nursing-round2-allotments-2026-27.json
```

The extractor works page by page:

1. It reads the PDF’s ruled-cell geometry and deduplicates identical cell rectangles.
2. It locates the repeated serial-number row band, groups its 14 cells, and assigns words to cells by word-center coordinates.
3. It reads the publication date from the first page.
4. It fails rather than writing outputs if it cannot identify 14 cells, validate the date, find required values, or confirm the full uninterrupted serial sequence.
5. It filters on the **final Round 2 “Allotted Course”** value, after whitespace normalization and case folding. Only `B.Sc. Nursing` records are retained; a candidate’s previous course does not determine inclusion.
6. It builds and checks both outputs before writing them.

The 14 fields are retained in both the Markdown records and the JSON records, including DOB and qualifying-exam percentage. The resulting dataset has **2,886** nursing candidates across **62** colleges. CET scores range from **45 to 161**. The Round 2 remark totals are 2,587 `Allotted`, 217 `No Change`, and 82 `Upgraded`.

## 5. What the Round 2 page shows

The browser is `frontend/nursing-round2-allotments.html`, linked from the home page and the Round 1 page. Its logic is in `frontend/js/nursing-round2-allotments.js`; its specific styles are in `frontend/css/nursing-round2-allotments.css`, layered over the shared allotment styles.

The desktop table has 11 visible columns: source serial; candidate and roll number; CET score; previous institute, course, category, and remark; Round 2 institute, course, category, and remark. On narrow screens, the same fields are shown as candidate cards. Neither layout renders DOB or qualifying-exam percentage.

The page provides:

- College search and alphabetical ordering.
- An optional high-score college ordering: sum CET scores **above 140**; if a college has no score above 140, use the sum of its five highest scores. Ties are resolved by the count above 140 and then college name.
- Candidate-name or roll-number search within the selected college.
- Minimum and maximum CET score filters.
- Page sizes of 25, 50, or 100 and previous/next pagination.
- Reset of the college and candidate filters.

Each selected college’s candidate rows are displayed in ascending source-serial order. The high-score ordering is a browsing aid only; it is not an official counselling rank, seat count, or preference order. The page also identifies itself as an independent reference view, not an official admissions portal.

### Public-data note

The page hides DOB and qualifying-exam percentage only in its rendered interface. The static JSON and source Markdown still contain those fields. Since the JSON is served from `frontend/data/` and the GitHub repository is public, the values are retrievable by visitors. The owner explicitly chose to push the files as-is after being informed of this.

## 6. Double verification

The second check is deliberately separate from the converter. The converter uses PyMuPDF cell rectangles; `scripts/verify_nursing_round2_pdf.py` uses `pdfplumber` table extraction instead.

Run it against the original PDF and the generated JSON:

```bash
.venv/bin/python scripts/verify_nursing_round2_pdf.py \
  attached_assets/264_1791820346097.pdf \
  frontend/data/nursing-round2-allotments-2026-27.json
```

The verification script:

1. Extracts exactly one 14-column table from each PDF page.
2. Confirms the 3,390 extracted source serials are continuous from 1 through 3,390.
3. Applies the same final-course filter to the independently extracted PDF rows.
4. Compares the resulting nursing rows to the JSON, in source order, across every field—including DOB and qualifying-exam percentage.
5. Stops with a page, serial, and field-specific mismatch if any value differs.

For this dataset, the independent extraction matched all **2,886 records and all 14 fields**. Pages 1, 108, and 214 were also rendered from the PDF and visually checked to review the beginning, middle, and ending rows.

Additional checks used for the page and files:

```bash
.venv/bin/python -m py_compile \
  scripts/convert_nursing_round2.py \
  scripts/verify_nursing_round2_pdf.py
node --check frontend/js/nursing-round2-allotments.js
```

The HTML was parsed, Markdown and JSON record counts were checked, and the page was opened in the running application at `/nursing-round2-allotments.html` on desktop and mobile. The application workflow serves the frontend and FastAPI together on port 5000.

## 7. Push the workspace to GitHub

The configured `Push workspace to GitHub` workflow runs `scripts/push_to_github.sh`. The script stages workspace changes, commits them if needed, sets the `github` remote to `https://github.com/TITANICBHAI/uhsrcetrank.git`, and pushes `HEAD` to `GITHUB_BRANCH` (default `main`).

The script checks `GITHUB_PERSONAL_ACCESS_TOKEN` from Replit Secrets and passes it through a temporary Git askpass helper. It supplies a generic `Replit Workspace` author identity for that commit command only, disables commit signing, and disables interactive terminal prompts; it does not ask for or change the user's global Git name or email. The token is not placed in the remote URL, source files, or command output. Do not paste the token into this guide or any repository file.

To publish a verified change:

1. Run the converter if the source or dataset changed.
2. Run the independent PDF comparison and resolve any mismatch before proceeding.
3. Review `git status --short` and confirm the intended files are being published.
4. Confirm the data’s destination and visibility. The target repository is public; the Round 2 JSON and Markdown include DOB and qualifying-exam percentage.
5. Start the existing **Push workspace to GitHub** workflow.
6. Check the workflow log for a successful push, then compare the local commit hash with `main` on GitHub.
