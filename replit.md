# UHSR CET Rank Calculator 2026

This project is an independent candidate utility and is not affiliated with UHSR or the Department of Medical Education and Research, Government of Haryana.

## Preview

The configured `Start application` workflow serves the FastAPI backend and the static frontend together on port 5000:

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 5000
```

The public site intentionally starts with the calculator unavailable until a real dataset is imported, validated, reviewed, and published through the unlinked admin page.

## Push workflow

Use the `Push workspace to GitHub` workflow to commit and push the complete workspace to:

```text
https://github.com/TITANICBHAI/uhsr-cet-ranker-2026
```

The workflow reads `GITHUB_PERSONAL_ACCESS_TOKEN` from Replit Secrets. The token is never written to the Git remote URL, source files, or logs. The committed helper is `scripts/push_to_github.sh`; keeping that script in the repository makes the push action available after a future GitHub import.

Optional workflow variables:

- `GITHUB_BRANCH` — target branch, default `main`
- `GITHUB_COMMIT_MESSAGE` — commit message, default `Sync workspace from Replit`