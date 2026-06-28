#!/bin/bash
tmux kill-session -t ollama-orchestrator 2>/dev/null && echo "Stopped: ollama-orchestrator" || echo "Not running: ollama-orchestrator"
tmux kill-session -t nerve-healer 2>/dev/null && echo "Stopped: nerve-healer" || echo "Not running: nerve-healer"
tmux kill-session -t diagnostics 2>/dev/null && echo "Stopped: diagnostics" || true
