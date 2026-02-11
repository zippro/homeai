#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <base_url>"
  echo "Example: $0 https://api.homeai.example.com"
  exit 1
fi

BASE_URL="${1%/}"

echo "Checking: ${BASE_URL}/healthz"
curl -fsS "${BASE_URL}/healthz"
echo

echo "Checking: ${BASE_URL}/v1/config/provider-route-preview?operation=restyle&tier=preview&target_part=full_room"
curl -fsS "${BASE_URL}/v1/config/provider-route-preview?operation=restyle&tier=preview&target_part=full_room"
echo

echo "Backend verification passed."
