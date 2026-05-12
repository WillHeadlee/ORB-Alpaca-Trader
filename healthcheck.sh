#!/bin/bash
LOG_FILE="/opt/orb-trader/logs/healthcheck.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

if ! systemctl is-active --quiet orb-trader; then
    echo "[$TIMESTAMP] CRITICAL: orb-trader service is DOWN" >> "$LOG_FILE"

    # Uncomment to send a Discord alert:
    # curl -s -X POST -H 'Content-Type: application/json' \
    #   -d '{"content":"🚨 ORB Trader is DOWN!"}' \
    #   "$DISCORD_WEBHOOK_URL"

    exit 1
else
    echo "[$TIMESTAMP] OK: orb-trader service is running" >> "$LOG_FILE"
    exit 0
fi
