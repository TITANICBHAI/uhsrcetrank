#!/usr/bin/env bash
set -euo pipefail

readonly repository_url="https://github.com/TITANICBHAI/uhsr-cet-ranker-2026.git"
readonly branch="${GITHUB_BRANCH:-main}"
readonly remote_name="github"

if [[ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]]; then
  echo "GITHUB_PERSONAL_ACCESS_TOKEN is not configured in Replit Secrets." >&2
  exit 1
fi

git rev-parse --show-toplevel >/dev/null
git add -A

if git diff --cached --quiet; then
  echo "No workspace changes to commit."
else
  commit_message="${GITHUB_COMMIT_MESSAGE:-Sync workspace from Replit}"
  git commit -m "$commit_message"
fi

if git remote get-url "$remote_name" >/dev/null 2>&1; then
  git remote set-url "$remote_name" "$repository_url"
else
  git remote add "$remote_name" "$repository_url"
fi

askpass_file="$(mktemp)"
cleanup() {
  rm -f "$askpass_file"
}
trap cleanup EXIT
chmod 700 "$askpass_file"
cat > "$askpass_file" <<'ASKPASS'
#!/bin/sh
case "$1" in
  *Username*) printf '%s\n' "x-access-token" ;;
  *) printf '%s\n' "$GITHUB_PERSONAL_ACCESS_TOKEN" ;;
esac
ASKPASS

export GIT_ASKPASS="$askpass_file"
export GIT_TERMINAL_PROMPT=0
git push "$remote_name" "HEAD:$branch"
echo "Workspace pushed to $repository_url ($branch)."