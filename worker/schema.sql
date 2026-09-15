-- Cloudflare D1 schema for the published UHSR CET datasets.
-- Heavy parsing and ranking happen locally before this schema is populated.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS datasets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cet_exam TEXT NOT NULL,
  academic_year TEXT NOT NULL DEFAULT '2026',
  display_name TEXT NOT NULL,
  version TEXT NOT NULL,
  ranking_mode TEXT NOT NULL CHECK (ranking_mode IN ('PRECOMPUTED', 'ENGINE')),
  ranking_algorithm_version TEXT NOT NULL,
  ranking_criteria_json TEXT NOT NULL DEFAULT '[]',
  candidate_count INTEGER NOT NULL DEFAULT 0,
  source_type TEXT NOT NULL DEFAULT 'MARKDOWN',
  source_reference TEXT,
  source_sha256 TEXT,
  validation_status TEXT NOT NULL DEFAULT 'PASS',
  validation_report_json TEXT NOT NULL DEFAULT '{}',
  is_published INTEGER NOT NULL DEFAULT 0 CHECK (is_published IN (0, 1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  processed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  published_at TEXT,
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_datasets_exam_published
  ON datasets (cet_exam, is_published, id DESC);

CREATE TABLE IF NOT EXISTS candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  dataset_id INTEGER NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  merit_position INTEGER,
  roll_number TEXT NOT NULL,
  normalized_roll_number TEXT NOT NULL,
  cet_exam TEXT NOT NULL,
  name TEXT,
  cet_score REAL,
  percentile REAL,
  dob TEXT,
  category TEXT,
  course TEXT,
  published_order INTEGER,
  tie_break_used TEXT,
  extra_fields_json TEXT NOT NULL DEFAULT '{}',
  UNIQUE (dataset_id, normalized_roll_number)
);

CREATE INDEX IF NOT EXISTS idx_candidates_dataset_roll
  ON candidates (dataset_id, normalized_roll_number);

CREATE INDEX IF NOT EXISTS idx_candidates_dataset_position
  ON candidates (dataset_id, merit_position);