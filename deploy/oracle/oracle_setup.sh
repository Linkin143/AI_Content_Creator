#!/usr/bin/env bash
# ===========================================================================
# AEVRIX Content Intelligence Engine - Oracle Cloud Always Free provisioner
#
# Target OS: Ubuntu 22.04 / 24.04 (ARM Ampere A1 or AMD micro).
# Run as a sudo-capable user (the default `ubuntu` user), NOT as root.
#
# GIT-BASED DEPLOY (recommended) — pass your repo URL; it clones to /opt/aevrix:
#     chmod +x deploy/oracle/oracle_setup.sh
#     ./deploy/oracle/oracle_setup.sh https://github.com/<you>/<repo>.git [branch]
#
# LOCAL DEPLOY — run it from inside an already-present checkout with no URL arg;
# it rsyncs the current tree to /opt/aevrix instead of cloning.
#
# Idempotent: safe to re-run (git pulls if /opt/aevrix is already a checkout).
#   1. Install system packages (Python 3.12, git, sqlite3, Caddy).
#   2. Create a locked-down `aevrix` service user.
#   3. Clone (or rsync) the app to /opt/aevrix and build a venv.
#   4. Install + enable systemd services + the daily backup timer.
#   5. Open the host firewall (ufw) for 80/443.
#
# AFTER running: edit /opt/aevrix/.env, edit the Caddyfile domain, then:
#     sudo systemctl restart aevrix-api aevrix-bot aevrix-scheduler aevrix-dashboard
#     sudo systemctl reload caddy
# Later updates are a one-liner:  sudo /opt/aevrix/deploy/oracle/update.sh
# ===========================================================================
set -euo pipefail

APP_USER="aevrix"
APP_DIR="/opt/aevrix"
REPO_URL="${1:-}"
BRANCH="${2:-}"
# Directory this script lives in (…/deploy/oracle) and the repo root above it.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ -n "${REPO_URL}" ]]; then
  echo "==> Git-based deploy from: ${REPO_URL} ${BRANCH:+(branch ${BRANCH})}"
else
  echo "==> Local deploy from checkout at: ${REPO_ROOT}"
fi

echo "==> [1/6] Installing system packages..."
sudo apt-get update -y
sudo apt-get install -y \
    python3.12 python3.12-venv python3.12-dev \
    build-essential git sqlite3 curl ufw ca-certificates \
    debian-keyring debian-archive-keyring apt-transport-https

# --- Caddy (automatic HTTPS reverse proxy) --------------------------------
if ! command -v caddy >/dev/null 2>&1; then
  echo "==> Installing Caddy..."
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
      | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
      | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y
  sudo apt-get install -y caddy
fi

echo "==> [2/6] Creating service user '${APP_USER}'..."
if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin "${APP_USER}"
fi

echo "==> [3/6] Placing app at ${APP_DIR}..."
sudo mkdir -p "${APP_DIR}"
# Allow root to run git in a repo owned by ${APP_USER} without "dubious ownership".
sudo git config --global --add safe.directory "${APP_DIR}" 2>/dev/null || true

if [[ -n "${REPO_URL}" ]]; then
  # ---- Git-based deploy ---------------------------------------------------
  if [[ -d "${APP_DIR}/.git" ]]; then
    echo "    Existing checkout found; fetching + resetting to remote."
    sudo -u "${APP_USER}" git -C "${APP_DIR}" remote set-url origin "${REPO_URL}"
    sudo -u "${APP_USER}" git -C "${APP_DIR}" fetch --prune origin
    TARGET_BRANCH="${BRANCH:-$(git -C "${APP_DIR}" rev-parse --abbrev-ref HEAD)}"
    sudo -u "${APP_USER}" git -C "${APP_DIR}" checkout "${TARGET_BRANCH}"
    sudo -u "${APP_USER}" git -C "${APP_DIR}" reset --hard "origin/${TARGET_BRANCH}"
  else
    echo "    Cloning fresh into ${APP_DIR}."
    # Clone as the service user so it owns the working tree.
    sudo chown "${APP_USER}:${APP_USER}" "${APP_DIR}"
    sudo -u "${APP_USER}" git clone ${BRANCH:+--branch "${BRANCH}"} \
        "${REPO_URL}" "${APP_DIR}"
  fi
else
  # ---- Local deploy (rsync current checkout) ------------------------------
  echo "    No repo URL given; rsyncing local tree (no git pulls later)."
  sudo rsync -a --delete \
      --exclude '.venv' \
      --exclude '__pycache__' \
      --exclude '.pytest_cache' \
      --exclude '.ruff_cache' \
      --exclude '.git' \
      --exclude 'logs/*' \
      --exclude 'data/*' \
      "${REPO_ROOT}/" "${APP_DIR}/"
fi

# Never overwrite live data/logs; ensure they exist.
sudo mkdir -p "${APP_DIR}/data" "${APP_DIR}/data/backups" "${APP_DIR}/logs"
sudo chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
sudo chmod +x "${APP_DIR}/deploy/oracle/backup.sh" "${APP_DIR}/deploy/oracle/update.sh" || true

echo "==> [4/6] Building Python venv + installing deps..."
sudo -u "${APP_USER}" python3.12 -m venv "${APP_DIR}/.venv"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip wheel
# Core deps + the LLM providers you actually use (OpenAI-compatible = Azure v1).
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -e "${APP_DIR}[providers]"

if [[ ! -f "${APP_DIR}/.env" ]]; then
  echo "==> No .env found; seeding from deploy/oracle/.env.production.example"
  sudo -u "${APP_USER}" cp "${APP_DIR}/deploy/oracle/.env.production.example" "${APP_DIR}/.env"
  echo "    !!! EDIT ${APP_DIR}/.env before the services will work correctly."
fi

echo "==> [5/6] Installing systemd services + backup timer..."
sudo cp "${APP_DIR}/deploy/oracle/systemd/"*.service /etc/systemd/system/
sudo cp "${APP_DIR}/deploy/oracle/systemd/"*.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now \
    aevrix-api aevrix-bot aevrix-scheduler aevrix-dashboard aevrix-backup.timer

# Install the Caddyfile (edit the domain first for HTTPS to succeed).
sudo cp "${APP_DIR}/deploy/oracle/Caddyfile" /etc/caddy/Caddyfile
sudo systemctl enable caddy

echo "==> [6/6] Configuring host firewall (ufw)..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

cat <<EOF

===========================================================================
 AEVRIX provisioning complete.

 NEXT STEPS (manual, one-time):
   1. Edit secrets:            sudo nano ${APP_DIR}/.env
   2. Set your real domain:    sudo nano /etc/caddy/Caddyfile
   3. Apply + start HTTPS:     sudo systemctl reload caddy
   4. Restart app services:    sudo systemctl restart aevrix-api aevrix-bot \\
                                   aevrix-scheduler aevrix-dashboard

 ALSO required in the Oracle web console (Security List / NSG):
   - Ingress allow TCP 80  (0.0.0.0/0)
   - Ingress allow TCP 443 (0.0.0.0/0)
   (Oracle's cloud firewall is separate from ufw — you need BOTH.)

 Verify:
   systemctl status aevrix-api --no-pager
   curl -s http://127.0.0.1:8000/health
   journalctl -u aevrix-bot -f
===========================================================================
EOF
