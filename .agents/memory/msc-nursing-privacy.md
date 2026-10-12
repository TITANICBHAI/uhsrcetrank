---
name: M.Sc. Nursing field visibility
description: The user's repeated visibility rule for DOB and qualifying-exam percentage in M.Sc. Nursing allotment data and pages.
---

For M.Sc. Nursing allotments, retain date of birth and qualifying-exam percentage in the underlying data, but do not show either field in rendered tables or cards.

**Why:** The user repeated this requirement for both Round 1 and Round 2.

**How to apply:** Preserve these fields when importing each round's source data, and check every user-facing M.Sc. Nursing view for accidental display. Static frontend JSON is downloadable by visitors; hiding fields in the UI does not make them private.
