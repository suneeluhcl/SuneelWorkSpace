#!/bin/bash
# Start the full Ollama intelligence stack in tmux
cd ~/SuneelWorkSpace

# Start orchestrator (coordinates all engines)
tmux new-session -d -s ollama-orchestrator \
  "cd ~/SuneelWorkSpace && python3 lab/autolab/ollama_orchestrator.py 2>&1 | tee blood/logs/orchestrator.log"

# Start nerve healer daemon
tmux new-session -d -s nerve-healer \
  "cd ~/SuneelWorkSpace && python3 nervous/nerve_healer.py 2>&1 | tee blood/logs/nerve_healer_daemon.log"

echo "Ollama stack started:"
echo "   ollama-orchestrator — all engines (repair, learn, code review, security, etc.)"
echo "   nerve-healer        — continuous nerve connection monitoring"
echo ""
echo "View logs:  tmux attach -t ollama-orchestrator"
echo "            tmux attach -t nerve-healer"
echo "Status:     ollama-stack-status"
