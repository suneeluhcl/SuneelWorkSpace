#!/usr/bin/env bash
# shell_client.sh — Shell functions for the workspace gateway
# Source this file: source ~/SuneelWorkSpace/nervous/gateway/clients/shell_client.sh

WORKSPACE="${WORKSPACE:-$HOME/SuneelWorkSpace}"
GW_URL="http://localhost:8888"
GW_TOKEN_FILE="$WORKSPACE/nervous/gateway/.token"

_gw_token() { cat "$GW_TOKEN_FILE" 2>/dev/null || echo "NO_TOKEN"; }
_gw_get()  { curl -sf -H "Authorization: Bearer $(_gw_token)" "$GW_URL$1" | jq . 2>/dev/null || curl -sf -H "Authorization: Bearer $(_gw_token)" "$GW_URL$1"; }
_gw_post() { curl -sf -X POST -H "Authorization: Bearer $(_gw_token)" "$GW_URL$1" | jq . 2>/dev/null; }

ws-health()   { _gw_get "/health"; }
ws-suggest()  { _gw_get "/brain/anticipation/suggestions"; }
ws-goals()    { _gw_get "/goals/active"; }
ws-workflows(){ _gw_get "/workflows/list"; }
ws-decisions(){ _gw_get "/memory/decisions"; }
ws-facts()    { _gw_get "/memory/facts"; }

ws-search() {
  local query="${1:-}"
  if [[ -z "$query" ]]; then echo "Usage: ws-search <query>"; return 1; fi
  _gw_get "/memory/search?q=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")"
}

ws-arxiv() {
  local query="${1:-}"
  if [[ -z "$query" ]]; then echo "Usage: ws-arxiv <query>"; return 1; fi
  curl -sf -X POST -H "Authorization: Bearer $(_gw_token)" "$GW_URL/research/arxiv?query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$query'))")" | jq . 2>/dev/null
}

ws-help() {
  echo "Workspace gateway shell functions:"
  echo "  ws-health       — Check gateway and workspace health"
  echo "  ws-suggest      — Get current anticipation suggestions"
  echo "  ws-goals        — List active goals"
  echo "  ws-workflows    — List available workflows"
  echo "  ws-decisions    — Read decisions memory"
  echo "  ws-facts        — Read facts memory"
  echo "  ws-search <q>   — Semantic memory search"
  echo "  ws-arxiv <q>    — Search Arxiv for papers"
  echo "  ws-help         — Show this help"
}
