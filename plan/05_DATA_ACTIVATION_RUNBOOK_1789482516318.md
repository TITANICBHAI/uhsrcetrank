# UHSR CET Rank Calculator 2026 — Data Activation Runbook

> Use this only after UHSR publishes the relevant 2026 source. The result must remain unavailable until every gate below passes.

## 1. Before touching the application

Create a private activation folder outside the public repository:

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
- page/document title;
- retrieval date and time;
- source file checksum;
- CET exam and academic year;
- whether the document is text-based or scanned;
- conversion tool and version;
- operator name;
- any official serial/order visible in the source.

Never upload an unverified source directly to the public dataset.

## 2. Convert the source

### Text PDF

Convert to Markdown while preserving page boundaries if possible. Keep the original PDF unchanged.

### Scanned PDF

Use an OCR workflow, then manually inspect representative pages. Do not assume OCR output is correct because it parses successfully.

### Conversion review

Inspect at least:

- first page;
- one middle page;
- last page;
- pages where headers repeat;
- pages containing unusual names, dates, categories, or missing values.

Save the conversion command and tool version in `notes/`.

## 3. Process and import one exam at a time

For each exam:

1. Select the exact CET exam and ranking mode.
2. Run the local exporter from `backend/`:

   ```bash
   python export_d1.py --exam bsc-nursing --input ../activation/converted/source.md \
     --output ../activation/reports/bsc-nursing.sql \
     --json-output ../activation/reports/bsc-nursing.json \
     --ranking-mode PRECOMPUTED --ranking-version UG-2026
   ```

3. Confirm the source reference, version, and notes in the generated report.
4. Preserve the validation JSON and inspect total rows, failures, warnings, and duplicates.
5. Stop if the exporter exits non-zero; it does not produce a safe production import for failed validation.
6. Apply `worker/schema.sql` to D1 and import the reviewed SQL with Wrangler.
7. Inspect the dataset through protected Worker admin actions.
8. Keep the dataset unpublished.

Never combine two exams into one dataset just because their tables look similar.

## 4. Resolve import issues

### Safe to resolve automatically

- repeated header rows;
- blank separator rows;
- exact duplicate rows;
- known whitespace artifacts.

### Requires operator review

- two different names or scores for one roll number;
- column shifts;
- unparseable dates;
- values outside expected ranges;
- missing ranking fields;
- unexplained row-count differences;
- candidate records appearing in multiple CET sections.

Do not “fix” a source value by intuition. Preserve the raw value and record the decision.

## 5. Determine the merit ordering

Use this priority:

1. If the published document includes an official merit serial/order or rank/position column, capture it and use precomputed published-order mode.
2. If the source includes an explicit rule, record the exact rule and its source page/section.
3. If neither exists, compare plausible configurable orderings against the published candidate sequence.
4. If the ordering cannot be established reliably, keep the calculator unavailable for that exam.

Do not treat the following as verified merely because they seem plausible:

```text
percentile descending → score descending → DOB
```

If a tie remains after documented criteria, do not break it with roll number and call that official. Use the configured tie policy and disclose uncertainty.

## 6. Verify

Run the verifier against the published roll-number sequence when available. Save:

- configuration version;
- criteria;
- position policy;
- exact-match count;
- agreement percentage;
- disagreements;
- missing/extra roll numbers;
- maximum position delta;
- operator notes.

A perfect numerical match still requires visual source inspection for truncation, duplicates, and page omissions.

## 7. Publish gate

Publish only when all are true:

- source provenance is recorded;
- the imported dataset is complete enough to use;
- conflicting duplicates are resolved;
- required ranking inputs are present;
- every candidate has a resolved merit position;
- ordering is published or verified;
- the public display fields have been reviewed;
- manual sample lookups match the source;
- an authorized operator approves the release.

Publishing is a public action. The admin panel must show a final summary before the publish request is made.

## 8. Public smoke test

Use a small list of known roll numbers from the source:

- one candidate near the beginning;
- one from the middle;
- one near the end;
- one with a tie or warning if applicable;
- one nonexistent roll number.

Check:

- the correct exam is enabled;
- result details match the source;
- position and candidates-ahead calculation are correct;
- dataset version is visible;
- the disclaimer is present when the algorithm is unverified;
- no admin diagnostics appear publicly;
- official-result link works;
 - browser print/save report matches the page and says unofficial.

## 9. Rollback

If the public result is wrong or the source is corrected:

1. Unpublish the active dataset or publish the corrected version.
2. Do not delete the old version until the incident is understood.
3. Record the incident, source version, and affected exam.
4. Re-run validation and smoke tests.
5. Publish only the corrected dataset.

If correctness is uncertain, the safe state is unavailable—not a guessed result.
