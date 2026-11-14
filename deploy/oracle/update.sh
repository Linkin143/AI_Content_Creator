#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Git-based deploy: check out a ref into /opt/aevrix, reinstall deps, reinstall
# unit files, restart services. Run from a sudo-capable user.
#
#   sudo /opt/aevrix/deploy/oracle/update.sh            # update current branch
#   sudo /opt/aevrix/deploy/oracle/update.sh v1.2.0     # deploy a TAG (recommended)
#   sudo /opt/aevrix/deploy/oracle/update.sh main       # deploy a branch tip
#   sudo /opt/aevrix/deploy/oracle/update.sh <sha>      # deploy an exact commit
#
# The ref may be a tag, a branch, or a commit SHA — it is resolved accordingly.
# /opt/aevrix must be a git checkout (oracle_setup.sh clones it for you).
# Your .env, data/ and logs/ are untracked, so they are never touched.
# ---------------------------------------------------------------------------
set -euo pipefail
APP_USER="aevrix"
APP_DIR="/opt/aevrix"
REF="${1:-}"

cd "${APP_DIR}"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "ERROR: ${APP_DIR} is not a git checkout."
  echo "Re-provision with oracle_setup.sh <repo-url>, or 'git init' + set a remote."
  exit 1
fi

# Mark the dir safe for root running git on an aevrix-owned repo.
git config --global --add safe.directory "${APP_DIR}" 2>/dev/null || true
GIT=(sudo -u "${APP_USER}" git -C "${APP_DIR}")

echo "==> Fetching latest code (branches + tags)..."
"${GIT[@]}" fetch --prune --tags --force origin

if [[ -z "${REF}" ]]; then
  # No ref given: update the currently checked-out branch to its remote tip.
  REF="$(git -C "${APP_DIR}" rev-parse --abbrev-ref HEAD)"
  echo "==> No ref given; using current branch '${REF}'."
fi

# Resolve the ref to a concrete commit, preferring (in order):
#   remote branch origin/<REF>  ->  tag <REF>  ->  raw commit/ref <REF>
if git -C "${APP_DIR}" rev-parse --verify --quiet "refs/remotes/origin/${REF}^{commit}" >/dev/null; then
  TARGET="origin/${REF}"
  echo "==> Deploying branch '${REF}' (${TARGET})."
elif git -C "${APP_DIR}" rev-parse --verify --quiet "refs/tags/${REF}^{commit}" >/dev/null; then
  TARGET="refs/tags/${REF}"
  echo "==> Deploying tag '${REF}'."
elif git -C "${APP_DIR}" rev-parse --verify --quiet "${REF}^{commit}" >/dev/null; then
  TARGET="${REF}"
  echo "==> Deploying commit/ref '${REF}'."
else
  echo "ERROR: ref '${REF}' not found as a branch, tag, or commit on origin."
  exit 1
fi

echo "==> Checking out ${TARGET}..."
# Hard reset so local .sh mode/permission noise never blocks the checkout.
# (Detached HEAD on a tag/commit is expected and fine for deployment.)
"${GIT[@]}" checkout --quiet --force --detach "${TARGET}"
"${GIT[@]}" reset --hard "${TARGET}"
echo "==> Now at: $(git -C "${APP_DIR}" rev-parse --short HEAD)"

echo "==> Reinstalling dependencies..."
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -e "${APP_DIR}[providers]"

echo "==> Reinstalling systemd units (in case they changed)..."
sudo cp "${APP_DIR}/deploy/oracle/systemd/"*.service /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/oracle/systemd/"*.timer   /etc/systemd/system/ 2>/dev/null || true
sudo systemctl daemon-reload

echo "==> Restarting services..."
sudo systemctl restart aevrix-api aevrix-bot aevrix-scheduler aevrix-dashboard

echo "==> Done. Health check:"
sleep 2
curl -s http://127.0.0.1:8000/health || echo "(API not responding yet; check logs)"

