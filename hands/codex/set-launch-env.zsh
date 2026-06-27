#!/bin/zsh

source /Users/MAC/SuneelWorkSpace/hands/codex/codex-env.zsh

if [ -n "${GITHUB_PAT_TOKEN:-}" ]; then
  launchctl setenv GITHUB_PAT_TOKEN "$GITHUB_PAT_TOKEN"
fi
