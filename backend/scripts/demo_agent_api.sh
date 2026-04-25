#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"

print_section() {
  printf '\n== %s ==\n' "$1"
}

pretty_print_json() {
  python -m json.tool
}

get_json() {
  local path="$1"
  curl -sS "${API_BASE_URL}${path}" | pretty_print_json
}

post_json() {
  local path="$1"
  local body="$2"
  curl -sS \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$body" \
    "${API_BASE_URL}${path}" | pretty_print_json
}

print_section "Service Health"
get_json "/health"

print_section "Agent Health"
get_json "/api/agent/health"

print_section "Registered Tools"
get_json "/api/agent/tools"

print_section "Validation Report"
get_json "/api/admin/validate"

print_section "Agent Query: Trending Tokens"
post_json "/api/agent/query" '{"message":"Which tokens are trending right now?","debug":true}'

print_section "Agent Query: Positive KOL Sentiment"
post_json "/api/agent/query" '{"message":"Which tokens have positive KOL sentiment?","debug":true}'

print_section "Agent Query: Risky Tokens"
post_json "/api/agent/query" '{"message":"Which tokens look risky?","debug":true}'

print_section "Agent Query: Smart-Money Activity"
post_json "/api/agent/query" '{"message":"Which tokens have smart-money activity?","debug":true}'

print_section "Agent Query: KOL Hype Vs Market Data"
post_json "/api/agent/query" '{"message":"Is the KOL hype backed by market data?","debug":true}'
