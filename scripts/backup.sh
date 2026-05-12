#!/bin/bash

set -e

export RESTIC_REPOSITORY="rclone:gdrive:orb-trader-backups"
export RESTIC_PASSWORD_FILE="/etc/orb-trader/restic.password"

BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/opt/orb-trader/logs/backup_${BACKUP_DATE}.log"

echo "========================================" | tee -a "$LOG_FILE"
echo "Backup started: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"

echo "Dumping database..." | tee -a "$LOG_FILE"
sudo -u postgres pg_dump orb_trader > /tmp/orb_backup_${BACKUP_DATE}.sql

echo "Uploading to Google Drive..." | tee -a "$LOG_FILE"
restic backup \
  /tmp/orb_backup_${BACKUP_DATE}.sql \
  /opt/orb-trader/config.yaml \
  /opt/orb-trader/logs \
  2>&1 | tee -a "$LOG_FILE"

echo "Applying retention policy..." | tee -a "$LOG_FILE"
restic forget \
  --keep-daily 30 \
  --keep-weekly 52 \
  --keep-yearly 5 \
  --prune \
  2>&1 | tee -a "$LOG_FILE"

rm /tmp/orb_backup_${BACKUP_DATE}.sql

echo "========================================" | tee -a "$LOG_FILE"
echo "Backup completed: $(date)" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
