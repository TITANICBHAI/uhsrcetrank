---
name: Cloudflare publishing safety
description: Durable rules for exporting ranked datasets into D1 without unsafe publication or unstable foreign keys.
---

The local export pipeline must fail closed when any candidate lacks a resolved merit position, including unresolved ranking ties. D1 imports should reference the inserted dataset through a stable value such as its source hash, not SQLite `last_insert_rowid()` across multiple candidate rows.

**Why:** Public lookup is intentionally read-only and cannot repair missing or inconsistent positions; a malformed import would otherwise make the public result misleading or break the candidates-above view.

**How to apply:** Keep parsing, ranking, and validation local. Only export/import datasets whose validation report passes, and use indexed `(dataset_id, normalized_roll_number)` and `(dataset_id, merit_position)` lookups in the Worker.