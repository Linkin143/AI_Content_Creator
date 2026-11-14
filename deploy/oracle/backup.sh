#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# WAL-safe SQLite backup for AEVRIX.
# Uses the sqlite3 `.backup` command, which is safe while writers are active
# (it does NOT require stopping the bot/scheduler). Keeps the last 14 copies.
# ---------------------------------------------------------------------------
set -euo pipefail

APP_DIR="/opt/aevrix"
DB="${APP_DIR}/data/aevrix.db"
DEST="${APP_DIR}/data/backups"
KEEP=14

mkdir -p "${DEST}"

if [[ ! -f "${DB}" ]]; then
  echo "[backup] no database at ${DB} yet; nothing to do."
  exit 0
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="${DEST}/aevrix-${STAMP}.db"

# Atomic, consistent copy even with WAL mode active.
sqlite3 "${DB}" ".backup '${OUT}'"
gzip -f "${OUT}"
echo "[backup] wrote ${OUT}.gz"

# Prune: keep only the newest ${KEEP} archives.
ls -1t "${DEST}"/aevrix-*.db.gz 2>/dev/null | tail -n +$((KEEP + 1)) | xargs -r rm -f
echo "[backup] retention applied (keep ${KEEP})."
