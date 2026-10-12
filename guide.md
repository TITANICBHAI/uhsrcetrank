# Reusable Runbook: Source Data to Verified Web Page

Use this guide when turning a source document or dataset into structured data and a related page in this project. It is intentionally independent of any particular filename, subject, column names, row count, filter, or ranking rule. Re-discover those details for every new request; never carry them over from a previous dataset.

## Core rules

- Follow the latest user request and use the supplied source material as evidence. Do not infer missing values or silently resolve conflicting source versions.
- Treat each source as new: identify its actual format, schema, terminology, filters, and ordering before writing extraction logic.
- Inspect only the relevant project files. Search for the closest existing page and read its implementation before adapting it.
- Honor explicit instructions about delegation. If the user says not to use subagents, work directly.
- Keep source extraction, transformation, verification, page rendering, and publishing as separate steps so each can be checked.
- Fail clearly on ambiguous or incomplete data. Do not publish a best guess.

## 1. Define the job and inspect the inputs

Before coding, record:

| Item | Value for this run |
| --- | --- |
| Source file(s), format, and version/date | |
| Requested output(s) and destination | |
| Exact inclusion and exclusion rules | |
| Source order, official rank, or other ordering rule | |
| Fields to retain, display, search, or sort | |
| Fields restricted from public output | |
| Existing page or component to follow | |
| Verification method and publishing target | |

Inspect the actual source, not just its filename or a previous agent's notes. For documents, check page or sheet count, repeated headers, merged or wrapped cells, rotations, footnotes, and whether pages are text-based or scanned. For multiple files, establish which one is authoritative and how overlapping or conflicting records should be handled. Ask the user only when an unresolved choice changes the data, ranking, privacy, or public behavior.

For a web page, search the project for the closest existing page, its data source, styles, scripts, navigation link, and relevant tests. Note its actual route, field labels, sorting and filtering behavior, pagination, responsive layout, and shared components. Avoid broad repository dumps; follow imports and references only as needed.

## 2. Specify the data contract before extraction

Create a mapping from each source field to the output schema. For every field, decide whether it is retained in the authoritative data, included in a public download, rendered on the page, searchable, sortable, or sensitive. Map from actual source headings and values; do not reuse old field names or assume similar labels have the same meaning.

Define the selection predicate precisely, including which source field it uses and how values are normalized. Distinguish current values from historical or previous-round values when the source contains both. Define tie-breaking and ordering explicitly. A source serial is not an official rank unless the source says it is.

Preserve meaningful source details:

- Keep identifiers as text when leading zeros or formatting matter.
- Do not turn blanks, unavailable values, or unknowns into zero or an invented category.
- Normalize only what the task requires, and document each transformation.
- Preserve original order unless the user or source specifies another order.
- Keep an auditable link from each output record to its source page, row, sheet, or stable identifier.

## 3. Extract efficiently and deterministically

Use a script for substantial or repetitive extraction rather than manually transcribing records. Make input and output locations explicit arguments or configuration. Keep source-specific field maps and filters separate from parsing mechanics where that makes the next run easier; do not build a large generic framework for a one-off task.

Choose a parser that fits the input:

- Structured documents: use table or cell geometry and account for wrapped values, repeated headers, and page boundaries.
- Scanned documents: use OCR only when needed, then validate OCR output against rendered pages.
- Spreadsheets: inspect every relevant sheet, header row, formula/value behavior, hidden rows, and merged cells.
- CSV, JSON, or other text data: validate encoding, delimiters, quoting, schema, and malformed records.

Process the source in a predictable order. Emit a concise run summary with source rows/pages examined, records accepted and rejected, duplicate keys, missing values, and any parse anomalies. Make unexpected row shapes, missing required values, broken sequences, and unknown filter values explicit errors; never silently skip them. Re-running the same command on the same inputs should produce the same output.

Write only the outputs the task needs. If a Markdown table or other human-readable export is requested, escape values correctly and generate it from the same normalized records as the website data rather than maintaining two manually edited copies.

## 4. Build or adapt the page

Follow the closest existing page's project conventions, but use the newly defined schema and requirements. Keep the data separate from presentation. Implement only the requested fields and interactions, with clear labels and usable empty, loading, error, and no-results states. Check keyboard use, semantic table or card markup, narrow screens, and the project's existing navigation pattern.

Treat all browser-delivered files as public. Hiding a field in a table, CSS, or JavaScript does **not** protect it if the full value is sent to the browser in JSON or another client asset. Keep restricted data out of public assets and public repositories unless the user has explicitly approved that exposure and it is appropriate to publish. Never put credentials or tokens in source files, generated data, logs, or documentation.

Do not invent a ranking, score, or official status from a display order. If a derived sort or summary is useful, label it as a derived browsing aid and explain its formula; preserve the official/source order separately.

## 5. Verify independently before publishing

Use two genuinely separate checks:

1. **Primary extraction:** produce the normalized output using the chosen parser and transformations.
2. **Independent audit:** read the original source again using a different extraction path or independent checks. Do not simply call the primary converter's parsing functions a second time.

Compare every selected record and every retained field, in order where order matters. Report the source location, record identifier, field, expected value, and extracted value for each mismatch. Do not waive discrepancies by changing the expected value without source evidence.

Also check the invariants relevant to this source:

- Counts before and after each filter, with a reason for excluded records.
- Duplicate or missing identifiers and any expected sequence gaps.
- Required fields, allowed categories, and type/format constraints.
- Summary totals independently derived from the source.
- Source order and any official ranking or tie-break rules.
- Boundary cases, wrapped or multi-page rows, and unusual values.

For visual documents, render and inspect representative pages from the beginning, middle, and end, plus any pages flagged by automated checks. Visual sampling complements the full record comparison; it does not replace it. For other formats, inspect representative records and known edge cases in the original application or source viewer.

Do not publish while unexplained mismatches remain. Report totals and the scope of the independent comparison so the result can be audited without relying on a vague “verified” claim.

## 6. Run the final project checks

After all edits are complete, perform one final verification pass:

- Regenerate outputs and confirm repeat runs are deterministic.
- Run the independent source comparison and applicable unit or schema tests.
- Run the language-specific syntax/build checks for changed files.
- Parse or validate generated HTML/data and confirm the page loads at its intended route.
- Check both desktop and mobile layouts when the page is responsive.
- Confirm each requested field is present or absent in the actual browser payload and rendered interface as intended.
- Review `git diff --check`, changed files, and the final summary counts.

Batch independent checks together. Avoid repeating a full extraction or PDF audit after unrelated documentation-only edits; rerun the checks affected by each change and repeat the full source audit before a data-changing publication.

## 7. Publish safely

Before publishing, review what will be public: repository visibility, generated data, Markdown exports, source attachments, and any sensitive fields. A field omitted from the page can still be exposed by a committed or browser-served data file. Get explicit direction when public exposure is unclear.

Use the project's existing authenticated publishing workflow. Read credentials only through the approved secrets mechanism; do not print, paste, or embed them. Do not change global Git identity just to make automation work. If commits need an identity, use a non-interactive identity scoped to the commit command, and make its attribution consequence clear. Disable terminal prompts so an unattended workflow fails clearly instead of asking for personal information.

After publishing:

1. Check the workflow log for the commit and successful push.
2. Confirm the intended branch's remote commit hash equals the local commit hash.
3. Confirm no unintended workspace changes remain.
4. State what was published, what was independently verified, and any source or privacy limitations.

## Efficiency checklist

1. Inventory the source and inspect the closest existing page.
2. Write the field map, exact filter, ordering rule, and privacy boundary before coding.
3. Build one deterministic extractor with explicit input/output settings and useful error messages.
4. Generate outputs once, then run an independent full-data comparison and targeted visual checks.
5. Implement the page from the actual project pattern and verify desktop/mobile behavior.
6. Run one consolidated final check, review the diff, and publish only after the data and visibility decisions are clear.
