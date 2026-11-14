#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Git-based deploy: pull latest code into /opt/aevrix, reinstall deps,
# reinstall unit files, restart services. Run from a sudo-capable user.
#
#   sudo /opt/aevrix/deploy/oracle/update.sh            # pull current branch
#   sudo /opt/aevrix/deploy/oracle/update.sh main       # pull a specific branch
#
# /opt/aevrix must be a git checkout (oracle_setup.sh clones it for you).
# Your .env, data/ and logs/ are untracked, so they are never touched.
# ---------------------------------------------------------------------------
set -euo pipefail
APP_USER="aevrix"
APP_DIR="/opt/aevrix"
BRANCH="${1:-}"

cd "${APP_DIR}"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "ERROR: ${APP_DIR} is not a git checkout."
  echo "Re-provision with oracle_setup.sh <repo-url>, or 'git init' + set a remote."
  exit 1
fi

# Mark the dir safe for root running git on an aevrix-owned repo.
git config --global --add safe.directory "${APP_DIR}" 2>/dev/null || true

echo "==> Fetching latest code..."
sudo -u "${APP_USER}" git -C "${APP_DIR}" fetch --prune origin
if [[ -n "${BRANCH}" ]]; then
  sudo -u "${APP_USER}" git -C "${APP_DIR}" checkout "${BRANCH}"
fi
CURRENT_BRANCH="$(git -C "${APP_DIR}" rev-parse --abbrev-ref HEAD)"
echo "==> Pulling origin/${CURRENT_BRANCH}..."
# Hard reset to remote so local .sh permission/mode noise never blocks a pull.
sudo -u "${APP_USER}" git -C "${APP_DIR}" reset --hard "origin/${CURRENT_BRANCH}"

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

