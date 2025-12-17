#!/bin/bash
# FreeSWITCH Docker Entrypoint Script

set -e

echo "Starting FreeSWITCH for OCP Platform..."

# Set environment variables if not provided
export FREESWITCH_ESL_PASSWORD=${FREESWITCH_ESL_PASSWORD:-ClueCon}
export TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID:-}
export TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN:-}

# Print configuration (without sensitive data)
echo "FreeSWITCH Configuration:"
echo "  ESL Password: [SET]"
echo "  Twilio Account SID: ${TWILIO_ACCOUNT_SID:0:10}..."

# Start FreeSWITCH in foreground
exec /usr/bin/freeswitch -nonat -nc -nf
