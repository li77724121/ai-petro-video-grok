#!/bin/bash
# AI Pet Video Demo Script
# Usage: ./demo.sh [image_path] [motion_prompt]

set -e

# Defaults
IMAGE_PATH="${1:-~/Desktop/pet.jpg}"
MOTION_PROMPT="${2:-尾巴摇摆 + 眨眼 + 自然光照}"
OUTPUT_DIR="$(dirname "$0")/media"
mkdir -p "$OUTPUT_DIR"

# Check environment
if [ -z "$AUTH_TOKEN" ]; then
    echo "❌ AUTH_TOKEN not set. Run: export AUTH_TOKEN=\$(cat ~/.hermes-web-ui/.token)"
    exit 1
fi

BASE_URL="${HERMES_WEB_UI_URL:-http://127.0.0.1:8648}"

# Generate video
echo "🎬 Generating pet video..."
curl -sS \
  -X POST "${BASE_URL}/api/studio/media/grok-image-to-video" \\
  -H "Authorization: Bearer $AUTH_TOKEN" \\
  -d '{
    "image_path": "'"${IMAGE_PATH}"'",
    "prompt": "'"${MOTION_PROMPT}"'",
    "duration": 8,
    "output_path": "'"${OUTPUT_DIR}/pet-demo.mp4"'"
  }' | jq '.'

echo ""
echo "✅ Video saved to: ${OUTPUT_DIR}/pet-demo.mp4"
