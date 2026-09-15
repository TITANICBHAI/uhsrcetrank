---
name: Managed PostgreSQL runtime
description: Replit's managed DATABASE_URL may be PostgreSQL with sslmode query parameters.
---

When the runtime supplies DATABASE_URL as PostgreSQL, normalize it to SQLAlchemy's asyncpg driver and translate sslmode into an asyncpg-compatible SSL argument before creating the async engine.

**Why:** The imported requirements default to SQLite, but Replit can inject a managed PostgreSQL URL; passing its sslmode directly to asyncpg prevents application startup.

**How to apply:** Keep SQLite as the local default, but handle postgres:// and postgresql:// runtime URLs in the database engine setup.