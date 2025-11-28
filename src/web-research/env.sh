#!/bin/sh
# Generates runtime config.js from environment variables
# This runs at container startup before nginx starts

set -e

CONFIG_FILE="/usr/share/nginx/html/config.js"

cat > "$CONFIG_FILE" << EOF
// Runtime configuration - generated at container startup
window.env = {
  API_URL: "${VITE_API_URL:-/api}",
  APP_VERSION: "${APP_VERSION:-dev}",
  ENABLE_MOCK: ${ENABLE_MOCK:-false}
};
EOF

echo "Generated $CONFIG_FILE with API_URL=${VITE_API_URL:-/api}"
