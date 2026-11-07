#!/bin/bash
# Grok API Wrapper for Hermes Web UI
# Usage: ./grok-api.sh [image_path] [prompt] [duration]

set -e

IMAGE_PATH="${1:-}"
PROMPT="${2:-尾巴摇摆 + 眨眼 + 自然光照}"
DURATION="${3:-8}"
OUTPUT_PATH="${4:-$(dirname "$0")/media/output.mp4}"

# Check arguments
if [ -z "$IMAGE_PATH" ]; then
    echo "Usage: $0 <image_path> [prompt] [duration] [output_path]"
    exit 1
fi

# Resolve image path
IMAGE_PATH=$(realpath "$IMAGE_PATH")

# Check environment
if [ -z "$AUTH_TOKEN" ]; then
    echo "❌ AUTH_TOKEN not set. Run: export AUTH_TOKEN=\$(cat ~/.hermes-web-ui/.token)"
    exit 1
fi

BASE_URL="${HERMES_WEB_UI_URL:-http://127.0.0.1:8648}"

# Create output directory
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Generate video
echo "🎬 Grok Image-to-Video API call..."
curl -sS \
  -X POST "${BASE_URL}/api/studio/media/grok-image-to-video" \\
  -H "Authorization: Bearer $AUTH_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "image_path": "'"${IMAGE_PATH}"'",
    "prompt": "'"${PROMPT}"'",
    "duration": '"${DURATION}"',
    "output_path": "'"${OUTPUT_PATH}"'"
  }' | jq '.'

echo ""
if [ -f "$OUTPUT_PATH" ]; then
    echo "✅ Video generated: $OUTPUT_PATH"
    ls -lh "$OUTPUT_PATH"
else
    echo "⚠️  Output file not found at: $OUTPUT_PATH"
fi
