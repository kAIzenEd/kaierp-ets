#!/bin/bash
# Backup Odoo database and filestore for local Docker dev.
# Usage: ./scripts/backup.sh
# Backups are saved to ~/odoo-backups/ (not committed to Git).

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${ODOO_BACKUP_DIR:-$HOME/odoo-backups}"
DB_NAME="${ODOO_DB_NAME:-odoo_ets}"
DATE=$(date +%Y%m%d_%H%M)

mkdir -p "$BACKUP_DIR"
cd "$PROJECT_DIR"

if ! docker compose ps --status running web db 2>/dev/null | grep -q .; then
    echo "Error: Docker containers are not running. Start them with: docker compose up -d"
    exit 1
fi

echo "Backing up database: $DB_NAME"
docker compose exec -T db pg_dump -U odoo -Fc "$DB_NAME" \
    > "$BACKUP_DIR/${DB_NAME}_${DATE}.dump"

echo "Backing up filestore: $DB_NAME"
docker compose exec -T web tar czf - -C /var/lib/odoo/filestore "$DB_NAME" \
    > "$BACKUP_DIR/${DB_NAME}_filestore_${DATE}.tar.gz"

# Keep last 14 days of backups
find "$BACKUP_DIR" -name "${DB_NAME}*" -mtime +14 -delete 2>/dev/null || true

echo "Done."
echo "  Database:  $BACKUP_DIR/${DB_NAME}_${DATE}.dump"
echo "  Filestore: $BACKUP_DIR/${DB_NAME}_filestore_${DATE}.tar.gz"
